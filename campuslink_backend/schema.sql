-- CampusLink — SQLite schema
-- Multi-Source Placement Integration & Analytics Platform
-- Notes:
--  * Integrates multi-source data:
--    1. Student Academic & Resume Data
--    2. Recruiter Job Descriptions & Eligibility Criteria
--    3. Placement Drive Calendars & Timelines
--    4. Historical Placement Records (multi-year benchmarks)
--    5. Assessment & Mock-Interview Results
--  * JSON fields stored as JSON text and decoded with json.loads() in Python.
--  * PRAGMA foreign_keys = ON enforced for relational integrity.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- COLLEGES
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS colleges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    college_code TEXT    NOT NULL UNIQUE,
    college_name TEXT    NOT NULL,
    email        TEXT    NOT NULL UNIQUE,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- STUDENTS (Academic & Resume Data)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT    NOT NULL,
    branch               TEXT    NOT NULL,
    cgpa                 REAL    NOT NULL CHECK (cgpa >= 0 AND cgpa <= 10),
    backlogs             INTEGER NOT NULL DEFAULT 0,
    skills               TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    certifications       TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    projects             TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    mock_interview_score INTEGER          CHECK (mock_interview_score BETWEEN 0 AND 100),
    college_id           INTEGER REFERENCES colleges(id) ON DELETE SET NULL,
    college_approval     TEXT    NOT NULL DEFAULT 'Pending',
    resume_url           TEXT,
    resume_text          TEXT,                            -- Extracted full resume text
    parsed_resume_data   TEXT    NOT NULL DEFAULT '{}',   -- Extracted structured resume attributes
    created_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_students_branch ON students(branch);
CREATE INDEX IF NOT EXISTS idx_students_college ON students(college_id);

-- ---------------------------------------------------------------------
-- RECRUITERS (Job Descriptions & Eligibility Criteria)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recruiters (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    company              TEXT    NOT NULL,
    role                 TEXT    NOT NULL,                 -- Job title, e.g. "Backend Engineer"
    job_description      TEXT,                             -- Full Job Description
    responsibilities     TEXT    NOT NULL DEFAULT '[]',    -- JSON array
    required_skills      TEXT    NOT NULL DEFAULT '[]',    -- JSON array
    min_cgpa             REAL    NOT NULL DEFAULT 0,
    max_backlogs         INTEGER NOT NULL DEFAULT 0,       -- Eligibility: Max backlogs permitted
    min_mock_score       INTEGER NOT NULL DEFAULT 50,      -- Eligibility: Min mock interview score
    min_assessment_score INTEGER NOT NULL DEFAULT 50,      -- Eligibility: Min technical assessment score
    eligible_branches    TEXT    NOT NULL DEFAULT '[]',    -- JSON array
    location             TEXT    DEFAULT 'On-Campus / Hybrid',
    experience_level     TEXT    DEFAULT 'Entry Level / Fresher',
    allowed_batches      TEXT    NOT NULL DEFAULT '["2026"]', -- JSON array
    created_at           TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_recruiters_company ON recruiters(company);

-- ---------------------------------------------------------------------
-- DRIVES (Placement Drive Calendars & Timelines)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drives (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    company                 TEXT    NOT NULL,
    recruiter_id            INTEGER REFERENCES recruiters(id) ON DELETE SET NULL,
    date                    TEXT    NOT NULL,        -- ISO date, e.g. '2026-09-20'
    time_slot               TEXT    NOT NULL,        -- e.g. '10:00-12:00'
    venue                   TEXT    NOT NULL,
    status                  TEXT    NOT NULL DEFAULT 'Scheduled'
                            CHECK (status IN ('Scheduled','Rescheduled','Cancelled','Completed')),
    resources               TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    interview_panels        TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    infrastructure_capacity INTEGER DEFAULT 100,
    registration_deadline   TEXT,                            -- ISO date/time, e.g. '2026-09-17 23:59'
    round_timeline          TEXT    NOT NULL DEFAULT '[]'    -- JSON array of round schedules
);

CREATE INDEX IF NOT EXISTS idx_drives_date_venue ON drives(date, venue);

-- ---------------------------------------------------------------------
-- OFFERS (Current Batch Offer Tracking)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS offers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(id)   ON DELETE CASCADE,
    recruiter_id  INTEGER NOT NULL REFERENCES recruiters(id) ON DELETE CASCADE,
    status        TEXT    NOT NULL DEFAULT 'Issued'
                  CHECK (status IN ('Issued','Accepted','Deferred','Withdrawn','Joined')),
    ctc_lpa       REAL,                    -- numeric CTC in LPA
    joining_date  TEXT,                    -- ISO date
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (student_id, recruiter_id)
);

CREATE INDEX IF NOT EXISTS idx_offers_student   ON offers(student_id);
CREATE INDEX IF NOT EXISTS idx_offers_recruiter ON offers(recruiter_id);
CREATE INDEX IF NOT EXISTS idx_offers_status    ON offers(status);

-- ---------------------------------------------------------------------
-- HISTORICAL PLACEMENT RECORDS (Multi-Year Benchmarks)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historical_placement_records (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_year              TEXT    NOT NULL,       -- e.g. "2023-2024"
    company                 TEXT    NOT NULL,
    role                    TEXT    NOT NULL,
    branch                  TEXT    NOT NULL,
    package_ctc_lpa         REAL    NOT NULL,
    students_placed         INTEGER NOT NULL DEFAULT 1,
    hiring_domain           TEXT    NOT NULL,       -- e.g. "Software Engineering", "Cloud & DevOps"
    key_skills_demanded     TEXT    NOT NULL DEFAULT '[]',
    avg_cgpa_placed         REAL    NOT NULL DEFAULT 7.5,
    min_cgpa_placed         REAL    NOT NULL DEFAULT 6.5,
    selection_ratio_percent REAL    NOT NULL DEFAULT 15.0,
    placement_season        TEXT    NOT NULL DEFAULT 'Phase 1 - Autumn',
    created_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_hist_batch ON historical_placement_records(batch_year);
CREATE INDEX IF NOT EXISTS idx_hist_branch ON historical_placement_records(branch);
CREATE INDEX IF NOT EXISTS idx_hist_domain ON historical_placement_records(hiring_domain);
CREATE INDEX IF NOT EXISTS idx_hist_company ON historical_placement_records(company);

-- ---------------------------------------------------------------------
-- ASSESSMENT RESULTS (Coding, Aptitude & Technical Scores)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessment_results (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id       INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    assessment_title TEXT    NOT NULL,
    assessment_type  TEXT    NOT NULL DEFAULT 'Comprehensive',
    aptitude_score   REAL    NOT NULL DEFAULT 0.0,
    coding_score     REAL    NOT NULL DEFAULT 0.0,
    technical_score  REAL    NOT NULL DEFAULT 0.0,
    total_score      REAL    NOT NULL DEFAULT 0.0,
    percentile       REAL    NOT NULL DEFAULT 0.0,
    strengths        TEXT    NOT NULL DEFAULT '[]',
    weaknesses       TEXT    NOT NULL DEFAULT '[]',
    status           TEXT    NOT NULL DEFAULT 'Completed',
    completed_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_assessment_student ON assessment_results(student_id);

-- ---------------------------------------------------------------------
-- MOCK INTERVIEW RESULTS (Panel Evaluation & Behavioral Feedback)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mock_interview_results (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id              INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    interview_type          TEXT    NOT NULL DEFAULT 'Technical Mock Round',
    interviewer_name        TEXT    NOT NULL DEFAULT 'Placement Cell Panel',
    interviewer_designation TEXT    DEFAULT 'Senior Industry Mentor',
    technical_rating        REAL    NOT NULL DEFAULT 0.0,
    communication_rating    REAL    NOT NULL DEFAULT 0.0,
    problem_solving_rating  REAL    NOT NULL DEFAULT 0.0,
    overall_score           REAL    NOT NULL DEFAULT 0.0,
    verdict                 TEXT    NOT NULL DEFAULT 'Developing',
    feedback_notes          TEXT,
    recommended_actions     TEXT    NOT NULL DEFAULT '[]',
    conducted_at            TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mock_student ON mock_interview_results(student_id);

-- ---------------------------------------------------------------------
-- USER ACCOUNTS & AUTH
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_accounts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'student' CHECK (role IN ('student','recruiter','college','admin')),
    student_id    INTEGER REFERENCES students(id) ON DELETE CASCADE UNIQUE,
    recruiter_id  INTEGER REFERENCES recruiters(id) ON DELETE CASCADE UNIQUE,
    college_id    INTEGER REFERENCES colleges(id) ON DELETE CASCADE UNIQUE,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- NOTIFICATIONS (Automated Multi-Channel Communication)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_role           TEXT    NOT NULL DEFAULT 'student',
    recipient_id             INTEGER,
    recipient_name           TEXT,
    recipient_email          TEXT,
    recipient_phone          TEXT,
    category                 TEXT    NOT NULL,
    title                    TEXT    NOT NULL,
    message                  TEXT    NOT NULL,
    channels                 TEXT    NOT NULL DEFAULT '["in_app","email","whatsapp"]',
    dispatch_status          TEXT    NOT NULL DEFAULT 'Delivered',
    email_delivery_status    TEXT    NOT NULL DEFAULT 'Sent',
    whatsapp_delivery_status TEXT    NOT NULL DEFAULT 'Delivered',
    meta_data                TEXT    NOT NULL DEFAULT '{}',
    deadline_at              TEXT,
    read                     INTEGER NOT NULL DEFAULT 0,
    created_at               TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_notifications_role ON notifications(recipient_role);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_id);
CREATE INDEX IF NOT EXISTS idx_notifications_category ON notifications(category);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at);
