"""
Prediction Engine
====================
Loads the 4 trained models and runs live predictions for a single
intern. Each model was trained on a DIFFERENT feature set (see each
build_*.py file), so this file has a dedicated feature-extraction
helper per model that exactly matches what that model was trained on -
using the wrong feature set here (even with the right model file)
would silently produce garbage predictions.

Models used:
  - Dropout Risk          -> shared features.py (build_feature_vector)
  - Performance Trend     -> shared features.py (same features, minus
                              the leaky columns dropped during training)
  - Success Probability   -> its own feature set (build_success_dataset.py)
  - Learning Speed/Skill Growth -> its own early-period feature set
                              (build_growth_dataset.py)
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sqlalchemy.orm import Session

from app.models.db_models import (
    Intern, Attendance, Task, GithubActivity, CodeReview, MentorFeedback
)
from app.ml.features import build_feature_vector

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")

TECHNOLOGIES = ["Laravel", "MERN Stack", "Artificial Intelligence", "Flutter", "UI/UX", "DevOps"]


# ============================================================
# Generic helpers
# ============================================================

def _load_xgb_classifier(model_filename: str) -> xgb.XGBClassifier:
    model = xgb.XGBClassifier()
    model.load_model(os.path.join(SAVED_MODELS_DIR, model_filename))
    return model


def _load_feature_list(features_filename: str) -> list:
    path = os.path.join(SAVED_MODELS_DIR, features_filename)
    with open(path) as f:
        return json.load(f)


def _load_metrics(filename: str) -> dict:
    path = os.path.join(SAVED_MODELS_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def _technology_onehot(technology: str) -> dict:
    """Matches pd.get_dummies(columns=['technology'], prefix='tech') from training."""
    return {f"tech_{t}": 1 if t == technology else 0 for t in TECHNOLOGIES}


def _align_to_features(raw_features: dict, feature_list: list) -> pd.DataFrame:
    """
    Builds a single-row DataFrame containing EXACTLY the columns the
    model was trained on, in the same order, filling anything missing
    with 0. This is what makes it safe to pass a raw feature dict that
    might have extra/differently-ordered keys - reindexing guarantees
    a match regardless.
    """
    row = pd.DataFrame([raw_features])
    row = row.reindex(columns=feature_list, fill_value=0)
    return row


def _shap_explanation(model: xgb.XGBClassifier, row: pd.DataFrame, top_n: int = 3,
                       class_index: int = None) -> dict:
    """
    Returns the top contributing features for this one prediction.

    class_index: for multi-class models (e.g. Performance Trend's 3
    classes), SHAP returns a separate set of values PER CLASS - we
    need to pick out the ones for the class that was actually
    predicted, not just grab the first array blindly (that's what
    caused a ValueError on 3-class predictions - the shapes didn't
    line up with a plain binary assumption).
    """
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(row)

        if class_index is not None:
            # Multi-class: shap_values is either a list of arrays (one
            # per class) or a single 3D array (samples, features, classes)
            # depending on the SHAP/XGBoost version - handle both.
            if isinstance(shap_values, list):
                values = shap_values[class_index][0]
            else:
                values = shap_values[0, :, class_index]
        else:
            # Binary: single array, or a list with one entry for the
            # positive class.
            values = shap_values[0] if not isinstance(shap_values, list) else shap_values[0][0]

        contributions = sorted(
            zip(row.columns, values), key=lambda x: abs(x[1]), reverse=True
        )[:top_n]
        return {
            "top_factors": [
                {"feature": feat, "contribution": round(float(val), 4)}
                for feat, val in contributions
            ]
        }
    except Exception as e:
        return {"note": f"SHAP explanation unavailable ({type(e).__name__}: {str(e)[:100]})"}


# ============================================================
# Model 1: Dropout Risk
# ============================================================

def predict_dropout_risk(intern_id: int, db: Session) -> dict:
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    raw_features = build_feature_vector(intern_id, db)
    raw_features.update(_technology_onehot(intern.technology))

    feature_list = _load_feature_list("dropout_risk_features.json")
    row = _align_to_features(raw_features, feature_list)

    model = _load_xgb_classifier("dropout_risk_xgb.json")
    probability = float(model.predict_proba(row)[0][1])

    metrics = _load_metrics("dropout_risk_metrics.json")
    threshold = metrics.get("decision_threshold", 0.5) if metrics else 0.5

    explanation = _shap_explanation(model, row)
    explanation["flagged_as_at_risk"] = probability >= threshold
    explanation["decision_threshold"] = threshold

    return {"value": probability, "confidence": None, "explanation": explanation}


# ============================================================
# Model 2: Performance Trend (3-class: declining/stable/improving)
# ============================================================

def predict_performance_trend(intern_id: int, db: Session) -> dict:
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    raw_features = build_feature_vector(intern_id, db)
    raw_features.update(_technology_onehot(intern.technology))

    feature_list = _load_feature_list("performance_trend_features.json")
    row = _align_to_features(raw_features, feature_list)

    model = _load_xgb_classifier("performance_trend_xgb.json")
    probabilities = model.predict_proba(row)[0]
    predicted_class = int(np.argmax(probabilities))
    confidence = float(probabilities[predicted_class])

    label_names = ["declining", "stable", "improving"]
    predicted_label = label_names[predicted_class]

    explanation = _shap_explanation(model, row, class_index=predicted_class)
    explanation["predicted_label"] = predicted_label
    explanation["class_probabilities"] = {
        name: round(float(p), 4) for name, p in zip(label_names, probabilities)
    }

    # predicted_value stores the class as a number (0=declining, 1=stable,
    # 2=improving) - the human-readable label is in the explanation.
    return {"value": float(predicted_class), "confidence": confidence, "explanation": explanation}


# ============================================================
# Model 3: Success Probability
# ============================================================

def _build_success_features_single(intern_id: int, db: Session) -> dict:
    """
    Matches build_success_dataset.py's exact columns for ONE intern.
    NOTE: intentionally does NOT include avg_review_score - it was
    used to build the training label, so including it here would be
    the same leakage bug we already fixed once during training.
    """
    attendance = db.query(Attendance).filter(Attendance.intern_id == intern_id).all()
    tasks = db.query(Task).filter(Task.intern_id == intern_id).all()
    github = db.query(GithubActivity).filter(GithubActivity.intern_id == intern_id).all()
    reviews = db.query(CodeReview).filter(CodeReview.intern_id == intern_id).all()
    feedback = db.query(MentorFeedback).filter(MentorFeedback.intern_id == intern_id).all()

    total_days = len(attendance) or 1
    attendance_rate = sum(1 for a in attendance if a.present) / total_days

    total_tasks = len(tasks) or 1
    completed_tasks = sum(1 for t in tasks if t.status == "completed")
    late_tasks = sum(1 for t in tasks if t.status == "late")
    skipped_tasks = sum(1 for t in tasks if t.status == "skipped")
    task_completion_rate = completed_tasks / total_tasks

    total_commits = sum(g.commits for g in github)
    total_prs = sum(g.pull_requests for g in github)
    num_reviews = len(reviews)
    avg_mentor_rating = (
        sum(float(f.rating) for f in feedback if f.rating is not None) / len(feedback)
        if feedback else 0.0
    )
    total_messages = 0  # placeholder default matched to training's fillna default
    total_meetings = 0

    return {
        "attendance_rate": attendance_rate,
        "task_completion_rate": task_completion_rate,
        "late_tasks": late_tasks,
        "skipped_tasks": skipped_tasks,
        "total_commits": total_commits,
        "total_prs": total_prs,
        "num_reviews": num_reviews,
        "avg_mentor_rating": avg_mentor_rating,
        "total_messages": total_messages,
        "total_meetings": total_meetings,
    }


def predict_success_probability(intern_id: int, db: Session) -> dict:
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    raw_features = _build_success_features_single(intern_id, db)
    raw_features.update(_technology_onehot(intern.technology))

    feature_list = _load_feature_list("success_probability_features.json")
    row = _align_to_features(raw_features, feature_list)

    model = _load_xgb_classifier("success_probability_xgb.json")
    probability = float(model.predict_proba(row)[0][1])

    metrics = _load_metrics("success_probability_metrics.json")
    threshold = metrics.get("decision_threshold", 0.5) if metrics else 0.5

    explanation = _shap_explanation(model, row)
    explanation["predicted_success"] = probability >= threshold
    explanation["decision_threshold"] = threshold

    return {"value": probability, "confidence": None, "explanation": explanation}


# ============================================================
# Model 4: Learning Speed & Skill Growth (regression)
# ============================================================

def _early_split_single(records: list, date_attr: str, value_fn) -> float:
    """Early-half average for one intern's records - matches build_growth_dataset.py."""
    if len(records) < 2:
        return 0.0
    sorted_records = sorted(records, key=lambda r: getattr(r, date_attr))
    mid = len(sorted_records) // 2
    early = sorted_records[:mid]
    return sum(value_fn(r) for r in early) / len(early) if early else 0.0


def _early_trend_single(records: list, date_attr: str, value_fn) -> float:
    """Trend within the early half only - matches build_growth_dataset.py."""
    if len(records) < 4:
        return 0.0
    sorted_records = sorted(records, key=lambda r: getattr(r, date_attr))
    early_half = sorted_records[: len(sorted_records) // 2]
    q1 = early_half[: len(early_half) // 2]
    q2 = early_half[len(early_half) // 2:]
    q1_mean = sum(value_fn(r) for r in q1) / len(q1) if q1 else 0.0
    q2_mean = sum(value_fn(r) for r in q2) / len(q2) if q2 else 0.0
    return q2_mean - q1_mean


def _build_growth_features_single(intern_id: int, db: Session) -> dict:
    attendance = db.query(Attendance).filter(Attendance.intern_id == intern_id).all()
    tasks = db.query(Task).filter(Task.intern_id == intern_id).all()
    github = db.query(GithubActivity).filter(GithubActivity.intern_id == intern_id).all()
    reviews = db.query(CodeReview).filter(CodeReview.intern_id == intern_id).all()
    feedback = db.query(MentorFeedback).filter(MentorFeedback.intern_id == intern_id).all()

    attendance_early = _early_split_single(attendance, "date", lambda a: 1.0 if a.present else 0.0)
    completion_early = _early_split_single(tasks, "assigned_date", lambda t: 1.0 if t.status == "completed" else 0.0)
    commits_early = _early_split_single(github, "date", lambda g: g.commits)
    review_early = _early_split_single(reviews, "review_date", lambda r: float(r.score) if r.score is not None else 0.0)
    mentor_rating_early = _early_split_single(feedback, "date", lambda f: float(f.rating) if f.rating is not None else 0.0)

    attendance_early_trend = _early_trend_single(attendance, "date", lambda a: 1.0 if a.present else 0.0)
    completion_early_trend = _early_trend_single(tasks, "assigned_date", lambda t: 1.0 if t.status == "completed" else 0.0)

    return {
        "attendance_early": attendance_early,
        "completion_early": completion_early,
        "commits_early": commits_early,
        "review_early": review_early,
        "mentor_rating_early": mentor_rating_early,
        "attendance_early_trend": attendance_early_trend,
        "completion_early_trend": completion_early_trend,
    }


def predict_learning_growth(intern_id: int, db: Session) -> dict:
    """Returns BOTH learning_speed and skill_growth predictions."""
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    raw_features = _build_growth_features_single(intern_id, db)
    raw_features.update(_technology_onehot(intern.technology))

    feature_list = _load_feature_list("growth_features.json")
    row = _align_to_features(raw_features, feature_list)

    scaler = joblib.load(os.path.join(SAVED_MODELS_DIR, "growth_scaler.pkl"))
    model = joblib.load(os.path.join(SAVED_MODELS_DIR, "growth_model.pkl"))

    row_scaled = scaler.transform(row)
    predictions = model.predict(row_scaled)[0]

    return {
        "value": float(predictions[0]),  # learning_speed
        "confidence": None,
        "explanation": {
            "learning_speed": round(float(predictions[0]), 4),
            "skill_growth": round(float(predictions[1]), 4),
            "note": "Positive values indicate improvement, negative indicate decline.",
        },
    }


# ============================================================
# Derived predictions (no separate model - math/reuse only)
# ============================================================

def predict_completion_probability(intern_id: int, db: Session) -> dict:
    """Completion Probability = 1 - Dropout Risk. No separate model needed."""
    dropout_result = predict_dropout_risk(intern_id, db)
    completion_prob = 1.0 - dropout_result["value"]
    return {
        "value": completion_prob,
        "confidence": None,
        "explanation": {"derived_from": "1 - dropout_risk", "dropout_risk": dropout_result["value"]},
    }


def predict_project_success_probability(intern_id: int, db: Session) -> dict:
    """
    Project Success Probability - reuses the Success Probability model.
    Documented approximation: we don't track per-project data separately
    from overall intern performance in this system, so project-level
    success is approximated using the intern's overall success signal.
    """
    result = predict_success_probability(intern_id, db)
    result["explanation"]["note"] = "Approximated using overall Success Probability model (no separate per-project data tracked)."
    return result


def calculate_mentor_workload(db: Session) -> list:
    """
    Mentor Workload - pure SQL, no ML model. Returns each mentor's
    current active-intern load vs their max_capacity.
    """
    from app.models.db_models import Mentor, Intern
    from sqlalchemy import func

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
            "utilization": (r.active_interns / r.max_capacity) if r.max_capacity else 0,
            "overloaded": r.active_interns > r.max_capacity if r.max_capacity else False,
        }
        for r in results
    ]
