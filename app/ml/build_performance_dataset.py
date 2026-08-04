"""
Preprocessing for Model 5: Performance Trend
===============================================
IMPORTANT FIX (v2): An earlier version of this file tried to detect a
trend by comparing "early half vs late half" of each intern's history.
That approach produced a near-useless model (~39% accuracy on 3
classes, barely above random). The reason: the synthetic data generator
assigns each intern a fixed profile with a CONSTANT mean behaviour for
their whole internship (only day-to-day random noise on top) - there
is no real time trend baked in, so comparing early vs late halves was
just comparing two noisy samples of the same distribution. No amount
of tuning can extract a signal that isn't there.

THE FIX: the generator DOES bake in a real, strong pattern - it's just
not a time trend. Every intern's hidden profile drives their
attendance, task completion, commits, review scores, and mentor
ratings TOGETHER (see PROFILE_RANGES in generate_synthetic_data.py -
at_risk interns get low ranges across ALL of these at once). That's a
genuine, learnable correlation.

So instead of "is this intern changing over time", Performance Trend
is reframed as "what tier is this intern's current engagement/delivery
trajectory in" - a composite of attendance_rate + task_completion_rate,
bucketed into 3 tiers. This is predicted from a DIFFERENT set of
columns (commits, review scores, mentor ratings, communication) - not
the same columns the target is built from, so there's no leakage, and
because profile correlates all of these, there IS real signal to learn.

Preprocessing steps:
  1. Pull full-history features for every intern (features.py)
  2. Missing value handling (explicit fillna)
  3. Categorical encoding (technology -> one-hot, done in features.py)
  4. Label creation: composite of attendance_rate + task_completion_rate,
     split into 3 balanced tiers via quantiles (declining/stable/improving)
  5. Leakage check: attendance_rate and task_completion_rate (the columns
     the label is built from) are dropped from X

Usage (standalone preview):
    python -m app.ml.build_performance_dataset
"""
import pandas as pd

from app.database import SessionLocal
from app.ml.features import build_features_dataframe

LEAKY_OR_ID_COLUMNS = [
    "intern_id", "status", "dropped", "completed",
    "attendance_rate", "task_completion_rate",  # used to build the label - excluded from X
    # These are mathematically derived FROM attendance_rate/task_completion_rate,
    # so leaving them in would let the model reconstruct the label almost
    # exactly (this is what caused a suspicious ~99% accuracy before this
    # fix - a hard lesson in checking every column, not just the two most
    # obvious ones, for leakage):
    "late_task_ratio", "skipped_task_ratio",        # + task_completion_rate always sum to 1
    "attendance_completion_interaction",             # literally attendance_rate * task_completion_rate
    "on_time_given_turned_in",                       # derived from the same completed/late task counts
]


def build_performance_dataset(db=None):
    own_session = db is None
    db = db or SessionLocal()
    try:
        df = build_features_dataframe(db)
    finally:
        if own_session:
            db.close()

    if df.empty:
        raise ValueError("No interns with enough history found - generate the dataset first.")

    df = df.fillna(0)

    # --- Label creation ---
    # Composite "current delivery" score: equal-weighted attendance +
    # task completion. Bucketed into 3 roughly-equal tiers using
    # quantiles, so classes stay balanced regardless of the raw
    # distribution's shape. Ranking first (rather than qcut on the raw
    # values directly) avoids errors when many interns share the same
    # composite score (duplicate bin edges).
    composite = 0.5 * df["attendance_rate"] + 0.5 * df["task_completion_rate"]
    y = pd.qcut(composite.rank(method="first"), q=3, labels=["declining", "stable", "improving"])

    X = df.drop(columns=[c for c in LEAKY_OR_ID_COLUMNS if c in df.columns])

    return X, y


if __name__ == "__main__":
    X, y = build_performance_dataset()
    print(f"Performance Trend dataset: {X.shape[0]} rows, {X.shape[1]} feature columns")
    print("Class balance:")
    print(y.value_counts())
