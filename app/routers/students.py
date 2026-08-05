"""
app/routers/students.py
==========================
Self-service endpoints for the Student dashboard - profile editing,
task tracking, and an aggregated "my dashboard" view.

Every endpoint here is scoped through current_user.intern_id (pulled
from the JWT), never from a URL parameter, so a student can only ever
read or edit their own record - the same pattern used in
app/routers/mentor.py for mentor-scoped data.
"""
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import (
    Intern, Mentor, Task, Attendance, GithubActivity,
    CommunicationActivity, Prediction, Recommendation,
)
from app.schemas.schemas import StudentProfileUpdate, TaskOut, TaskStatusUpdate
from app.security import require_role

router = APIRouter(prefix="/students/me", tags=["Students"])


def _get_own_intern(current_user, db: Session) -> Intern:
    if not current_user.intern_id:
        raise HTTPException(status_code=400, detail="This account isn't linked to an intern record.")
    intern = db.query(Intern).filter(Intern.intern_id == current_user.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern record not found.")
    return intern


# --- Profile ----------------------------------------------------------------

@router.get("/profile")
def get_my_profile(db: Session = Depends(get_db),
                    current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    mentor = db.query(Mentor).filter(Mentor.mentor_id == intern.mentor_id).first() if intern.mentor_id else None
    return {
        "intern_id": intern.intern_id,
        "name": intern.name,
        "email": intern.email,
        "technology": intern.technology,
        "batch": intern.batch,
        "status": intern.status,
        "start_date": intern.start_date,
        "expected_end_date": intern.expected_end_date,
        "mentor": {"mentor_id": mentor.mentor_id, "name": mentor.name, "technology": mentor.technology}
        if mentor else None,
    }


@router.patch("/profile")
def update_my_profile(payload: StudentProfileUpdate, db: Session = Depends(get_db),
                       current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    updates = payload.model_dump(exclude_unset=True)

    if "email" in updates and updates["email"] != intern.email:
        new_email = updates["email"]
        if db.query(Intern).filter(Intern.email == new_email, Intern.intern_id != intern.intern_id).first() \
                or db.query(Mentor).filter(Mentor.email == new_email).first():
            raise HTTPException(status_code=409, detail="That email is already in use.")
        # Keep the login record in sync - the User row is what /auth/login checks against.
        current_user.email = new_email
        db.add(current_user)

    for field, value in updates.items():
        setattr(intern, field, value)

    db.add(intern)
    db.commit()
    db.refresh(intern)
    return {
        "intern_id": intern.intern_id,
        "name": intern.name,
        "email": intern.email,
        "technology": intern.technology,
        "batch": intern.batch,
        "status": intern.status,
    }


# --- Tasks --------------------------------------------------------------------

@router.get("/tasks", response_model=list[TaskOut])
def list_my_tasks(db: Session = Depends(get_db),
                   current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    return (
        db.query(Task)
        .filter(Task.intern_id == intern.intern_id)
        .order_by(Task.due_date.is_(None), Task.due_date.asc())
        .all()
    )


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_my_task_status(task_id: int, payload: TaskStatusUpdate, db: Session = Depends(get_db),
                           current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    task = db.query(Task).filter(Task.task_id == task_id, Task.intern_id == intern.intern_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if payload.status not in ("pending", "in_progress", "completed", "late", "skipped"):
        raise HTTPException(status_code=422, detail="Invalid task status.")

    task.status = payload.status
    task.completed_date = date.today() if payload.status == "completed" else None
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# --- Dashboard overview ---------------------------------------------------------

@router.get("/overview")
def get_my_overview(db: Session = Depends(get_db),
                     current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    mentor = db.query(Mentor).filter(Mentor.mentor_id == intern.mentor_id).first() if intern.mentor_id else None

    # --- Latest prediction per type (same "most recent wins" logic as admin/mentor) ---
    preds = (
        db.query(Prediction)
        .filter(Prediction.intern_id == intern.intern_id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    latest = {}
    for p in preds:
        if p.prediction_type not in latest:
            latest[p.prediction_type] = p
    predictions = {ptype: float(p.predicted_value) for ptype, p in latest.items()}
    trend_label = None
    if "performance_trend" in latest and latest["performance_trend"].explanation_json:
        trend_label = latest["performance_trend"].explanation_json.get("predicted_label")

    # --- Tasks ---
    tasks = db.query(Task).filter(Task.intern_id == intern.intern_id).all()
    total_tasks = len(tasks)
    completed = sum(1 for t in tasks if t.status == "completed")
    pending = sum(1 for t in tasks if t.status == "pending")
    in_progress = sum(1 for t in tasks if t.status == "in_progress")
    late = sum(1 for t in tasks if t.status == "late")
    skipped = sum(1 for t in tasks if t.status == "skipped")
    completion_rate = round(completed / total_tasks, 4) if total_tasks else None

    # --- Attendance ---
    attendance = db.query(Attendance).filter(Attendance.intern_id == intern.intern_id).all()
    attendance_rate = round(sum(1 for a in attendance if a.present) / len(attendance), 4) if attendance else None

    # --- GitHub activity ---
    github = db.query(GithubActivity).filter(GithubActivity.intern_id == intern.intern_id).all()
    github_totals = {
        "commits": sum(g.commits or 0 for g in github),
        "pull_requests": sum(g.pull_requests or 0 for g in github),
        "issues_opened": sum(g.issues_opened or 0 for g in github),
        "issues_closed": sum(g.issues_closed or 0 for g in github),
    }

    # --- Communication activity ---
    comms = db.query(CommunicationActivity).filter(CommunicationActivity.intern_id == intern.intern_id).all()
    comm_totals = {
        "messages_sent": sum(c.messages_sent or 0 for c in comms),
        "meetings_attended": sum(c.meetings_attended or 0 for c in comms),
    }

    # --- Recommendations (view-only for students; generation is admin/mentor) ---
    recs = (
        db.query(Recommendation)
        .filter(Recommendation.intern_id == intern.intern_id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )

    return {
        "profile": {
            "intern_id": intern.intern_id,
            "name": intern.name,
            "email": intern.email,
            "technology": intern.technology,
            "batch": intern.batch,
            "status": intern.status,
            "start_date": intern.start_date,
            "expected_end_date": intern.expected_end_date,
        },
        "mentor": {"name": mentor.name, "technology": mentor.technology} if mentor else None,
        "predictions": {
            "dropout_risk": predictions.get("dropout_risk"),
            "success_probability": predictions.get("success_probability"),
            "performance_trend": trend_label,
            "learning_speed": predictions.get("learning_speed"),
            "skill_growth": predictions.get("skill_growth"),
            "completion_probability": predictions.get("completion_probability"),
        },
        "tasks": {
            "total": total_tasks,
            "completed": completed,
            "pending": pending,
            "in_progress": in_progress,
            "late": late,
            "skipped": skipped,
            "completion_rate": completion_rate,
            "items": [
                {
                    "task_id": t.task_id, "task_name": t.task_name,
                    "assigned_date": t.assigned_date, "due_date": t.due_date,
                    "completed_date": t.completed_date, "status": t.status,
                    "difficulty": t.difficulty,
                }
                for t in sorted(tasks, key=lambda t: (t.due_date is None, t.due_date))
            ],
        },
        "attendance_rate": attendance_rate,
        "github": github_totals,
        "communication": comm_totals,
        "recommendations": [
            {"recommendation_type": r.recommendation_type, "message": r.message, "created_at": r.created_at}
            for r in recs
        ],
    }
