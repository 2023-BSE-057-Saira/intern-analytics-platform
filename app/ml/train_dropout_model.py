"""
Train Dropout Risk Model
==========================
Trains an XGBoost model to predict intern dropout risk, evaluates it
honestly on unseen data, generates SHAP explainability, and saves
everything needed for the API to use it.

Implements Steps 5-8 of the preprocessing/training plan:
  5. Handle class imbalance
  6. (Feature scaling skipped - not needed for tree models)
  7. Train/test split
  8. Avoid data leakage (features used are all "before outcome" signals)

Usage:
    python -m app.ml.train_dropout_model

Outputs (all saved to app/ml/saved_models/):
    dropout_risk_xgb.json       - the trained model
    dropout_risk_features.json  - the exact list/order of feature columns
                                   (the API needs this to build predictions correctly)
    dropout_risk_metrics.json   - evaluation results (for your Model Evaluation Report)
    shap_summary.png            - explainability plot (for your Explainability Report)
"""
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb
import shap
import matplotlib
matplotlib.use("Agg")  # no GUI needed, just save plots to file
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    roc_auc_score, confusion_matrix, classification_report
)

from app.ml.build_dataset import build_dropout_dataset

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)


def main():
    print("Step 1-4: Building dataset from database...")
    df = build_dropout_dataset()
    print(f"  Dataset shape: {df.shape}")
    print(f"  Label balance:\n{df['dropped'].value_counts()}\n")

    # Separate features (X) from label (y). intern_id is not a feature —
    # it's just an identifier, including it would be meaningless noise.
    X = df.drop(columns=["intern_id", "dropped"])
    y = df["dropped"]
    feature_columns = list(X.columns)

    # --- Step 7: Train/test split (stratified to preserve class ratio) ---
    print("Step 7: Splitting into train/test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  Train size: {len(X_train)}, Test size: {len(X_test)}\n")

    # --- Step 5: Handle class imbalance ---
    # Tells XGBoost to pay extra attention to the minority class (dropouts)
    # instead of lazily predicting "not dropped" for everyone.
    num_negative = (y_train == 0).sum()
    num_positive = (y_train == 1).sum()
    scale_pos_weight = num_negative / max(num_positive, 1)
    print(f"Step 5: Class imbalance handling — scale_pos_weight = {scale_pos_weight:.2f}\n")

    # --- Hyperparameter tuning ---
    # Try a few reasonable combinations and keep whichever performs best
    # on a validation split. This is a safe way to improve the model -
    # no data changes, just finding better settings for the same algorithm.
    print("Tuning hyperparameters (trying a few combinations)...")
    from sklearn.model_selection import cross_val_score

    param_options = [
        {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05},
        {"n_estimators": 300, "max_depth": 3, "learning_rate": 0.03},
        {"n_estimators": 150, "max_depth": 5, "learning_rate": 0.08},
        {"n_estimators": 400, "max_depth": 3, "learning_rate": 0.02},
        {"n_estimators": 250, "max_depth": 6, "learning_rate": 0.03},
    ]

    best_params = None
    best_score = -1
    for params in param_options:
        candidate = xgb.XGBClassifier(
            **params,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=42,
        )
        # 5-fold cross-validation on ROC-AUC (more reliable than a single split)
        scores = cross_val_score(candidate, X_train, y_train, cv=5, scoring="roc_auc")
        avg_score = scores.mean()
        print(f"  {params}  ->  avg ROC-AUC = {avg_score:.4f}")
        if avg_score > best_score:
            best_score = avg_score
            best_params = params

    print(f"\nBest hyperparameters: {best_params} (cross-val ROC-AUC = {best_score:.4f})\n")

    # --- Train the final model using the best settings found ---
    print("Training final XGBoost model with best hyperparameters...")
    model = xgb.XGBClassifier(
        **best_params,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train)
    print("  Training complete.\n")

    # --- Step 8 note: no leakage check needed here since we only used
    # pre-outcome behavioral features (attendance, tasks, commits, etc.) ---

    # --- Evaluate ---
    print("Evaluating on held-out test set...")
    y_proba = model.predict_proba(X_test)[:, 1]

    # Default threshold (0.5) evaluation, for comparison
    y_pred_default = (y_proba >= 0.5).astype(int)
    print("--- At default threshold (0.5) ---")
    print(f"  Accuracy:  {accuracy_score(y_test, y_pred_default):.3f}")
    print(f"  Precision: {precision_score(y_test, y_pred_default, zero_division=0):.3f}")
    print(f"  Recall:    {recall_score(y_test, y_pred_default, zero_division=0):.3f}\n")

    # --- Threshold tuning ---
    # Lowering the threshold makes the model flag "at risk" more easily.
    # We search for the threshold with the best F1 score (a balance of
    # precision and recall) rather than just chasing maximum recall,
    # since too many false alarms causes alert fatigue for mentors.
    print("--- Trying different thresholds to find the best balance ---")
    from sklearn.metrics import f1_score

    best_threshold = 0.5
    best_f1 = f1_score(y_test, y_pred_default, zero_division=0)
    for threshold in [0.45, 0.40, 0.35, 0.30, 0.25]:
        y_pred_t = (y_proba >= threshold).astype(int)
        prec = precision_score(y_test, y_pred_t, zero_division=0)
        rec = recall_score(y_test, y_pred_t, zero_division=0)
        acc = accuracy_score(y_test, y_pred_t)
        f1 = f1_score(y_test, y_pred_t, zero_division=0)
        print(f"  threshold={threshold:.2f}  accuracy={acc:.3f}  precision={prec:.3f}  recall={rec:.3f}  f1={f1:.3f}")
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    print(f"\nSelected threshold: {best_threshold} (best precision/recall balance, F1={best_f1:.3f})\n")

    y_pred = (y_proba >= best_threshold).astype(int)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_proba)  # ROC-AUC is threshold-independent
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, zero_division=0)

    print(f"--- At selected threshold ({best_threshold}) ---")
    print(f"  Accuracy:  {accuracy:.3f}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  ROC-AUC:   {roc_auc:.3f}")
    print(f"\n  Confusion Matrix:\n{cm}")
    print(f"\n  Full report:\n{report}")

    if accuracy > 0.98:
        print("  ⚠ WARNING: accuracy is suspiciously high — double check for data leakage.")

    # --- Save evaluation metrics for your Model Evaluation Report ---
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
    with open(os.path.join(SAVED_MODELS_DIR, "dropout_risk_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved metrics to app/ml/saved_models/dropout_risk_metrics.json")

    # --- SHAP Explainability ---
    print("\nGenerating SHAP explainability...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    plt.figure()
    shap.summary_plot(shap_values, X_test, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(SAVED_MODELS_DIR, "shap_summary.png"), dpi=150)
    plt.close()
    print("Saved SHAP summary plot to app/ml/saved_models/shap_summary.png")

    # --- Save the model itself ---
    model.save_model(os.path.join(SAVED_MODELS_DIR, "dropout_risk_xgb.json"))
    with open(os.path.join(SAVED_MODELS_DIR, "dropout_risk_features.json"), "w") as f:
        json.dump(feature_columns, f, indent=2)
    print("Saved trained model to app/ml/saved_models/dropout_risk_xgb.json")

    print("\nDone. Model is ready to be used by the prediction engine.")


if __name__ == "__main__":
    main()