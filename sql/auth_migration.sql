-- ===========================================================
-- Auth migration: adds a dedicated users table for login.
-- Run this once against your existing DB:
--   psql -U intern_admin -d intern_analytics -f auth_migration.sql
-- (or paste it into DBeaver's SQL editor and execute)
-- ===========================================================

CREATE TABLE IF NOT EXISTS users (
    user_id         SERIAL PRIMARY KEY,
    email           VARCHAR(100) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL,        -- 'admin', 'mentor', 'student'
    mentor_id       INTEGER REFERENCES mentors(mentor_id),   -- set only if role='mentor'
    intern_id       INTEGER REFERENCES interns(intern_id),   -- set only if role='student'
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
