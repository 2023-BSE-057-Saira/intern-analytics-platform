-- ===========================================================
-- Student features migration: self-service profile, weekly
-- reports, and project submissions.
-- Run this once against your existing DB:
--   psql -U intern_admin -d intern_analytics -f sql/student_features_migration.sql
-- (or paste it into DBeaver's SQL editor and execute)
-- ===========================================================

-- --- Profile fields on interns (nullable — filled in by the
--     student after registration, via /student/profile) --------------
ALTER TABLE interns ADD COLUMN IF NOT EXISTS phone         VARCHAR(30);
ALTER TABLE interns ADD COLUMN IF NOT EXISTS education     VARCHAR(200);
ALTER TABLE interns ADD COLUMN IF NOT EXISTS skills        TEXT;        -- comma-separated, kept simple on purpose
ALTER TABLE interns ADD COLUMN IF NOT EXISTS bio           TEXT;
ALTER TABLE interns ADD COLUMN IF NOT EXISTS linkedin_url  VARCHAR(255);
ALTER TABLE interns ADD COLUMN IF NOT EXISTS github_url    VARCHAR(255);
ALTER TABLE interns ADD COLUMN IF NOT EXISTS avatar_color  VARCHAR(20); -- initials-avatar accent color, set at registration

-- --- Weekly reports: student self-reported summary of the week ------
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
CREATE INDEX IF NOT EXISTS idx_weekly_reports_intern ON weekly_reports(intern_id);

-- --- Project submissions: link-based (repo URL), visible to the
--     assigned mentor and admins ------------------------------------
CREATE TABLE IF NOT EXISTS project_submissions (
    submission_id     SERIAL PRIMARY KEY,
    intern_id          INTEGER REFERENCES interns(intern_id),
    title              VARCHAR(200) NOT NULL,
    description        TEXT,
    repo_url           VARCHAR(500) NOT NULL,
    demo_url           VARCHAR(500),
    submitted_at       TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_project_submissions_intern ON project_submissions(intern_id);
