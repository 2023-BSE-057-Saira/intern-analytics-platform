-- ===========================================================
-- Mentor review migration: adds "reviewed" tracking to weekly
-- reports and project submissions, so the Mentor Dashboard's
-- "Pending Reviews" section reflects real state instead of
-- just being unbuilt.
-- Run this once against your existing DB:
--   psql -U intern_admin -d intern_analytics -f sql/mentor_review_migration.sql
-- (or paste it into DBeaver's SQL editor and execute)
-- ===========================================================

ALTER TABLE weekly_reports ADD COLUMN IF NOT EXISTS reviewed         BOOLEAN DEFAULT FALSE;
ALTER TABLE weekly_reports ADD COLUMN IF NOT EXISTS mentor_comment   TEXT;
ALTER TABLE weekly_reports ADD COLUMN IF NOT EXISTS reviewed_at      TIMESTAMP;

ALTER TABLE project_submissions ADD COLUMN IF NOT EXISTS reviewed        BOOLEAN DEFAULT FALSE;
ALTER TABLE project_submissions ADD COLUMN IF NOT EXISTS mentor_comment  TEXT;
ALTER TABLE project_submissions ADD COLUMN IF NOT EXISTS reviewed_at     TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_weekly_reports_reviewed ON weekly_reports(reviewed);
CREATE INDEX IF NOT EXISTS idx_project_submissions_reviewed ON project_submissions(reviewed);
