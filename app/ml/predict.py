"""
Prediction Engine — loads trained models and runs predictions.

WEEK 2 TODO:
  1. Train models in app/ml/train.py, save them to app/ml/saved_models/
  2. Load them here (e.g. via joblib.load or mlflow.pyfunc.load_model)
  3. Replace the dummy logic below with real feature extraction + model.predict()
  4. Add SHAP explainability (see shap.TreeExplainer for XGBoost/LightGBM)

Each function currently returns a placeholder so the API is testable
end-to-end (via Postman) before the real models exist.
"""
from sqlalchemy.orm import Session
from app.ml.features import build_feature_vector

# TODO: load your trained models once available, e.g.:
# import joblib
# dropout_model = joblib.load("app/ml/saved_models/dropout_risk_xgb.pkl")


def predict_dropout_risk(intern_id: int, db: Session) -> dict:
    features = build_feature_vector(intern_id, db)

    # --- Placeholder logic (replace with dropout_model.predict_proba) ---
    value = 0.35  # dummy risk score between 0-1
    confidence = 0.80
    explanation = {"note": "placeholder — replace with SHAP values once model is trained",
                    "features_used": list(features.keys())}
    # ----------------------------------------------------------------

    return {"value": value, "confidence": confidence, "explanation": explanation}


def predict_performance_trend(intern_id: int, db: Session) -> dict:
    features = build_feature_vector(intern_id, db)

    value = 0.60  # dummy trend score
    confidence = 0.75
    explanation = {"note": "placeholder", "features_used": list(features.keys())}

    return {"value": value, "confidence": confidence, "explanation": explanation}


def predict_success_probability(intern_id: int, db: Session) -> dict:
    features = build_feature_vector(intern_id, db)

    value = 0.72  # dummy probability
    confidence = 0.78
    explanation = {"note": "placeholder", "features_used": list(features.keys())}

    return {"value": value, "confidence": confidence, "explanation": explanation}
