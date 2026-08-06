"""
app/routers/students.py
==========================
Self-service endpoints for the Student dashboard - profile editing,
task tracking, daily attendance check-in, weekly reports, project
submissions, and an aggregated "my dashboard" view.

Every endpoint here is scoped through current_user.intern_id (pulled
from the JWT), never from a URL parameter, so a student can only ever
read or edit their own record - the same pattern used in
app/routers/mentor.py for mentor-scoped data.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import (
    Intern, Mentor, Task, Attendance, GithubActivity,
    CommunicationActivity, Prediction, Recommendation,
    WeeklyReport, ProjectSubmission,
)
from app.schemas.schemas import (
    InternProfileOut, InternProfileUpdate, TaskOut, TaskStatusUpdate,
    AttendanceOut, WeeklyReportCreate, WeeklyReportOut,
    ProjectSubmissionCreate, ProjectSubmissionOut,
)
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

@router.get("/profile", response_model=InternProfileOut)
def get_my_profile(db: Session = Depends(get_db),
                    current_user=Depends(require_role("student"))):
    return _get_own_intern(current_user, db)


@router.patch("/profile", response_model=InternProfileOut)
def update_my_profile(payload: InternProfileUpdate, db: Session = Depends(get_db),
                       current_user=Depends(require_role("student"))):
    """Only the fields InternProfileUpdate defines (phone, education,
    skills, bio, linkedin_url, github_url) are student-editable — name/
    email/technology/batch stay admin-controlled by design."""
    intern = _get_own_intern(current_user, db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(intern, field, value)
    db.add(intern)
    db.commit()
    db.refresh(intern)
    return intern


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


# --- Attendance: daily self check-in -------------------------------------------

@router.post("/attendance/checkin", response_model=AttendanceOut)
def check_in_today(db: Session = Depends(get_db),
                    current_user=Depends(require_role("student"))):
    """Marks the logged-in student present for today. Idempotent - if
    today's row already exists it's just returned, not duplicated."""
    intern = _get_own_intern(current_user, db)
    today = date.today()
    existing = (
        db.query(Attendance)
        .filter(Attendance.intern_id == intern.intern_id, Attendance.date == today)
        .first()
    )
    if existing:
        return existing
    record = Attendance(intern_id=intern.intern_id, date=today, present=True)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/attendance", response_model=list[AttendanceOut])
def list_my_attendance(db: Session = Depends(get_db),
                        current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    return (
        db.query(Attendance)
        .filter(Attendance.intern_id == intern.intern_id)
        .order_by(Attendance.date.desc())
        .limit(60)
        .all()
    )


# --- Weekly reports --------------------------------------------------------------

@router.get("/weekly-reports", response_model=list[WeeklyReportOut])
def list_my_weekly_reports(db: Session = Depends(get_db),
                            current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    return (
        db.query(WeeklyReport)
        .filter(WeeklyReport.intern_id == intern.intern_id)
        .order_by(WeeklyReport.week_start_date.desc())
        .all()
    )


@router.post("/weekly-reports", response_model=WeeklyReportOut)
def submit_weekly_report(payload: WeeklyReportCreate, db: Session = Depends(get_db),
                          current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    existing = (
        db.query(WeeklyReport)
        .filter(WeeklyReport.intern_id == intern.intern_id,
                WeeklyReport.week_start_date == payload.week_start_date)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="You've already submitted a report for that week.")
    report = WeeklyReport(intern_id=intern.intern_id, **payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# --- Project submissions ---------------------------------------------------------

@router.get("/projects", response_model=list[ProjectSubmissionOut])
def list_my_projects(db: Session = Depends(get_db),
                      current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    return (
        db.query(ProjectSubmission)
        .filter(ProjectSubmission.intern_id == intern.intern_id)
        .order_by(ProjectSubmission.submitted_at.desc())
        .all()
    )


@router.post("/projects", response_model=ProjectSubmissionOut)
def submit_project(payload: ProjectSubmissionCreate, db: Session = Depends(get_db),
                    current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    submission = ProjectSubmission(intern_id=intern.intern_id, **payload.model_dump())
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


# --- Dashboard overview ---------------------------------------------------------

@router.get("/overview")
def get_my_overview(db: Session = Depends(get_db),
                     current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    mentor = db.query(Mentor).filter(Mentor.mentor_id == intern.mentor_id).first() if intern.mentor_id else None

    # --- Latest prediction per type ---
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
    marked_today = any(a.date == date.today() for a in attendance)

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
            "phone": intern.phone,
            "education": intern.education,
            "skills": intern.skills,
            "bio": intern.bio,
            "linkedin_url": intern.linkedin_url,
            "github_url": intern.github_url,
            "avatar_color": intern.avatar_color,
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
        "attendance_marked_today": marked_today,
        "weekly_reports_count": db.query(WeeklyReport).filter(WeeklyReport.intern_id == intern.intern_id).count(),
        "projects_count": db.query(ProjectSubmission).filter(ProjectSubmission.intern_id == intern.intern_id).count(),
        "github": github_totals,
        "communication": comm_totals,
        "recommendations": [
            {"recommendation_type": r.recommendation_type, "message": r.message, "created_at": r.created_at}
            for r in recs
        ],
    }
