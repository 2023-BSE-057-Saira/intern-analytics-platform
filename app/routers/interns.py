"""
Endpoints for managing intern records.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import (
    Intern, Prediction, Recommendation, WeeklyReport, ProjectSubmission,
)
from app.schemas.schemas import InternCreate, InternOut, InternUpdate
from app.security import require_role

router = APIRouter(prefix="/interns", tags=["Interns"])


def _assert_can_view(intern: Intern, current_user) -> None:
    """Ownership check shared by /{intern_id} and /{intern_id}/detail.
    Admins: unrestricted. Mentors: only their own roster. Students:
    only their own record. Without this, any authenticated mentor or
    student could view any intern by editing the URL/ID."""
    if current_user.role == "admin":
        return
    if current_user.role == "mentor" and current_user.mentor_id == intern.mentor_id:
        return
    if current_user.role == "student" and current_user.intern_id == intern.intern_id:
        return
    raise HTTPException(status_code=403, detail="Not authorized to view this intern")


@router.post("/", response_model=InternOut)
def create_intern(intern: InternCreate, db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin"))):
    db_intern = Intern(**intern.model_dump())
    db.add(db_intern)
    db.commit()
    db.refresh(db_intern)
    return db_intern


@router.get("/", response_model=list[InternOut])
def list_interns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                  current_user=Depends(require_role("admin", "mentor"))):
    return db.query(Intern).offset(skip).limit(limit).all()


@router.get("/unassigned/list", response_model=list[InternOut])
def list_unassigned_interns(db: Session = Depends(get_db),
                             current_user=Depends(require_role("admin"))):
    """Self-registered students waiting for a mentor to be assigned.
    NOTE: this route must stay ABOVE /{intern_id} below — FastAPI
    matches routes top-to-bottom, and /{intern_id} would otherwise
    swallow this request (treating 'unassigned' as an intern_id and
    failing int validation) before ever reaching this one."""
    return db.query(Intern).filter(Intern.mentor_id.is_(None)).all()


@router.get("/{intern_id}", response_model=InternOut)
def get_intern(intern_id: int, db: Session = Depends(get_db),
                current_user=Depends(require_role("admin", "mentor", "student"))):
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    _assert_can_view(intern, current_user)
    return intern


@router.get("/{intern_id}/detail")
def get_intern_detail(intern_id: int, db: Session = Depends(get_db),
                       current_user=Depends(require_role("admin", "mentor", "student"))):
    """
    Combined payload for the intern detail page: profile + every past
    prediction (with its SHAP explanation) + recommendations, plus —
    for admin/mentor only — weekly reports and project submissions so
    reviews can happen from the same screen.

    One call instead of five separate fetches on the frontend.
    """
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    _assert_can_view(intern, current_user)

    predictions = (
        db.query(Prediction)
        .filter(Prediction.intern_id == intern_id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.intern_id == intern_id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )

    # Most recent prediction per type, for the summary cards at the top.
    latest_by_type = {}
    for p in predictions:
        if p.prediction_type not in latest_by_type:
            latest_by_type[p.prediction_type] = p

    payload = {
        "intern": {
            "intern_id": intern.intern_id,
            "name": intern.name,
            "email": intern.email,
            "technology": intern.technology,
            "batch": intern.batch,
            "status": intern.status,
            "start_date": intern.start_date.isoformat() if intern.start_date else None,
            "expected_end_date": intern.expected_end_date.isoformat() if intern.expected_end_date else None,
            "phone": intern.phone,
            "education": intern.education,
            "skills": intern.skills,
            "bio": intern.bio,
            "linkedin_url": intern.linkedin_url,
            "github_url": intern.github_url,
            "avatar_color": intern.avatar_color,
            "mentor_id": intern.mentor_id,
        },
        "latest_predictions": {
            ptype: {
                "predicted_value": float(p.predicted_value),
                "confidence": float(p.confidence) if p.confidence is not None else None,
                "explanation": p.explanation_json,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for ptype, p in latest_by_type.items()
        },
        "prediction_history": [
            {
                "prediction_type": p.prediction_type,
                "predicted_value": float(p.predicted_value),
                "confidence": float(p.confidence) if p.confidence is not None else None,
                "explanation": p.explanation_json,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in predictions
        ],
        "recommendations": [
            {
                "recommendation_type": r.recommendation_type,
                "message": r.message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recommendations
        ],
    }

    if current_user.role in ("admin", "mentor"):
        reports = (
            db.query(WeeklyReport)
            .filter(WeeklyReport.intern_id == intern_id)
            .order_by(WeeklyReport.week_start_date.desc())
            .all()
        )
        submissions = (
            db.query(ProjectSubmission)
            .filter(ProjectSubmission.intern_id == intern_id)
            .order_by(ProjectSubmission.submitted_at.desc())
            .all()
        )
        payload["weekly_reports"] = [
            {
                "report_id": r.report_id,
                "week_start_date": r.week_start_date.isoformat(),
                "hours_worked": float(r.hours_worked) if r.hours_worked is not None else None,
                "summary": r.summary,
                "challenges": r.challenges,
                "reviewed": bool(r.reviewed),
                "mentor_comment": r.mentor_comment,
            }
            for r in reports
        ]
        payload["project_submissions"] = [
            {
                "submission_id": s.submission_id,
                "title": s.title,
                "description": s.description,
                "repo_url": s.repo_url,
                "demo_url": s.demo_url,
                "submitted_at": s.submitted_at.isoformat(),
                "reviewed": bool(s.reviewed),
                "mentor_comment": s.mentor_comment,
            }
            for s in submissions
        ]

    return payload


@router.patch("/{intern_id}", response_model=InternOut)
def update_intern(intern_id: int, payload: InternUpdate, db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin"))):
    """Admin-only. Primary use case right now: assigning a mentor to a
    student who self-registered through the landing page (their
    mentor_id starts out NULL until an admin does this)."""
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(intern, field, value)
    db.commit()
    db.refresh(intern)
    return intern