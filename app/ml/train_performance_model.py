"""
Training for Model 5: Performance Trend
==========================================
3-class classification (declining / stable / improving) using ONLY
early-period features (see build_performance_dataset.py).

Class imbalance handling here uses `sample_weight` instead of
`scale_pos_weight` - scale_pos_weight is XGBoost's binary-only imbalance
knob, so for 3 classes we compute balanced per-row weights instead
(sklearn's compute_sample_weight('balanced', ...)), which has the same
effect: rare classes count more during training.

NOTE: MLflow logging is wrapped so the script still runs and saves
results even if the MLflow container isn't up - it just skips the
logging step in that case instead of crashing.

Usage:
    python -m app.ml.train_performance_model
"""
import json
import os

import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import (
    accuracy_score, classification_report, precision_recall_fscore_support,
    confusion_matrix
)
from sklearn.utils.class_weight import compute_sample_weight

from app.ml.build_performance_dataset import build_performance_dataset

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)

LABEL_MAP = {"declining": 0, "stable": 1, "improving": 2}
LABEL_NAMES = ["declining", "stable", "improving"]

PARAM_GRID = {
    "n_estimators": [100, 200, 300],
    "max_depth": [3, 4, 5],
    "learning_rate": [0.01, 0.05, 0.1],
}


def train_trend_model(X=None, y=None):
    if X is None or y is None:
        X, y = build_performance_dataset()

    y_enc = y.map(LABEL_MAP)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    print(f"Dataset: {X.shape[0]} rows, {X.shape[1]} feature columns")
    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}\n")

    # --- Class imbalance handling (multiclass) ---
    sample_weights = compute_sample_weight(class_weight="balanced", y=y_train)

    base_model = xgb.XGBClassifier(eval_metric="mlogloss", random_state=42)

    # GridSearchCV can't pass sample_weight through cv folds automatically
    # in older sklearn/xgboost combos, so we tune using unweighted CV
    # first (still finds good structural params), then refit the final
    # chosen params WITH sample weights on the full training set.
    print("Tuning hyperparameters...")
    search = GridSearchCV(base_model, PARAM_GRID, scoring="f1_macro", cv=5, n_jobs=-1)
    search.fit(X_train, y_train)
    best_params = search.best_params_
    print(f"Best params (Performance Trend): {best_params}\n")

    final_model = xgb.XGBClassifier(eval_metric="mlogloss", random_state=42, **best_params)
    final_model.fit(X_train, y_train, sample_weight=sample_weights)

    preds = final_model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, preds, average="macro", zero_division=0
    )
    cm = confusion_matrix(y_test, preds)

    print("=== Performance Trend Model (tuned) ===")
    print(classification_report(y_test, preds, target_names=LABEL_NAMES, zero_division=0))
    print(f"Accuracy: {acc:.3f}")
    print(f"\nConfusion Matrix (rows=actual, cols=predicted, order={LABEL_NAMES}):\n{cm}\n")

    # --- MLflow logging (optional - skipped safely if unreachable) ---
    try:
        import mlflow
        import mlflow.xgboost
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
        mlflow.set_experiment("intern_performance_trend")
        with mlflow.start_run(run_name="performance_trend_xgb_tuned"):
            mlflow.log_params(best_params)
            mlflow.log_metric("accuracy", acc)
            mlflow.log_metric("precision", precision)
            mlflow.log_metric("recall", recall)
            mlflow.log_metric("f1_score", f1)
            mlflow.xgboost.log_model(final_model, "model")
        print("Logged run to MLflow.\n")
    except Exception as e:
        print(f"(MLflow logging skipped - {type(e).__name__}: not connected. This is fine, results are still saved locally below.)\n")

    # --- Save model + metrics for the evaluation report ---
    final_model.save_model(os.path.join(SAVED_MODELS_DIR, "performance_trend_xgb.json"))

    metrics = {
        "model_type": "3-class (declining/stable/improving)",
        "accuracy": round(float(acc), 4),
        "precision_macro": round(float(precision), 4),
        "recall_macro": round(float(recall), 4),
        "f1_macro": round(float(f1), 4),
        "confusion_matrix": cm.tolist(),
        "label_names": LABEL_NAMES,
        "best_params": best_params,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "features_used": list(X.columns),
    }
    with open(os.path.join(SAVED_MODELS_DIR, "performance_trend_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(SAVED_MODELS_DIR, "performance_trend_features.json"), "w") as f:
        json.dump(list(X.columns), f, indent=2)
    print("Saved model + metrics to app/ml/saved_models/")

    return {
        "model": "Performance Trend", "accuracy": acc, "precision": precision,
        "recall": recall, "f1_score": f1, "roc_auc": None,
        "best_params": best_params,
    }


if __name__ == "__main__":
    train_trend_model()
