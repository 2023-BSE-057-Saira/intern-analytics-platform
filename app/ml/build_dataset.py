"""
Build Training Dataset (v2 - using shared features.py)
==========================================================
Switched to the shared feature pipeline (app/ml/features.py) instead
of this file's own separate aggregation logic. Reasoning: features.py
includes attendance_trend / completion_trend / review_trend, plus
interaction terms and consistency measures (review_score_std,
commit_std, hard_task_completion_rate) - none of which the old
version of this file computed.

This matters specifically for Dropout Risk because the data generator
ties dropout probability to whether an intern's TRAJECTORY is
declining vs improving (see generate_synthetic_data.py's
TRAJECTORY_DROPOUT_MULTIPLIER) - a flat attendance_rate average alone
can't see that, but the trend features can.

Usage (import in other scripts):
    from app.ml.build_dataset import build_dropout_dataset
    df = build_dropout_dataset()
"""
import pandas as pd
from app.database import SessionLocal
from app.ml.features import build_features_dataframe

# Columns that either directly define the label or leak it:
# - status: this is where 'dropped' comes from
# - completed: the complementary outcome, would let the model just
#   read the answer for any intern who didn't drop
# (intern_id is kept - train_dropout_model.py drops it itself)
LEAKY_OR_ID_COLUMNS = ["status", "completed"]


def build_dropout_dataset() -> pd.DataFrame:
    """
    Returns a DataFrame with one row per intern:
    engineered features + a 'dropped' label column (1 = dropped out, 0 = did not).
    """
    db = SessionLocal()
    try:
        df = build_features_dataframe(db)
    finally:
        db.close()

    if df.empty:
        raise ValueError("No interns with enough history found - generate the dataset first.")

    df = df.fillna(0)

    # --- Only use interns whose OUTCOME IS KNOWN (dropped or completed) ---
    # 'active' interns are still ongoing - we don't know their real
    # outcome yet, so including them would just add noise/wrong answers.
    df = df[df["status"].isin(["dropped", "completed"])].copy()

    df = df.drop(columns=[c for c in LEAKY_OR_ID_COLUMNS if c in df.columns])

    return df


if __name__ == "__main__":
    dataset = build_dropout_dataset()
    print(f"Dataset shape: {dataset.shape}")
    print(f"\nColumns: {list(dataset.columns)}")
    print(f"\nLabel balance:\n{dataset['dropped'].value_counts()}")
    print(f"\nFirst few rows:\n{dataset.head()}")