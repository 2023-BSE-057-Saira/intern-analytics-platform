"""
app/routers/admin.py
========================
Aggregated data for the Admin dashboard. Mirrors what the old
Streamlit dashboard did with raw pandas SQL queries, but through the
API so the HTML/JS frontend has one endpoint to call instead of
looping per-intern requests.

Admin-only.
"""
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Intern, Prediction
from app.security import require_role

router = APIRouter(prefix="/admin", tags=["Admin"])


def _latest_predictions_by_intern(db: Session) -> dict:
    """
    Returns { intern_id: { prediction_type: predicted_value, ... }, ... }
    using only the most recent prediction per (intern, type) — matches
    the "distinct on" logic the old dashboard used in raw SQL.
    """
    latest = {}
    all_preds = db.query(Prediction).order_by(Prediction.created_at.desc()).all()
    for p in all_preds:
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
        "mentor_id": intern.mentor_id,
        "dropout_risk": preds.get("dropout_risk"),
        "success_probability": preds.get("success_probability"),
        "performance_trend": preds.get("performance_trend_label"),
    }


@router.get("/overview")
def get_admin_overview(db: Session = Depends(get_db),
                        current_user=Depends(require_role("admin"))):
    interns = db.query(Intern).all()
    preds_by_intern = _latest_predictions_by_intern(db)

    summaries = [_intern_summary(i, preds_by_intern.get(i.intern_id, {})) for i in interns]

    total = len(summaries)
    active = sum(1 for s in summaries if s["status"] == "active")
    completed = sum(1 for s in summaries if s["status"] == "completed")
    dropped = sum(1 for s in summaries if s["status"] == "dropped")

    risk_values = [s["dropout_risk"] for s in summaries if s["dropout_risk"] is not None]
    success_values = [s["success_probability"] for s in summaries if s["success_probability"] is not None]
    avg_dropout_risk = sum(risk_values) / len(risk_values) if risk_values else None
    avg_success_probability = sum(success_values) / len(success_values) if success_values else None

    high_risk = sorted(
        [s for s in summaries if s["dropout_risk"] is not None and s["dropout_risk"] > 0.5],
        key=lambda s: s["dropout_risk"], reverse=True,
    )
    top_performers = sorted(
        [s for s in summaries if s["success_probability"] is not None and s["success_probability"] > 0.9],
        key=lambda s: s["success_probability"], reverse=True,
    )

    # --- Group by technology ---
    by_tech = defaultdict(list)
    for s in summaries:
        by_tech[s["technology"]].append(s)
    technology_stats = []
    for tech, rows in by_tech.items():
        r = [x["dropout_risk"] for x in rows if x["dropout_risk"] is not None]
        p = [x["success_probability"] for x in rows if x["success_probability"] is not None]
        technology_stats.append({
            "technology": tech,
            "interns": len(rows),
            "avg_dropout_risk": (sum(r) / len(r)) if r else None,
            "avg_success_probability": (sum(p) / len(p)) if p else None,
        })

    # --- Group by batch ---
    by_batch = defaultdict(list)
    for s in summaries:
        by_batch[s["batch"]].append(s)
    batch_stats = []
    for batch, rows in by_batch.items():
        r = [x["dropout_risk"] for x in rows if x["dropout_risk"] is not None]
        p = [x["success_probability"] for x in rows if x["success_probability"] is not None]
        batch_stats.append({
            "batch": batch,
            "interns": len(rows),
            "avg_dropout_risk": (sum(r) / len(r)) if r else None,
            "avg_success_probability": (sum(p) / len(p)) if p else None,
            "dropped": sum(1 for x in rows if x["status"] == "dropped"),
        })

    return {
        "totals": {"total": total, "active": active, "completed": completed, "dropped": dropped},
        "avg_dropout_risk": avg_dropout_risk,
        "avg_success_probability": avg_success_probability,
        "dropout_risk_distribution": sorted(risk_values),
        "success_probability_distribution": sorted(success_values),
        "high_risk": high_risk,
        "top_performers": top_performers,
        "by_technology": technology_stats,
        "by_batch": batch_stats,
    }
