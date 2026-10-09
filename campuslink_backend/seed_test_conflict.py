import sqlite3
from datetime import datetime

for db_path in ['campuslink_backend/campuslink.db', 'campuslink.db']:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM job_applications WHERE student_id = 2 AND company = 'Jio Platforms'")
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO job_applications (
                student_id, job_title, company, college, job_url, source, college_approval, status, applied_at, updated_at
            ) VALUES (
                2, 'Software Engineer', 'Jio Platforms', 'Government Engineering College',
                'https://jio.com/careers', 'Placement Cell', 'Approved', 'Interview',
                '2026-10-01 10:00:00', '2026-10-01 10:00:00'
            )
        """)
        conn.commit()
    conn.close()

print('Successfully added test student simultaneous shortlist application')
