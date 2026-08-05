"""
app/routers/student.py
==========================
Everything the student dashboard needs, scoped to the logged-in
student's own intern_id (never a URL param) — same pattern as
mentor.py, for the same reason: a student should never be able to
view or edit another intern's data by editing the URL.
"""
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import (
    Intern, Attendance, Task, Prediction, Recommendation,
    WeeklyReport, ProjectSubmission,
)
from app.schemas.schemas import (
    InternProfileOut, InternProfileUpdate, AttendanceOut,
    WeeklyReportCreate, WeeklyReportOut,
    ProjectSubmissionCreate, ProjectSubmissionOut,
)
from app.security import require_role

router = APIRouter(prefix="/student", tags=["Student"])


def _own_intern(db: Session, current_user) -> Intern:
    if not current_user.intern_id:
        raise HTTPException(status_code=400, detail="This account isn't linked to an intern record")
    intern = db.query(Intern).filter(Intern.intern_id == current_user.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern record not found")
    return intern


# --- Profile ------------------------------------------------------------------
@router.get("/profile", response_model=InternProfileOut)
def get_profile(db: Session = Depends(get_db), current_user=Depends(require_role("student"))):
    return _own_intern(db, current_user)


@router.patch("/profile", response_model=InternProfileOut)
def update_profile(payload: InternProfileUpdate, db: Session = Depends(get_db),
                    current_user=Depends(require_role("student"))):
    intern = _own_intern(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(intern, field, value)
    db.commit()
    db.refresh(intern)
    return intern


# --- Attendance ----------------------------------------------------------------
@router.post("/attendance/mark", response_model=AttendanceOut)
def mark_attendance(db: Session = Depends(get_db), current_user=Depends(require_role("student"))):
    """Marks the student present for today. Idempotent — calling it
    again the same day just returns the existing row instead of erroring,
    since the UI calls this from a single 'Mark Attendance' button."""
    intern = _own_intern(db, current_user)
    today = date.today()
    existing = db.query(Attendance).filter(
        Attendance.intern_id == intern.intern_id, Attendance.date == today
    ).first()
    if existing:
        return existing
    record = Attendance(intern_id=intern.intern_id, date=today, present=True)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/attendance/history", response_model=list[AttendanceOut])
def attendance_history(days: int = 30, db: Session = Depends(get_db),
                        current_user=Depends(require_role("student"))):
    intern = _own_intern(db, current_user)
    since = date.today() - timedelta(days=days)
    return (
        db.query(Attendance)
        .filter(Attendance.intern_id == intern.intern_id, Attendance.date >= since)
        .order_by(Attendance.date.desc())
        .all()
    )


# --- Weekly reports --------------------------------------------------------------
@router.post("/weekly-report", response_model=WeeklyReportOut)
def submit_weekly_report(payload: WeeklyReportCreate, db: Session = Depends(get_db),
                          current_user=Depends(require_role("student"))):
    intern = _own_intern(db, current_user)
    existing = db.query(WeeklyReport).filter(
        WeeklyReport.intern_id == intern.intern_id,
        WeeklyReport.week_start_date == payload.week_start_date,
    ).first()
    if existing:
        # Same week already submitted — update it rather than error,
        # so a student can revise a report before their mentor reads it.
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    record = WeeklyReport(intern_id=intern.intern_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/weekly-reports", response_model=list[WeeklyReportOut])
def list_weekly_reports(db: Session = Depends(get_db), current_user=Depends(require_role("student"))):
    intern = _own_intern(db, current_user)
    return (
        db.query(WeeklyReport)
        .filter(WeeklyReport.intern_id == intern.intern_id)
        .order_by(WeeklyReport.week_start_date.desc())
        .all()
    )


# --- Project submissions -----------------------------------------------------------
@router.post("/project", response_model=ProjectSubmissionOut)
def submit_project(payload: ProjectSubmissionCreate, db: Session = Depends(get_db),
                    current_user=Depends(require_role("student"))):
    intern = _own_intern(db, current_user)
    record = ProjectSubmission(intern_id=intern.intern_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/projects", response_model=list[ProjectSubmissionOut])
def list_projects(db: Session = Depends(get_db), current_user=Depends(require_role("student"))):
    intern = _own_intern(db, current_user)
    return (
        db.query(ProjectSubmission)
        .filter(ProjectSubmission.intern_id == intern.intern_id)
        .order_by(ProjectSubmission.submitted_at.desc())
        .all()
    )


# --- Dashboard overview -------------------------------------------------------------
@router.get("/overview")
def get_student_overview(db: Session = Depends(get_db), current_user=Depends(require_role("student"))):
    intern = _own_intern(db, current_user)

    # Latest prediction per type
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
    performance_trend_label = None
    if "performance_trend" in latest and latest["performance_trend"].explanation_json:
        performance_trend_label = latest["performance_trend"].explanation_json.get("predicted_label")

    # Attendance streak (consecutive days present, walking back from today)
    records = (
        db.query(Attendance)
        .filter(Attendance.intern_id == intern.intern_id)
        .order_by(Attendance.date.desc())
        .limit(90)
        .all()
    )
    by_date = {r.date: r.present for r in records}
    streak = 0
    cursor = date.today()
    while by_date.get(cursor):
        streak += 1
        cursor -= timedelta(days=1)

    # Task snapshot
    tasks = db.query(Task).filter(Task.intern_id == intern.intern_id).all()
    task_totals = defaultdict(int)
    for t in tasks:
        task_totals[t.status] += 1

    recs = (
        db.query(Recommendation)
        .filter(Recommendation.intern_id == intern.intern_id)
        .order_by(Recommendation.created_at.desc())
        .limit(10)
        .all()
    )

    marked_today = date.today() in by_date

    return {
        "profile": InternProfileOut.model_validate(intern).model_dump(),
        "predictions": {
            "dropout_risk": float(latest["dropout_risk"].predicted_value) if "dropout_risk" in latest else None,
            "success_probability": float(latest["success_probability"].predicted_value) if "success_probability" in latest else None,
            "performance_trend": performance_trend_label,
        },
        "attendance": {
            "current_streak_days": streak,
            "marked_today": marked_today,
        },
        "tasks": {
            "completed": task_totals.get("completed", 0),
            "pending": task_totals.get("pending", 0),
            "late": task_totals.get("late", 0),
            "total": len(tasks),
        },
        "suggestions": [
            {"type": r.recommendation_type, "message": r.message, "created_at": r.created_at.isoformat()}
            for r in recs
        ],
    }
