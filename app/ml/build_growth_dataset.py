"""
Build Learning Speed + Skill Growth Dataset
==============================================
Predicts TWO continuous targets from the same early-period features:
  - learning_speed: how much task completion rate improved (late - early)
  - skill_growth:   how much code review score improved (late - early)

Reuses the same early/late split logic as Performance Trend, but here
the LABEL is a continuous number (how much it changed), not a
yes/no category - since Learning Speed and Skill Growth are rate
questions, not classification questions.

Usage:
    from app.ml.build_growth_dataset import build_growth_dataset
    df = build_growth_dataset()
"""
import pandas as pd
from sqlalchemy import text
from app.database import engine

MIN_ATTENDANCE_RECORDS = 6
MIN_TASK_RECORDS = 2


def _early_late_split(df: pd.DataFrame, date_col: str, value_col: str,
                       intern_col: str = "intern_id") -> pd.DataFrame:
    rows = []
    for intern_id, group in df.groupby(intern_col):
        group = group.sort_values(date_col)
        n = len(group)
        if n < 2:
            continue
        mid = n // 2
        early_mean = group.iloc[:mid][value_col].mean()
        late_mean = group.iloc[mid:][value_col].mean()
        rows.append({intern_col: intern_id, "early": early_mean, "late": late_mean})
    return pd.DataFrame(rows)


def _early_trend_split(df: pd.DataFrame, date_col: str, value_col: str,
                        intern_col: str = "intern_id") -> pd.DataFrame:
    """
    Splits ONLY the early half into two quarters (first vs second), and
    returns the difference between them. This captures whether a trend
    is ALREADY visible within the early period itself - something a
    single early-period average can't see. This is what actually lets
    the model detect trajectory (improving/declining), since the base
    attendance/completion LEVEL alone barely correlates with trajectory
    in how this dataset was generated.
    """
    rows = []
    for intern_id, group in df.groupby(intern_col):
        group = group.sort_values(date_col)
        n = len(group)
        if n < 4:  # need at least 4 points to split the early half into 2
            rows.append({intern_col: intern_id, "early_trend": 0.0})
            continue
        early_half = group.iloc[:n // 2]
        q1 = early_half.iloc[:len(early_half) // 2][value_col].mean()
        q2 = early_half.iloc[len(early_half) // 2:][value_col].mean()
        rows.append({intern_col: intern_id, "early_trend": q2 - q1})
    return pd.DataFrame(rows)


def build_growth_dataset() -> pd.DataFrame:
    interns = pd.read_sql(text("SELECT * FROM interns"), engine)
    attendance = pd.read_sql(text("SELECT * FROM attendance"), engine)
    tasks = pd.read_sql(text("SELECT * FROM tasks"), engine)
    github = pd.read_sql(text("SELECT * FROM github_activity"), engine)
    reviews = pd.read_sql(text("SELECT * FROM code_reviews"), engine)
    feedback = pd.read_sql(text("SELECT * FROM mentor_feedback"), engine)

    attendance["present_numeric"] = attendance["present"].astype(int)
    tasks["completed_numeric"] = (tasks["status"] == "completed").astype(int)

    attendance_split = _early_late_split(attendance, "date", "present_numeric")
    attendance_split = attendance_split.rename(columns={"early": "attendance_early", "late": "attendance_late"})

    tasks_split = _early_late_split(tasks, "assigned_date", "completed_numeric")
    tasks_split = tasks_split.rename(columns={"early": "completion_early", "late": "completion_late"})

    github_split = _early_late_split(github, "date", "commits")
    github_split = github_split.rename(columns={"early": "commits_early", "late": "commits_late"})

    reviews_split = _early_late_split(reviews, "review_date", "score")
    reviews_split = reviews_split.rename(columns={"early": "review_early", "late": "review_late"})

    feedback_split = _early_late_split(feedback, "date", "rating")
    feedback_split = feedback_split.rename(columns={"early": "mentor_rating_early", "late": "mentor_rating_late"})

    # --- NEW: early-trend features (the actual fix for skill_growth/learning_speed) ---
    attendance_trend = _early_trend_split(attendance, "date", "present_numeric")
    attendance_trend = attendance_trend.rename(columns={"early_trend": "attendance_early_trend"})

    completion_trend = _early_trend_split(tasks, "assigned_date", "completed_numeric")
    completion_trend = completion_trend.rename(columns={"early_trend": "completion_early_trend"})

    # --- Filter: only interns with enough history for a meaningful split ---
    attendance_counts = attendance.groupby("intern_id").size()
    task_counts = tasks.groupby("intern_id").size()
    eligible_interns = set(attendance_counts[attendance_counts >= MIN_ATTENDANCE_RECORDS].index) & \
                        set(task_counts[task_counts >= MIN_TASK_RECORDS].index)

    df = interns[interns["intern_id"].isin(eligible_interns)][["intern_id", "technology"]].copy()
    df = df.merge(attendance_split, on="intern_id", how="left")
    df = df.merge(tasks_split, on="intern_id", how="left")
    df = df.merge(github_split, on="intern_id", how="left")
    df = df.merge(reviews_split, on="intern_id", how="left")
    df = df.merge(feedback_split, on="intern_id", how="left")
    df = df.merge(attendance_trend, on="intern_id", how="left")
    df = df.merge(completion_trend, on="intern_id", how="left")

    fill_cols = ["attendance_early", "attendance_late", "completion_early", "completion_late",
                 "commits_early", "commits_late", "review_early", "review_late",
                 "mentor_rating_early", "mentor_rating_late",
                 "attendance_early_trend", "completion_early_trend"]
    df[fill_cols] = df[fill_cols].fillna(0)

    # --- Build the TWO continuous labels ---
    df["learning_speed"] = df["completion_late"] - df["completion_early"]
    df["skill_growth"] = df["review_late"] - df["review_early"]

    # --- Features: early-period stats PLUS early-trend hints ---
    # The early_trend features are what actually let the model detect
    # whether an intern is on an improving/declining trajectory - a
    # single early-period average can't see this, since trajectory is
    # a separate signal from the base attendance/completion level.
    feature_df = df[[
        "intern_id", "technology",
        "attendance_early", "completion_early", "commits_early", "review_early",
        "mentor_rating_early", "attendance_early_trend", "completion_early_trend",
        "learning_speed", "skill_growth"
    ]].copy()

    feature_df = pd.get_dummies(feature_df, columns=["technology"], prefix="tech")

    return feature_df


if __name__ == "__main__":
    dataset = build_growth_dataset()
    print(f"Dataset shape: {dataset.shape}")
    print(f"\nColumns: {list(dataset.columns)}")
    print(f"\nLearning speed stats:\n{dataset['learning_speed'].describe()}")
    print(f"\nSkill growth stats:\n{dataset['skill_growth'].describe()}")
    print(f"\nFirst few rows:\n{dataset.head()}")