"""
Model Training Script — run manually during Week 2.

Usage:
    python -m app.ml.train

WEEK 2 TODO:
  1. Pull feature vectors + labels for all interns from the DB
     (labels = did they actually drop out / what was their final score, etc.
      — for synthetic data, you define these labels yourself when generating it)
  2. Split train/test
  3. Train XGBoost/LightGBM models
  4. Evaluate (accuracy, precision, recall, ROC-AUC)
  5. Log run + metrics + model to MLflow (http://localhost:5000)
  6. Save the trained model to app/ml/saved_models/
"""
import os
import mlflow
import mlflow.xgboost
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
mlflow.set_experiment("intern_dropout_risk")

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)


def load_training_data():
    """
    TODO: Replace with a real query that pulls feature vectors + labels
    for every intern in the dataset (built via app/ml/features.py).
    Returns X (features DataFrame) and y (labels Series).
    """
    raise NotImplementedError(
        "Hook this up to your DB once the synthetic dataset is generated (Week 1, Day 3)."
    )


def train_dropout_model():
    X, y = load_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    with mlflow.start_run(run_name="dropout_risk_xgb"):
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            eval_metric="logloss",
        )
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, preds)
        auc = roc_auc_score(y_test, probs)

        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("roc_auc", auc)
        mlflow.xgboost.log_model(model, "model")

        print(classification_report(y_test, preds))
        print(f"Accuracy: {acc:.3f}  ROC-AUC: {auc:.3f}")

        model.save_model(os.path.join(SAVED_MODELS_DIR, "dropout_risk_xgb.json"))

    return model


if __name__ == "__main__":
    train_dropout_model()
