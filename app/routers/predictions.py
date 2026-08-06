"""
Endpoints that trigger and retrieve ML predictions.

Covers all 8 required predictions from the case study:
  1. Dropout Risk              - trained model
  2. Performance Trend         - trained model (3-class)
  3. Success Probability       - trained model
  4. Learning Speed/Skill Growth - trained model (regression)
  5. Completion Probability    - derived (1 - dropout_risk), no model
  6. Project Success Probability - reuses Success Probability model
  7. Mentor Workload            - direct SQL, no ML at all

FIX: the previous version of performance-trend and success-probability
returned the raw database record directly. The Prediction table's
column is named `explanation_json`, but the response schema expects
`explanation` - different names mean the response's explanation field
was silently coming back empty even though the data was saved
correctly in the database. Every endpoint below now explicitly builds
the response object instead of relying on that name matching.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.db_models import Intern, Prediction, Mentor
from app.schemas.schemas import PredictionOut, PredictionRequest
from app.security import require_role
from app.ml.predict import (
    predict_dropout_risk, predict_performance_trend, predict_success_probability,
    predict_learning_growth, predict_completion_probability, predict_project_success_probability,
)

router = APIRouter(prefix="/predict", tags=["Predictions"])


def _save_and_respond(intern_id: int, prediction_type: str, result: dict, db: Session) -> PredictionOut:
    """Shared save+response logic, used by every prediction endpoint below."""
    record = Prediction(
        intern_id=intern_id,
        prediction_type=prediction_type,
        predicted_value=result["value"],
        confidence=result.get("confidence"),
        explanation_json=result.get("explanation"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return PredictionOut(
        intern_id=record.intern_id,
        prediction_type=record.prediction_type,
        predicted_value=float(record.predicted_value),
        confidence=float(record.confidence) if record.confidence is not None else None,
        explanation=record.explanation_json,
        created_at=record.created_at,
    )


def _get_intern_or_404(intern_id: int, db: Session) -> Intern:
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    return intern


def _get_owned_intern_or_404(intern_id: int, db: Session, current_user) -> Intern:
    """Same as _get_intern_or_404, but also enforces that mentors only
    touch their own roster and students only touch their own record.
    Mirrors app/routers/interns.py's _assert_can_view."""
    intern = _get_intern_or_404(intern_id, db)
    if current_user.role == "admin":
        return intern
    if current_user.role == "mentor" and current_user.mentor_id == intern.mentor_id:
        return intern
    if current_user.role == "student" and current_user.intern_id == intern.intern_id:
        return intern
    raise HTTPException(status_code=403, detail="Not authorized for this intern")


@router.post("/dropout-risk", response_model=PredictionOut)
def get_dropout_risk(req: PredictionRequest, db: Session = Depends(get_db),
                      current_user=Depends(require_role("admin", "mentor", "student"))):
    _get_owned_intern_or_404(req.intern_id, db, current_user)
    result = predict_dropout_risk(intern_id=req.intern_id, db=db)
    return _save_and_respond(req.intern_id, "dropout_risk", result, db)


@router.post("/performance-trend", response_model=PredictionOut)
def get_performance_trend(req: PredictionRequest, db: Session = Depends(get_db),
                           current_user=Depends(require_role("admin", "mentor", "student"))):
    _get_owned_intern_or_404(req.intern_id, db, current_user)
    result = predict_performance_trend(intern_id=req.intern_id, db=db)
    return _save_and_respond(req.intern_id, "performance_trend", result, db)


@router.post("/success-probability", response_model=PredictionOut)
def get_success_probability(req: PredictionRequest, db: Session = Depends(get_db),
                             current_user=Depends(require_role("admin", "mentor", "student"))):
    _get_owned_intern_or_404(req.intern_id, db, current_user)
    result = predict_success_probability(intern_id=req.intern_id, db=db)
    return _save_and_respond(req.intern_id, "success_probability", result, db)


@router.post("/learning-growth", response_model=PredictionOut)
def get_learning_growth(req: PredictionRequest, db: Session = Depends(get_db),
                         current_user=Depends(require_role("admin", "mentor", "student"))):
    """Saves BOTH learning_speed and skill_growth as separate prediction rows."""
    _get_owned_intern_or_404(req.intern_id, db, current_user)
    result = predict_learning_growth(intern_id=req.intern_id, db=db)

    # Save skill_growth as its own row too, so it appears as its own
    # column when predictions are pivoted for the dashboard.
    skill_growth_value = result["explanation"]["skill_growth"]
    skill_growth_record = Prediction(
        intern_id=req.intern_id,
        prediction_type="skill_growth",
        predicted_value=skill_growth_value,
        confidence=None,
        explanation_json=result.get("explanation"),
    )
    db.add(skill_growth_record)
    db.commit()

    return _save_and_respond(req.intern_id, "learning_speed", result, db)


@router.post("/completion-probability", response_model=PredictionOut)
def get_completion_probability(req: PredictionRequest, db: Session = Depends(get_db),
                                current_user=Depends(require_role("admin", "mentor", "student"))):
    """Derived: 1 - dropout_risk. No separate model - just math on an existing prediction."""
    _get_owned_intern_or_404(req.intern_id, db, current_user)
    result = predict_completion_probability(intern_id=req.intern_id, db=db)
    return _save_and_respond(req.intern_id, "completion_probability", result, db)


@router.post("/project-success-probability", response_model=PredictionOut)
def get_project_success_probability(req: PredictionRequest, db: Session = Depends(get_db),
                                     current_user=Depends(require_role("admin", "mentor", "student"))):
    """Reuses the Success Probability model - documented approximation (see predict.py)."""
    _get_owned_intern_or_404(req.intern_id, db, current_user)
    result = predict_project_success_probability(intern_id=req.intern_id, db=db)
    return _save_and_respond(req.intern_id, "project_success_probability", result, db)


@router.get("/mentor-workload")
def get_mentor_workload(db: Session = Depends(get_db),
                         current_user=Depends(require_role("admin", "mentor"))):
    """
    Mentor Workload - pure SQL, no ML model. Counts each mentor's
    currently active interns against their max_capacity, so this is a
    genuine comparison (current load vs capacity), not just a headcount.
    """
    results = (
        db.query(
            Mentor.mentor_id,
            Mentor.name,
            Mentor.max_capacity,
            func.count(Intern.intern_id).label("active_interns"),
        )
        .outerjoin(Intern, (Intern.mentor_id == Mentor.mentor_id) & (Intern.status == "active"))
        .group_by(Mentor.mentor_id, Mentor.name, Mentor.max_capacity)
        .all()
    )

    return [
        {
            "mentor_id": r.mentor_id,
            "name": r.name,
            "active_interns": r.active_interns,
            "max_capacity": r.max_capacity,
            "utilization_pct": round(100 * r.active_interns / r.max_capacity, 1) if r.max_capacity else None,
            "overloaded": r.active_interns > r.max_capacity if r.max_capacity else False,
        }
        for r in results
    ]


@router.get("/history/{intern_id}", response_model=list[PredictionOut])
def prediction_history(intern_id: int, db: Session = Depends(get_db),
                        current_user=Depends(require_role("admin", "mentor", "student"))):
    _get_owned_intern_or_404(intern_id, db, current_user)
    records = db.query(Prediction).filter(Prediction.intern_id == intern_id).all()
    return [
        PredictionOut(
            intern_id=r.intern_id,
            prediction_type=r.prediction_type,
            predicted_value=float(r.predicted_value),
            confidence=float(r.confidence) if r.confidence is not None else None,
            explanation=r.explanation_json,
            created_at=r.created_at,
        )
        for r in records
    ]