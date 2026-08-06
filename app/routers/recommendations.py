"""
Endpoints for retrieving recommendations for an intern.
Recommendation *generation* logic lives in app/services/recommendation_engine.py
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Intern, Recommendation
from app.schemas.schemas import RecommendationOut
from app.services.recommendation_engine import generate_recommendations
from app.security import require_role

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _assert_can_view(intern: Intern, current_user) -> None:
    """Mirrors app/routers/interns.py's ownership check."""
    if current_user.role == "admin":
        return
    if current_user.role == "mentor" and current_user.mentor_id == intern.mentor_id:
        return
    if current_user.role == "student" and current_user.intern_id == intern.intern_id:
        return
    raise HTTPException(status_code=403, detail="Not authorized for this intern")


@router.post("/{intern_id}/generate", response_model=list[RecommendationOut])
def generate(intern_id: int, db: Session = Depends(get_db),
             current_user=Depends(require_role("admin", "mentor"))):
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    _assert_can_view(intern, current_user)

    recs = generate_recommendations(intern_id=intern_id, db=db)

    saved = []
    for rec in recs:
        record = Recommendation(
            intern_id=intern_id,
            recommendation_type=rec["type"],
            message=rec["message"],
        )
        db.add(record)
        saved.append(record)
    db.commit()
    for r in saved:
        db.refresh(r)
    return saved


@router.get("/{intern_id}", response_model=list[RecommendationOut])
def list_recommendations(intern_id: int, db: Session = Depends(get_db),
                          current_user=Depends(require_role("admin", "mentor", "student"))):
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    _assert_can_view(intern, current_user)
    return db.query(Recommendation).filter(Recommendation.intern_id == intern_id).all()