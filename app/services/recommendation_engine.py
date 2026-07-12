"""
Recommendation Engine — simple, explainable rule-based logic on top of
predictions. Doesn't need to be ML itself; clear rules are preferred
here since the grading criteria value "Recommendation Quality" as
distinct from "Prediction Accuracy".

WEEK 3 TODO: tune thresholds using real prediction distributions
once your models are trained.
"""
from sqlalchemy.orm import Session
from app.ml.predict import predict_dropout_risk, predict_performance_trend


def generate_recommendations(intern_id: int, db: Session) -> list[dict]:
    recommendations = []

    dropout = predict_dropout_risk(intern_id=intern_id, db=db)
    trend = predict_performance_trend(intern_id=intern_id, db=db)

    risk_value = dropout["value"]
    trend_value = trend["value"]

    if risk_value >= 0.7:
        recommendations.append({
            "type": "mentor_intervention",
            "message": "High dropout risk detected — recommend immediate mentor check-in this week."
        })
    elif risk_value >= 0.4:
        recommendations.append({
            "type": "additional_learning_resources",
            "message": "Moderate dropout risk — suggest additional learning resources and a lighter task load."
        })

    if trend_value < 0.4:
        recommendations.append({
            "type": "easier_task",
            "message": "Performance trend is declining — assign an easier task to rebuild momentum."
        })
    elif trend_value > 0.8:
        recommendations.append({
            "type": "advanced_task",
            "message": "Performance trend is strong — assign a more advanced/stretch task."
        })

    if not recommendations:
        recommendations.append({
            "type": "personalized_weekly_goal",
            "message": "Performance is stable — set a personalized weekly goal to maintain momentum."
        })

    return recommendations
