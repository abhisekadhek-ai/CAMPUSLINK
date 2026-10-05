import sqlite3

DB = "campuslink.db"

db = sqlite3.connect(DB)

try:
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute("BEGIN")

    # Rename the existing table temporarily
    db.execute("ALTER TABLE user_accounts RENAME TO user_accounts_old")

    # Create the new table with the college role allowed
    db.execute("""
        CREATE TABLE user_accounts (
            id INTEGER PRIMARY KEY,
            email VARCHAR NOT NULL UNIQUE,
            password_hash VARCHAR NOT NULL,
            role VARCHAR NOT NULL
                CHECK (role IN ('student', 'recruiter', 'college', 'admin')),
            student_id INTEGER UNIQUE,
            created_at DATETIME,
            recruiter_id INTEGER,
            college_id INTEGER
        )
    """)

    # Copy all existing accounts.
    # Existing accounts receive college_id = NULL.
    db.execute("""
        INSERT INTO user_accounts
        (id, email, password_hash, role, student_id,
         created_at, recruiter_id, college_id)
        SELECT
            id, email, password_hash, role, student_id,
            created_at, recruiter_id, NULL
        FROM user_accounts_old
    """)

    # Remove temporary old table
    db.execute("DROP TABLE user_accounts_old")

    # Preserve recruiter uniqueness
    db.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        uq_user_accounts_recruiter_id
        ON user_accounts(recruiter_id)
        WHERE recruiter_id IS NOT NULL
    """)

    # College account uniqueness
    db.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        uq_user_accounts_college_id
        ON user_accounts(college_id)
        WHERE college_id IS NOT NULL
    """)

    db.commit()

    print("College role migration completed successfully.")

    print(
        "User accounts:",
        db.execute("SELECT COUNT(*) FROM user_accounts").fetchone()[0]
    )

    print(
        "Students:",
        db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    )

except Exception as e:
    db.rollback()
    print("Migration FAILED:", e)
    print("No changes were committed.")

finally:
    db.execute("PRAGMA foreign_keys = ON")
    db.close()