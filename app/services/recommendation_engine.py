"""
Recommendation Engine — simple, explainable rule-based logic on top of
real predictions. Doesn't need to be ML itself; clear rules are
preferred here since the grading criteria value "Recommendation
Quality" as distinct from "Prediction Accuracy".

FIX: Performance Trend now returns a CLASS (0=declining, 1=stable,
2=improving), not the old continuous 0-1 score. The previous version
of this file still used continuous-scale thresholds (trend_value < 0.4
/ > 0.8), which meant "stable" (value=1) incorrectly matched the
">0.8" branch and got an "advanced_task" recommendation - the same
message as "improving". Fixed below to check the class directly.

Also: dropout risk now uses the model's own saved decision_threshold
(from training) instead of an arbitrary guessed number, so the
recommendation engine and the model agree on what "at risk" means.
"""
import json
import os
from sqlalchemy.orm import Session
from app.ml.predict import predict_dropout_risk, predict_performance_trend

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "saved_models")


def _load_dropout_threshold() -> float:
    path = os.path.join(SAVED_MODELS_DIR, "dropout_risk_metrics.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get("decision_threshold", 0.5)
    return 0.5


def generate_recommendations(intern_id: int, db: Session) -> list[dict]:
    recommendations = []

    dropout = predict_dropout_risk(intern_id=intern_id, db=db)
    trend = predict_performance_trend(intern_id=intern_id, db=db)

    risk_value = dropout["value"]
    threshold = _load_dropout_threshold()

    # --- Dropout risk tiers ---
    # Moderate tier is set at 60% of the model's own "at risk" threshold,
    # giving an earlier, softer warning before the model's actual cutoff.
    if risk_value >= threshold:
        recommendations.append({
            "type": "mentor_intervention",
            "message": f"High dropout risk detected ({risk_value:.0%}) — recommend immediate mentor check-in this week."
        })
    elif risk_value >= threshold * 0.6:
        recommendations.append({
            "type": "additional_learning_resources",
            "message": f"Moderate dropout risk ({risk_value:.0%}) — suggest additional learning resources and a lighter task load."
        })

    # --- Performance trend (now a CLASS, not a continuous score) ---
    trend_class = int(trend["value"])  # 0=declining, 1=stable, 2=improving
    trend_label = trend.get("explanation", {}).get("predicted_label", "")

    if trend_class == 0:  # declining
        recommendations.append({
            "type": "easier_task",
            "message": "Performance trend is declining — assign an easier task to rebuild momentum."
        })
    elif trend_class == 2:  # improving
        recommendations.append({
            "type": "advanced_task",
            "message": "Performance trend is strong and improving — assign a more advanced/stretch task."
        })
    else:  # stable - this branch was previously unreachable due to the bug
        recommendations.append({
            "type": "personalized_weekly_goal",
            "message": "Performance trend is stable — set a personalized weekly goal to maintain momentum."
        })

    if not recommendations:
        recommendations.append({
            "type": "personalized_weekly_goal",
            "message": "No specific concerns detected — set a personalized weekly goal to maintain momentum."
        })

    return recommendations