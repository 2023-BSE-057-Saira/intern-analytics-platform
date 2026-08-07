"""
app/routers/students.py
==========================
Self-service endpoints for the Student dashboard. Every response shape
here is matched exactly to what app/static/student.html reads off it -
built by reading that file directly, not guessed.

Every endpoint is scoped through current_user.intern_id (from the JWT),
never a URL parameter, so a student can only ever touch their own record.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import (
    Intern, Task, Attendance, Prediction, Recommendation,
    WeeklyReport, ProjectSubmission,
)
from app.schemas.schemas import (
    InternProfileOut, InternProfileUpdate,
    WeeklyReportCreate, WeeklyReportOut,
    ProjectSubmissionCreate, ProjectSubmissionOut,
)
from app.security import require_role

router = APIRouter(prefix="/student", tags=["Students"])


def _get_own_intern(current_user, db: Session) -> Intern:
    if not current_user.intern_id:
        raise HTTPException(status_code=400, detail="This account isn't linked to an intern record.")
    intern = db.query(Intern).filter(Intern.intern_id == current_user.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern record not found.")
    return intern


def _current_streak_days(attendance_records) -> int:
    """Consecutive present days counting back from today/yesterday.
    A gap breaks the streak to 0 rather than counting a stale one."""
    present_dates = sorted({a.date for a in attendance_records if a.present}, reverse=True)
    if not present_dates:
        return 0
    if present_dates[0] not in (date.today(), date.today() - timedelta(days=1)):
        return 0
    streak, cursor = 0, present_dates[0]
    for d in present_dates:
        if d == cursor:
            streak += 1
            cursor -= timedelta(days=1)
        elif d < cursor:
            break
    return streak


# --- Profile ------------------------------------------------------------------

@router.get("/profile", response_model=InternProfileOut)
def get_my_profile(db: Session = Depends(get_db),
                    current_user=Depends(require_role("student"))):
    return _get_own_intern(current_user, db)


@router.patch("/profile", response_model=InternProfileOut)
def update_my_profile(payload: InternProfileUpdate, db: Session = Depends(get_db),
                       current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(intern, field, value)
    db.add(intern)
    db.commit()
    db.refresh(intern)
    return intern


# --- Attendance -----------------------------------------------------------------

@router.post("/attendance/mark")
def mark_attendance(db: Session = Depends(get_db),
                     current_user=Depends(require_role("student"))):
    """Idempotent - calling it twice in one day doesn't double-mark."""
    intern = _get_own_intern(current_user, db)
    today = date.today()
    existing = (
        db.query(Attendance)
        .filter(Attendance.intern_id == intern.intern_id, Attendance.date == today)
        .first()
    )
    if not existing:
        db.add(Attendance(intern_id=intern.intern_id, date=today, present=True))
        db.commit()
    return {"detail": "Attendance marked."}


# --- Weekly reports ---------------------------------------------------------------

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


@router.post("/weekly-report", response_model=WeeklyReportOut)
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


# --- Project submissions -----------------------------------------------------------

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


@router.post("/project", response_model=ProjectSubmissionOut)
def submit_project(payload: ProjectSubmissionCreate, db: Session = Depends(get_db),
                    current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)
    submission = ProjectSubmission(intern_id=intern.intern_id, **payload.model_dump())
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


# --- Overview (drives the whole Overview tab) -----------------------------------------

@router.get("/overview")
def get_my_overview(db: Session = Depends(get_db),
                     current_user=Depends(require_role("student"))):
    intern = _get_own_intern(current_user, db)

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

    dropout_risk = float(latest["dropout_risk"].predicted_value) if "dropout_risk" in latest else None
    success_probability = float(latest["success_probability"].predicted_value) if "success_probability" in latest else None
    performance_trend = None
    if "performance_trend" in latest and latest["performance_trend"].explanation_json:
        performance_trend = latest["performance_trend"].explanation_json.get("predicted_label")

    # --- Attendance ---
    attendance = db.query(Attendance).filter(Attendance.intern_id == intern.intern_id).all()
    marked_today = any(a.date == date.today() for a in attendance)

    # --- Tasks ---
    tasks = db.query(Task).filter(Task.intern_id == intern.intern_id).all()
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == "completed")
    pending = sum(1 for t in tasks if t.status == "pending")
    late = sum(1 for t in tasks if t.status == "late")

    # --- AI suggestions (existing recommendations, most recent first) ---
    recs = (
        db.query(Recommendation)
        .filter(Recommendation.intern_id == intern.intern_id)
        .order_by(Recommendation.created_at.desc())
        .limit(10)
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
            "phone": intern.phone,
            "education": intern.education,
            "skills": intern.skills,
            "bio": intern.bio,
            "linkedin_url": intern.linkedin_url,
            "github_url": intern.github_url,
        },
        "predictions": {
            "dropout_risk": dropout_risk,
            "success_probability": success_probability,
            "performance_trend": performance_trend,
        },
        "attendance": {
            "current_streak_days": _current_streak_days(attendance),
            "marked_today": marked_today,
        },
        "tasks": {
            "total": total,
            "completed": completed,
            "pending": pending,
            "late": late,
        },
        "suggestions": [
            {"type": r.recommendation_type, "message": r.message}
            for r in recs
        ],
    }
