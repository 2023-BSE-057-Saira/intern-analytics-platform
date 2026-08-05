"""
app/routers/mentor.py
========================
Aggregated data for the Mentor dashboard — scoped to the logged-in
mentor's own interns only (never another mentor's roster).

Mentor-only. Uses current_user.mentor_id from the JWT, not a URL
parameter, so a mentor can never view another mentor's dashboard by
editing the URL.
"""
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Intern, Mentor, Prediction, Recommendation
from app.security import require_role

router = APIRouter(prefix="/mentor", tags=["Mentor"])


def _latest_predictions_by_intern(db: Session, intern_ids: list) -> dict:
    """Same logic as the admin overview: most recent prediction per (intern, type)."""
    latest = {}
    preds = (
        db.query(Prediction)
        .filter(Prediction.intern_id.in_(intern_ids))
        .order_by(Prediction.created_at.desc())
        .all()
    )
    for p in preds:
        key = (p.intern_id, p.prediction_type)
        if key not in latest:
            latest[key] = p

    by_intern = defaultdict(dict)
    for (intern_id, ptype), pred in latest.items():
        by_intern[intern_id][ptype] = float(pred.predicted_value)
        if ptype == "performance_trend" and pred.explanation_json:
            label = pred.explanation_json.get("predicted_label")
            if label:
                by_intern[intern_id]["performance_trend_label"] = label
    return by_intern


def _intern_summary(intern: Intern, preds: dict) -> dict:
    return {
        "intern_id": intern.intern_id,
        "name": intern.name,
        "technology": intern.technology,
        "batch": intern.batch,
        "status": intern.status,
        "dropout_risk": preds.get("dropout_risk"),
        "success_probability": preds.get("success_probability"),
        "performance_trend": preds.get("performance_trend_label"),
    }


@router.get("/overview")
def get_mentor_overview(db: Session = Depends(get_db),
                         current_user=Depends(require_role("mentor"))):
    if not current_user.mentor_id:
        raise HTTPException(status_code=400, detail="This account isn't linked to a mentor record.")

    mentor = db.query(Mentor).filter(Mentor.mentor_id == current_user.mentor_id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor record not found.")

    interns = db.query(Intern).filter(Intern.mentor_id == mentor.mentor_id).all()
    intern_ids = [i.intern_id for i in interns]
    preds_by_intern = _latest_predictions_by_intern(db, intern_ids) if intern_ids else {}

    summaries = [_intern_summary(i, preds_by_intern.get(i.intern_id, {})) for i in interns]
    active_interns = [s for s in summaries if s["status"] == "active"]

    weak_students = [
        s for s in summaries
        if (s["dropout_risk"] is not None and s["dropout_risk"] > 0.5)
        or s["performance_trend"] == "declining"
    ]
    strong_students = [
        s for s in summaries
        if s["success_probability"] is not None and s["success_probability"] > 0.85
    ]

    active_count = len(active_interns)
    capacity = mentor.max_capacity
    utilization_pct = round(100 * active_count / capacity, 1) if capacity else None
    overloaded = active_count > capacity if capacity else False

    # --- Weekly AI suggestions: most recent recommendation per intern ---
    suggestions = []
    if intern_ids:
        recs = (
            db.query(Recommendation)
            .filter(Recommendation.intern_id.in_(intern_ids))
            .order_by(Recommendation.created_at.desc())
            .all()
        )
        seen_interns = set()
        intern_names = {i.intern_id: i.name for i in interns}
        for r in recs:
            if r.intern_id in seen_interns:
                continue
            seen_interns.add(r.intern_id)
            suggestions.append({
                "intern_id": r.intern_id,
                "intern_name": intern_names.get(r.intern_id, "—"),
                "type": r.recommendation_type,
                "message": r.message,
            })

    return {
        "mentor": {
            "mentor_id": mentor.mentor_id,
            "name": mentor.name,
            "active_interns": active_count,
            "max_capacity": capacity,
            "utilization_pct": utilization_pct,
            "overloaded": overloaded,
        },
        "roster": summaries,
        "weak_students": weak_students,
        "strong_students": strong_students,
        "recommendations": [
            {
                "intern_id": s["intern_id"],
                "intern_name": s["intern_name"],
                "recommendation_type": s["type"],
                "message": s["message"],
            }
            for s in suggestions
        ],
    }
