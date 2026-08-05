-- ===========================================================
-- Ezitech Internship Performance Prediction & Risk Analytics
-- Database Schema
-- ===========================================================

CREATE TABLE IF NOT EXISTS mentors (
    mentor_id       SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    technology      VARCHAR(50),
    email           VARCHAR(100) UNIQUE,
    max_capacity    INTEGER DEFAULT 8
);

CREATE TABLE IF NOT EXISTS interns (
    intern_id           SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL,
    email               VARCHAR(100) UNIQUE,
    technology          VARCHAR(50) NOT NULL,       -- Laravel, MERN, AI, Flutter, UI/UX, DevOps
    mentor_id           INTEGER REFERENCES mentors(mentor_id),
    batch               VARCHAR(50),
    start_date          DATE NOT NULL,
    expected_end_date   DATE,
    status              VARCHAR(20) DEFAULT 'active',  -- active, completed, dropped
    -- Self-service profile fields, filled in by the student after
    -- registration via /student/profile (see student_features_migration.sql)
    phone               VARCHAR(30),
    education           VARCHAR(200),
    skills              TEXT,          -- comma-separated, kept simple on purpose
    bio                 TEXT,
    linkedin_url        VARCHAR(255),
    github_url          VARCHAR(255),
    avatar_color        VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id   SERIAL PRIMARY KEY,
    intern_id       INTEGER REFERENCES interns(intern_id),
    date            DATE NOT NULL,
    present         BOOLEAN NOT NULL,
    UNIQUE(intern_id, date)
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id         SERIAL PRIMARY KEY,
    intern_id       INTEGER REFERENCES interns(intern_id),
    task_name       VARCHAR(200),
    assigned_date   DATE NOT NULL,
    due_date        DATE,
    completed_date  DATE,
    status          VARCHAR(20) DEFAULT 'pending',  -- pending, completed, late, skipped
    difficulty      VARCHAR(20)                      -- easy, medium, hard
);

CREATE TABLE IF NOT EXISTS github_activity (
    activity_id     SERIAL PRIMARY KEY,
    intern_id       INTEGER REFERENCES interns(intern_id),
    date            DATE NOT NULL,
    commits         INTEGER DEFAULT 0,
    pull_requests   INTEGER DEFAULT 0,
    issues_opened   INTEGER DEFAULT 0,
    issues_closed   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS code_reviews (
    review_id       SERIAL PRIMARY KEY,
    intern_id       INTEGER REFERENCES interns(intern_id),
    task_id         INTEGER REFERENCES tasks(task_id),
    reviewer_id     INTEGER REFERENCES mentors(mentor_id),
    score           NUMERIC(4,2),        -- e.g. 0-10
    feedback        TEXT,
    review_date     DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS mentor_feedback (
    feedback_id     SERIAL PRIMARY KEY,
    intern_id       INTEGER REFERENCES interns(intern_id),
    mentor_id       INTEGER REFERENCES mentors(mentor_id),
    rating          NUMERIC(3,2),        -- e.g. 0-5
    feedback_text   TEXT,
    date            DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS communication_activity (
    comm_id         SERIAL PRIMARY KEY,
    intern_id       INTEGER REFERENCES interns(intern_id),
    date            DATE NOT NULL,
    messages_sent   INTEGER DEFAULT 0,
    meetings_attended INTEGER DEFAULT 0
);

-- Stores model outputs so dashboards can just query this table
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id     SERIAL PRIMARY KEY,
    intern_id         INTEGER REFERENCES interns(intern_id),
    prediction_type   VARCHAR(50) NOT NULL,   -- dropout_risk, performance_trend, success_probability
    predicted_value   NUMERIC(6,4) NOT NULL,  -- probability or score
    confidence         NUMERIC(6,4),
    explanation_json  JSONB,                  -- SHAP explanation payload
    created_at        TIMESTAMP DEFAULT NOW()
);

-- Stores generated recommendations per intern
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    intern_id          INTEGER REFERENCES interns(intern_id),
    recommendation_type VARCHAR(50),  -- mentor_intervention, easier_task, resource, etc.
    message             TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

-- Weekly performance snapshot - built by app/ml/build_weekly_performance.py
-- AFTER data generation, reading from the tables above. Satisfies the
-- case study's "Weekly Performance" / "Daily Productivity" data points.
CREATE TABLE IF NOT EXISTS weekly_performance (
    weekly_id             SERIAL PRIMARY KEY,
    intern_id             INTEGER REFERENCES interns(intern_id),
    week_number           INTEGER NOT NULL,
    week_start_date       DATE NOT NULL,
    attendance_rate       NUMERIC(5,4),
    task_completion_rate  NUMERIC(5,4),
    avg_commits           NUMERIC(6,2),
    avg_review_score      NUMERIC(4,2),
    UNIQUE(intern_id, week_number)
);

-- Weekly reports: student self-reported summary of the week
CREATE TABLE IF NOT EXISTS weekly_reports (
    report_id        SERIAL PRIMARY KEY,
    intern_id         INTEGER REFERENCES interns(intern_id),
    week_start_date   DATE NOT NULL,
    hours_worked      NUMERIC(5,2),
    summary           TEXT NOT NULL,
    challenges        TEXT,
    created_at        TIMESTAMP DEFAULT NOW(),
    UNIQUE(intern_id, week_start_date)
);

-- Project submissions: link-based (repo URL), visible to the
-- assigned mentor and admins
CREATE TABLE IF NOT EXISTS project_submissions (
    submission_id     SERIAL PRIMARY KEY,
    intern_id          INTEGER REFERENCES interns(intern_id),
    title              VARCHAR(200) NOT NULL,
    description        TEXT,
    repo_url           VARCHAR(500) NOT NULL,
    demo_url           VARCHAR(500),
    submitted_at       TIMESTAMP DEFAULT NOW()
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_attendance_intern ON attendance(intern_id);
CREATE INDEX IF NOT EXISTS idx_tasks_intern ON tasks(intern_id);
CREATE INDEX IF NOT EXISTS idx_github_intern ON github_activity(intern_id);
CREATE INDEX IF NOT EXISTS idx_predictions_intern ON predictions(intern_id);
CREATE INDEX IF NOT EXISTS idx_weekly_performance_intern ON weekly_performance(intern_id);
CREATE INDEX IF NOT EXISTS idx_weekly_reports_intern ON weekly_reports(intern_id);
CREATE INDEX IF NOT EXISTS idx_project_submissions_intern ON project_submissions(intern_id);
