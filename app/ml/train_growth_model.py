"""
Train Learning Speed + Skill Growth Model
=============================================
A single Linear Regression model that predicts BOTH targets at once
(learning_speed and skill_growth) from the same early-period features.
Includes feature scaling, which Linear Regression needs (unlike the
tree-based XGBoost models).

Usage:
    python -m app.ml.train_growth_model

Outputs (saved to app/ml/saved_models/):
    growth_model.pkl              - trained model (via joblib)
    growth_scaler.pkl             - the fitted StandardScaler (needed at prediction time too)
    growth_features.json          - feature column order
    growth_metrics.json           - MAE / R2 for both targets
"""
import json
import os

import joblib
import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

from app.ml.build_growth_dataset import build_growth_dataset

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)


def main():
    print("Building Learning Speed / Skill Growth dataset...")
    df = build_growth_dataset()
    print(f"  Dataset shape: {df.shape}\n")

    X = df.drop(columns=["intern_id", "learning_speed", "skill_growth"])
    y = df[["learning_speed", "skill_growth"]]  # two targets at once
    feature_columns = list(X.columns)

    print("Splitting into train/test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"  Train size: {len(X_train)}, Test size: {len(X_test)}\n")

    # --- Feature scaling (Linear Regression needs this, unlike XGBoost) ---
    # IMPORTANT: fit the scaler ONLY on training data, then apply it to
    # test data. Fitting on the full dataset would leak test-set
    # information into the scaling step.
    print("Scaling features (fit on train only, to avoid leakage)...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("Training Linear Regression model (multi-output)...")
    model = LinearRegression()
    model.fit(X_train_scaled, y_train)
    print("  Training complete.\n")

    print("Evaluating on held-out test set...")
    y_pred = model.predict(X_test_scaled)
    y_pred_df = pd.DataFrame(y_pred, columns=["learning_speed", "skill_growth"], index=y_test.index)

    metrics = {}
    for target in ["learning_speed", "skill_growth"]:
        mae = mean_absolute_error(y_test[target], y_pred_df[target])
        r2 = r2_score(y_test[target], y_pred_df[target])
        metrics[target] = {"mae": round(float(mae), 4), "r2": round(float(r2), 4)}
        print(f"  {target}:  MAE = {mae:.4f}   R2 = {r2:.4f}")

    print(
        "\n  (MAE = average prediction error in the original units."
        "\n   R2 close to 1.0 = model explains most of the variation."
        "\n   R2 close to 0 = model is no better than guessing the average.)"
    )

    metrics["train_size"] = len(X_train)
    metrics["test_size"] = len(X_test)
    metrics["features_used"] = feature_columns

    with open(os.path.join(SAVED_MODELS_DIR, "growth_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("\nSaved metrics to app/ml/saved_models/growth_metrics.json")

    # --- Save model, scaler, and feature list ---
    joblib.dump(model, os.path.join(SAVED_MODELS_DIR, "growth_model.pkl"))
    joblib.dump(scaler, os.path.join(SAVED_MODELS_DIR, "growth_scaler.pkl"))
    with open(os.path.join(SAVED_MODELS_DIR, "growth_features.json"), "w") as f:
        json.dump(feature_columns, f, indent=2)

    print("Saved trained model to app/ml/saved_models/growth_model.pkl")
    print("Saved scaler to app/ml/saved_models/growth_scaler.pkl")
    print("\nDone.")


if __name__ == "__main__":
    main()
