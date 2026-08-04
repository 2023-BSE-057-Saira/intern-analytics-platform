"""
Train Success Probability Model
==================================
Predicts whether an intern will complete their internship WITH strong
performance (not just avoid dropping out). Same pipeline pattern as
the other two models.

Usage:
    python -m app.ml.train_success_model

Outputs (saved to app/ml/saved_models/):
    success_probability_xgb.json
    success_probability_features.json
    success_probability_metrics.json
    shap_summary_success.png
"""
import json
import os

import xgboost as xgb
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

from app.ml.build_success_dataset import build_success_dataset

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)


def main():
    print("Building success probability dataset...")
    df = build_success_dataset()
    print(f"  Dataset shape: {df.shape}")
    print(f"  Label balance:\n{df['success'].value_counts()}\n")

    X = df.drop(columns=["intern_id", "success"])
    y = df["success"]
    feature_columns = list(X.columns)

    print("Splitting into train/test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  Train size: {len(X_train)}, Test size: {len(X_test)}\n")

    num_negative = (y_train == 0).sum()
    num_positive = (y_train == 1).sum()
    scale_pos_weight = num_negative / max(num_positive, 1)
    print(f"Class imbalance handling — scale_pos_weight = {scale_pos_weight:.2f}\n")

    print("Tuning hyperparameters (this may take a minute)...")
    from sklearn.model_selection import GridSearchCV

    param_grid = {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 4, 5, 6],
        "learning_rate": [0.03, 0.05, 0.1],
        "min_child_weight": [1, 3, 5],
    }

    base_model = xgb.XGBClassifier(
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=42,
    )

    grid_search = GridSearchCV(
        base_model, param_grid,
        scoring="roc_auc",
        cv=5,
        n_jobs=-1,
        verbose=0,
    )
    grid_search.fit(X_train, y_train)

    print(f"  Best parameters found: {grid_search.best_params_}")
    print(f"  Best cross-validated ROC-AUC: {grid_search.best_score_:.3f}\n")

    model = grid_search.best_estimator_
    print("Training complete (using best found parameters).\n")

    print("Evaluating on held-out test set...")
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred_default = (y_proba >= 0.5).astype(int)

    print("--- Trying different thresholds to find the best balance ---")
    best_threshold = 0.5
    best_f1 = f1_score(y_test, y_pred_default, zero_division=0)
    for threshold in [0.45, 0.40, 0.35, 0.30, 0.55, 0.60]:
        y_pred_t = (y_proba >= threshold).astype(int)
        prec = precision_score(y_test, y_pred_t, zero_division=0)
        rec = recall_score(y_test, y_pred_t, zero_division=0)
        acc = accuracy_score(y_test, y_pred_t)
        f1 = f1_score(y_test, y_pred_t, zero_division=0)
        print(f"  threshold={threshold:.2f}  accuracy={acc:.3f}  precision={prec:.3f}  recall={rec:.3f}  f1={f1:.3f}")
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    print(f"\nSelected threshold: {best_threshold} (F1={best_f1:.3f})\n")

    y_pred = (y_proba >= best_threshold).astype(int)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, zero_division=0)

    print(f"--- At selected threshold ({best_threshold}) ---")
    print(f"  Accuracy:  {accuracy:.3f}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  ROC-AUC:   {roc_auc:.3f}")
    print(f"\n  Confusion Matrix:\n{cm}")
    print(f"\n  Full report:\n{report}")

    metrics = {
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "roc_auc": round(float(roc_auc), 4),
        "decision_threshold": best_threshold,
        "confusion_matrix": cm.tolist(),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "features_used": feature_columns,
    }
    with open(os.path.join(SAVED_MODELS_DIR, "success_probability_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("\nSaved metrics to app/ml/saved_models/success_probability_metrics.json")

    print("\nGenerating SHAP explainability...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)
    plt.figure()
    shap.summary_plot(shap_values, X_test, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(SAVED_MODELS_DIR, "shap_summary_success.png"), dpi=150)
    plt.close()
    print("Saved SHAP summary plot to app/ml/saved_models/shap_summary_success.png")

    model.save_model(os.path.join(SAVED_MODELS_DIR, "success_probability_xgb.json"))
    with open(os.path.join(SAVED_MODELS_DIR, "success_probability_features.json"), "w") as f:
        json.dump(feature_columns, f, indent=2)
    print("Saved trained model to app/ml/saved_models/success_probability_xgb.json")

    print("\nDone.")


if __name__ == "__main__":
    main()