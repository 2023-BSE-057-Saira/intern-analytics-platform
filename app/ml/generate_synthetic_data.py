"""
Synthetic Dataset Generator
============================
Generates realistic fake intern data and inserts it directly into
PostgreSQL. This exists because Ezitech doesn't provide real intern
data — you build a believable pretend dataset so your ML models
(Week 2) have something meaningful to learn from.

IMPORTANT DESIGN IDEA:
  The data isn't purely random. Interns who behave "at risk"
  (low attendance, late/incomplete tasks, low GitHub activity,
  poor code review scores) are intentionally correlated with each
  other — the same way a real struggling intern would show multiple
  warning signs together, not just one random low number.

  This is what lets your model actually learn a pattern like
  "low attendance + low task completion → high dropout risk"
  instead of learning from noise.

Usage:
    python -m app.ml.generate_synthetic_data
"""
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.db_models import (
    Mentor, Intern, Attendance, Task, GithubActivity,
    CodeReview, MentorFeedback, CommunicationActivity
)

random.seed(42)  # reproducible results

TECHNOLOGIES = ["Laravel", "MERN Stack", "Artificial Intelligence", "Flutter", "UI/UX", "DevOps"]
BATCHES = ["Batch-2026-A", "Batch-2026-B", "Batch-2026-C"]

FIRST_NAMES = ["Ali", "Sara", "Ahmed", "Ayesha", "Bilal", "Fatima", "Hamza", "Zainab",
               "Usman", "Hira", "Omar", "Mahnoor", "Talha", "Sana", "Faizan", "Amna",
               "Kashif", "Rabia", "Zeeshan", "Mariam"]
LAST_NAMES = ["Khan", "Ahmed", "Malik", "Sheikh", "Butt", "Raza", "Qureshi", "Iqbal",
              "Hussain", "Chaudhry"]

NUM_INTERNS = 800
INTERNSHIP_LENGTH_DAYS = 90  # ~3 months

# Probability an intern in each profile actually drops out.
# NOTE: not 100%/0% on purpose - real at-risk interns don't always drop out,
# and occasionally a "strong" intern leaves for unrelated reasons. This
# overlap is what makes the label learnable-but-not-trivial, which is what
# you want for a believable, defensible model (not suspiciously perfect).
DROPOUT_PROBABILITY = {
    "at_risk": 0.55,
    "average": 0.12,
    "strong": 0.03,
}

# --- Trajectory: a REAL behavioral trend over time (not just review scores) ---
# Each intern gets a trajectory - improving, stable, or declining - which
# actually drifts their attendance and task completion probability across
# the internship, not just their review scores. This is what makes
# Performance Trend and Learning Speed learn a genuine signal rather than
# statistical noise from a constant probability.
TRAJECTORY_PROBABILITIES = {
    "at_risk":  {"declining": 0.55, "stable": 0.30, "improving": 0.15},
    "average":  {"declining": 0.25, "stable": 0.40, "improving": 0.35},
    "strong":   {"declining": 0.10, "stable": 0.25, "improving": 0.65},
}

# How much attendance/completion probability drifts from start to end of
# the internship. Centered on 0 so the drawn "base rate" still represents
# roughly the intern's average over the whole period.
TRAJECTORY_DRIFT_RANGE = {
    "improving": (0.10, 0.25),
    "stable": (-0.05, 0.05),
    "declining": (-0.25, -0.10),
}

# Trajectory adjusts dropout probability on top of the profile-based base
# rate - a declining intern is more likely to actually drop out, an
# improving one less likely, even within the same starting profile.
TRAJECTORY_DROPOUT_MULTIPLIER = {
    "improving": 0.6,
    "stable": 1.0,
    "declining": 1.4,
}


def generate_trajectory(profile: str) -> str:
    probs = TRAJECTORY_PROBABILITIES[profile]
    roll = random.random()
    cumulative = 0.0
    for trajectory, p in probs.items():
        cumulative += p
        if roll < cumulative:
            return trajectory
    return "stable"  # fallback, shouldn't normally hit this


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def create_mentors(db: Session, count: int = 30):
    mentors = []
    for i in range(count):
        m = Mentor(
            name=random_name(),
            technology=random.choice(TECHNOLOGIES),
            email=f"mentor{i+1}@ezitech.com",
            max_capacity=random.randint(5, 12),
        )
        db.add(m)
        mentors.append(m)
    db.commit()
    for m in mentors:
        db.refresh(m)
    return mentors


def generate_intern_profile():
    """
    Decides, up front, whether this intern is a 'strong', 'average',
    or 'at-risk' profile. Everything else generated for this intern
    (attendance, tasks, commits, scores) is pulled toward that profile,
    which is what creates realistic, learnable correlations.
    """
    roll = random.random()
    if roll < 0.20:
        return "at_risk"
    elif roll < 0.65:
        return "average"
    else:
        return "strong"


PROFILE_RANGES = {
    "at_risk":  {"attendance": (0.45, 0.70), "task_completion": (0.30, 0.55),
                 "commits_per_day": (0.0, 1.5), "review_score": (3.0, 5.5),
                 "mentor_rating": (1.5, 3.0)},
    "average":  {"attendance": (0.75, 0.90), "task_completion": (0.60, 0.80),
                 "commits_per_day": (1.0, 3.0), "review_score": (5.5, 7.5),
                 "mentor_rating": (3.0, 4.0)},
    "strong":   {"attendance": (0.90, 1.00), "task_completion": (0.82, 1.00),
                 "commits_per_day": (2.5, 5.0), "review_score": (7.5, 9.8),
                 "mentor_rating": (4.0, 5.0)},
}


def generate_for_intern(db: Session, intern: Intern, mentor_ids: list[int]):
    profile = generate_intern_profile()
    ranges = PROFILE_RANGES[profile]

    attendance_rate = random.uniform(*ranges["attendance"])
    completion_rate = random.uniform(*ranges["task_completion"])
    commits_per_day = random.uniform(*ranges["commits_per_day"])
    review_score_base = random.uniform(*ranges["review_score"])
    mentor_rating_base = random.uniform(*ranges["mentor_rating"])

    # --- Trajectory: real behavioral drift over time ---
    trajectory = generate_trajectory(profile)
    attendance_drift = random.uniform(*TRAJECTORY_DRIFT_RANGE[trajectory])
    completion_drift = random.uniform(*TRAJECTORY_DRIFT_RANGE[trajectory])

    # --- Inject realistic noise/overlap (10% chance of a "surprise" outcome) ---
    # This prevents classes from being perfectly separable, which would make
    # your model look suspiciously perfect (e.g. 99%+ accuracy) instead of
    # realistically good (e.g. 80-90%).
    if random.random() < 0.10:
        attendance_rate = min(1.0, max(0.0, attendance_rate + random.uniform(-0.20, 0.20)))
        completion_rate = min(1.0, max(0.0, completion_rate + random.uniform(-0.20, 0.20)))
        commits_per_day = max(0.0, commits_per_day + random.uniform(-1.5, 1.5))

    # Decide the ACTUAL outcome (this becomes intern.status, your real label).
    # Trajectory adjusts the base profile probability - declining interns
    # are more likely to actually drop out than their profile alone implies.
    adjusted_dropout_prob = min(0.95, DROPOUT_PROBABILITY[profile] * TRAJECTORY_DROPOUT_MULTIPLIER[trajectory])
    will_dropout = random.random() < adjusted_dropout_prob

    start = intern.start_date
    days_elapsed = min(INTERNSHIP_LENGTH_DAYS, (date.today() - start).days)
    days_elapsed = max(days_elapsed, 1)

    # --- Attendance (with real drift over time) ---
    for d in range(days_elapsed):
        day = start + timedelta(days=d)
        if day.weekday() >= 5:  # skip weekends
            continue
        day_progress = d / max(days_elapsed - 1, 1)  # 0.0 at start, 1.0 at end
        # Drift centered on the base rate: starts at (base - drift/2),
        # ends at (base + drift/2), so attendance_rate still represents
        # roughly the intern's average over the whole period.
        daily_prob = attendance_rate + attendance_drift * (day_progress - 0.5)
        daily_prob = min(1.0, max(0.0, daily_prob))
        present = random.random() < daily_prob
        db.add(Attendance(intern_id=intern.intern_id, date=day, present=present))

    # --- Tasks (roughly 2 per week, with real drift over time) ---
    num_tasks = max(1, days_elapsed // 4)
    for t in range(num_tasks):
        assigned = start + timedelta(days=t * 4)
        due = assigned + timedelta(days=5)

        task_progress = t / max(num_tasks - 1, 1)
        task_completion_prob = completion_rate + completion_drift * (task_progress - 0.5)
        task_completion_prob = min(1.0, max(0.0, task_completion_prob))

        completed_on_time = random.random() < task_completion_prob
        difficulty = random.choice(["easy", "medium", "hard"])

        if completed_on_time:
            status = "completed"
            completed_date = due - timedelta(days=random.randint(0, 2))
        elif random.random() < 0.5:
            status = "late"
            completed_date = due + timedelta(days=random.randint(1, 5))
        else:
            status = "skipped"
            completed_date = None

        task = Task(
            intern_id=intern.intern_id,
            task_name=f"{intern.technology} Task {t + 1}",
            assigned_date=assigned,
            due_date=due,
            completed_date=completed_date,
            status=status,
            difficulty=difficulty,
        )
        db.add(task)
        db.flush()  # get task.task_id for the code review below

        if status in ("completed", "late"):
            # Review score growth mirrors the same trajectory used for
            # attendance/completion above. Capped to avoid pushing scores
            # past the 0-10 bounds, which would clip/flatten the trend
            # for the most extreme improvers/decliners instead of
            # strengthening it.
            growth_total = (attendance_drift + completion_drift) * 3.0
            growth_total = max(-2.0, min(2.0, growth_total))
            # Noise = 1.0 (original value). We tested lower noise (0.6, 0.4)
            # to try improving skill_growth, but confirmed via real testing
            # that it measurably hurts Dropout Risk, Performance Trend, and
            # especially Success Probability. Since those 3 are the core
            # predictions, we keep noise at the original level and accept
            # skill_growth's modest R² (~0.02-0.09 depending on run) as a
            # documented, well-understood limitation rather than trade away
            # performance on the more important models.
            score = max(0, min(10, random.gauss(review_score_base + growth_total * task_progress, 1.0)))
            db.add(CodeReview(
                intern_id=intern.intern_id,
                task_id=task.task_id,
                reviewer_id=random.choice(mentor_ids),
                score=round(score, 2),
                feedback="Auto-generated synthetic review feedback.",
                review_date=(completed_date or due),
            ))

    # --- GitHub activity (daily-ish) ---
    for d in range(0, days_elapsed, 2):  # every ~2 days
        day = start + timedelta(days=d)
        commits = max(0, int(random.gauss(commits_per_day * 2, 1.5)))
        db.add(GithubActivity(
            intern_id=intern.intern_id,
            date=day,
            commits=commits,
            pull_requests=max(0, int(commits / 4)),
            issues_opened=random.randint(0, 2),
            issues_closed=random.randint(0, 2),
        ))

    # --- Mentor feedback (weekly-ish) ---
    for w in range(0, days_elapsed, 7):
        day = start + timedelta(days=w)
        rating = max(0, min(5, random.gauss(mentor_rating_base, 0.5)))
        db.add(MentorFeedback(
            intern_id=intern.intern_id,
            mentor_id=intern.mentor_id,
            rating=round(rating, 2),
            feedback_text="Auto-generated synthetic mentor feedback.",
            date=day,
        ))

    # --- Communication activity (daily-ish) ---
    for d in range(0, days_elapsed, 3):
        day = start + timedelta(days=d)
        db.add(CommunicationActivity(
            intern_id=intern.intern_id,
            date=day,
            messages_sent=max(0, int(random.gauss(5 * attendance_rate, 3))),
            meetings_attended=1 if random.random() < attendance_rate else 0,
        ))

    return profile, will_dropout, trajectory


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("Creating mentors...")
    mentors = create_mentors(db)
    mentor_ids = [m.mentor_id for m in mentors]

    print(f"Creating {NUM_INTERNS} interns and their activity data...")
    profile_counts = {"at_risk": 0, "average": 0, "strong": 0}
    trajectory_counts = {"improving": 0, "stable": 0, "declining": 0}
    status_counts = {"dropped": 0, "completed": 0, "active": 0}

    for i in range(NUM_INTERNS):
        start_date = date.today() - timedelta(days=random.randint(10, INTERNSHIP_LENGTH_DAYS))
        intern = Intern(
            name=random_name(),
            email=f"intern{i+1}@ezitech.com",
            technology=random.choice(TECHNOLOGIES),
            mentor_id=random.choice(mentor_ids),
            batch=random.choice(BATCHES),
            start_date=start_date,
            expected_end_date=start_date + timedelta(days=INTERNSHIP_LENGTH_DAYS),
            status="active",  # temporary, updated below once outcome is known
        )
        db.add(intern)
        db.commit()
        db.refresh(intern)

        profile, will_dropout, trajectory = generate_for_intern(db, intern, mentor_ids)
        profile_counts[profile] += 1
        trajectory_counts[trajectory] += 1

        # Decide final status: dropped, completed, or still active.
        # NOTE: completed/active is assigned directly (not tied to elapsed
        # days) so we get a realistic, usable proportion of "completed"
        # interns to train on, rather than almost everyone sitting in
        # "active" limbo with an unknown outcome.
        if will_dropout:
            intern.status = "dropped"
        elif random.random() < 0.75:
            intern.status = "completed"
        else:
            intern.status = "active"
        status_counts[intern.status] += 1

        if (i + 1) % 100 == 0:
            db.commit()
            print(f"  ...{i + 1}/{NUM_INTERNS} interns generated")

    db.commit()
    db.close()

    print("\nDone.")
    print(f"Profile distribution (hidden ground truth): {profile_counts}")
    print(f"Trajectory distribution (hidden ground truth): {trajectory_counts}")
    print(f"Status distribution (your actual training label): {status_counts}")
    print("Synthetic dataset generated successfully.")


if __name__ == "__main__":
    main()