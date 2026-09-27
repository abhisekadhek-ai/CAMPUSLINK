-- CampusLink — SQLite schema
-- Notes:
--  * SQLite has no native array/list type, so `skills`, `certifications`,
--    `required_skills` and `eligible_branches` are stored as JSON text
--    (e.g. '["Python","AWS"]') and decoded with json.loads() in Python.
--  * `ctc_lpa` is numeric (not a "12 LPA" string) so branch-wise package
--    trend analytics can aggregate it directly with AVG()/MAX().
--  * created_at/updated_at give you a time axis for predictive analytics
--    (e.g. "offers issued per week") without extra tracking tables.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- STUDENTS
-- ---------------------------------------------------------------------
CREATE TABLE students (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    name                   TEXT    NOT NULL,
    branch                 TEXT    NOT NULL,
    cgpa                   REAL    NOT NULL CHECK (cgpa >= 0 AND cgpa <= 10),
    backlogs               INTEGER NOT NULL DEFAULT 0,
    skills                 TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    certifications         TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    mock_interview_score   INTEGER          CHECK (mock_interview_score BETWEEN 0 AND 100),
    created_at             TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at             TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_students_branch ON students(branch);

-- ---------------------------------------------------------------------
-- RECRUITERS  (one row = one open role/job posting from one company)
-- ---------------------------------------------------------------------
CREATE TABLE recruiters (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company             TEXT    NOT NULL,
    role                TEXT    NOT NULL,                 -- job title, e.g. "Backend Engineer"
    required_skills     TEXT    NOT NULL DEFAULT '[]',    -- JSON array
    min_cgpa            REAL    NOT NULL DEFAULT 0,
    eligible_branches   TEXT    NOT NULL DEFAULT '[]',    -- JSON array
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_recruiters_company ON recruiters(company);

-- ---------------------------------------------------------------------
-- DRIVES  (a scheduled placement drive/interview slot)
-- ---------------------------------------------------------------------
CREATE TABLE drives (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company      TEXT    NOT NULL,
    recruiter_id INTEGER REFERENCES recruiters(id) ON DELETE SET NULL,  -- optional link to the specific role
    date         TEXT    NOT NULL,        -- ISO date, e.g. '2026-09-20'
    time_slot    TEXT    NOT NULL,        -- e.g. '10:00-12:00'
    venue        TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'Scheduled'
                 CHECK (status IN ('Scheduled','Rescheduled','Cancelled','Completed'))
);

-- Speeds up the conflict-detection query (same date + venue, overlapping slot)
CREATE INDEX idx_drives_date_venue ON drives(date, venue);

-- ---------------------------------------------------------------------
-- OFFERS
-- ---------------------------------------------------------------------
CREATE TABLE offers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(id)   ON DELETE CASCADE,
    recruiter_id  INTEGER NOT NULL REFERENCES recruiters(id) ON DELETE CASCADE,
    status        TEXT    NOT NULL DEFAULT 'Issued'
                  CHECK (status IN ('Issued','Accepted','Deferred','Withdrawn','Joined')),
    ctc_lpa       REAL,                    -- numeric CTC in LPA, for AVG()/MAX() analytics
    joining_date  TEXT,                    -- ISO date, nullable until confirmed
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),

    -- one student can't hold two separate offers for the same role
    UNIQUE (student_id, recruiter_id)
);

CREATE INDEX idx_offers_student   ON offers(student_id);
CREATE INDEX idx_offers_recruiter ON offers(recruiter_id);
CREATE INDEX idx_offers_status    ON offers(status);
