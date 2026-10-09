"""
migrate_projects_and_conflicts.py
Migrates SQLite database to add:
1. `projects` column in `students`
2. `resources`, `interview_panels`, `infrastructure_capacity` columns in `drives`
Populates realistic seed data for students and drives.
"""

import sqlite3
import json
import os

PROJECT_TEMPLATES = {
    "ai": ["AI Resume Matcher & Screener", "Deep Learning Image Classifier", "NLP Sentiment Analysis Pipeline"],
    "web": ["Full-Stack Campus Placement Portal", "Real-Time Chat & Collaboration App", "E-Commerce REST Platform"],
    "cloud": ["Cloud Native Microservices Architecture", "Automated CI/CD DevOps Pipeline", "Serverless Data Processor"],
    "data": ["Enterprise Sales Analytics Dashboard", "High-Performance Data Warehouse", "Predictive Churn Engine"],
    "systems": ["Embedded IoT Smart Sensor Network", "Distributed Key-Value Store", "Multi-Threaded HTTP Server"],
    "default": ["Smart Attendance & Campus System", "Automated Task Scheduling Platform"]
}

VENUE_CONFIG = {
    "Auditorium": {
        "resources": ["Main Stage AV System", "Projector Array", "Acoustic PA"],
        "panels": ["Technical Panel A", "Technical Panel B", "HR Panel A"],
        "capacity": 250
    },
    "Lab 1": {
        "resources": ["Lab 1 Workstations (60 Systems)", "High-Speed LAN", "Projector"],
        "panels": ["Technical Panel 1", "Technical Panel 2"],
        "capacity": 60
    },
    "Lab 2": {
        "resources": ["Lab 2 Workstations (45 Systems)", "Coding Assessment Terminal", "AV System"],
        "panels": ["Technical Panel 3", "HR Panel B"],
        "capacity": 45
    },
    "Placement Cell": {
        "resources": ["Interview Chamber A", "Video Conference System"],
        "panels": ["Panel Alpha", "Executive HR Panel"],
        "capacity": 30
    },
    "Seminar Hall A": {
        "resources": ["Presentation Screen", "Wireless Mic System"],
        "panels": ["Technical Panel 4", "Management Panel"],
        "capacity": 120
    },
    "Seminar Hall B": {
        "resources": ["Smart Board", "PA System"],
        "panels": ["Panel Beta", "HR Panel C"],
        "capacity": 80
    }
}


def pick_projects_for_student(skills_list):
    skills_text = " ".join(skills_list).lower()
    selected = []
    if any(k in skills_text for k in ["python", "machine learning", "nlp", "tensorflow", "opencv", "data science"]):
        selected.extend(PROJECT_TEMPLATES["ai"][:2])
    if any(k in skills_text for k in ["react", "javascript", "html", "node", "django", "fastapi", "rest api"]):
        selected.append(PROJECT_TEMPLATES["web"][0] if not selected else PROJECT_TEMPLATES["web"][1])
    if any(k in skills_text for k in ["aws", "cloud", "docker", "kubernetes"]):
        selected.append(PROJECT_TEMPLATES["cloud"][0])
    if any(k in skills_text for k in ["sql", "postgresql", "power bi", "database"]):
        selected.append(PROJECT_TEMPLATES["data"][0])
    if any(k in skills_text for k in ["c", "c++", "embedded"]):
        selected.append(PROJECT_TEMPLATES["systems"][0])

    if not selected:
        selected = PROJECT_TEMPLATES["default"]
    
    # Return 2 to 3 distinct projects
    return list(dict.fromkeys(selected))[:3]


def migrate_db(db_path):
    if not os.path.exists(db_path):
        print(f"Skipping {db_path} (does not exist)")
        return

    print(f"\n--- Migrating {db_path} ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Update students table
    cur.execute("PRAGMA table_info(students)")
    student_cols = [c[1] for c in cur.fetchall()]
    if "projects" not in student_cols:
        print("Adding 'projects' column to students table...")
        cur.execute("ALTER TABLE students ADD COLUMN projects TEXT NOT NULL DEFAULT '[]'")
        conn.commit()

    # Populate projects for existing students
    cur.execute("SELECT id, skills, projects FROM students")
    students = cur.fetchall()
    updated_students = 0
    for sid, skills_json, proj_json in students:
        try:
            curr_proj = json.loads(proj_json) if proj_json else []
        except Exception:
            curr_proj = []

        if not curr_proj:
            try:
                skills = json.loads(skills_json) if skills_json else []
            except Exception:
                skills = []
            new_proj = pick_projects_for_student(skills)
            cur.execute("UPDATE students SET projects = ? WHERE id = ?", (json.dumps(new_proj), sid))
            updated_students += 1

    print(f"Updated projects for {updated_students} students.")

    # 2. Update drives table
    cur.execute("PRAGMA table_info(drives)")
    drive_cols = [c[1] for c in cur.fetchall()]

    if "resources" not in drive_cols:
        print("Adding 'resources' column to drives table...")
        cur.execute("ALTER TABLE drives ADD COLUMN resources TEXT NOT NULL DEFAULT '[]'")
    if "interview_panels" not in drive_cols:
        print("Adding 'interview_panels' column to drives table...")
        cur.execute("ALTER TABLE drives ADD COLUMN interview_panels TEXT NOT NULL DEFAULT '[]'")
    if "infrastructure_capacity" not in drive_cols:
        print("Adding 'infrastructure_capacity' column to drives table...")
        cur.execute("ALTER TABLE drives ADD COLUMN infrastructure_capacity INTEGER DEFAULT 100")
    conn.commit()

    # Populate drive resource, panel, and capacity info
    cur.execute("SELECT id, venue, resources, interview_panels, infrastructure_capacity FROM drives")
    drives = cur.fetchall()
    updated_drives = 0
    for did, venue, r_json, p_json, cap in drives:
        needs_update = False
        try:
            res_list = json.loads(r_json) if r_json else []
        except Exception:
            res_list = []
        try:
            p_list = json.loads(p_json) if p_json else []
        except Exception:
            p_list = []

        cfg = VENUE_CONFIG.get(venue, {
            "resources": [f"{venue} Equipment", "Screen & Projector"],
            "panels": ["Panel 1", "Panel 2"],
            "capacity": 80
        })

        if not res_list:
            res_list = cfg["resources"]
            needs_update = True
        if not p_list:
            p_list = cfg["panels"]
            needs_update = True
        if not cap or cap == 100:
            cap = cfg["capacity"]
            needs_update = True

        if needs_update:
            cur.execute(
                "UPDATE drives SET resources = ?, interview_panels = ?, infrastructure_capacity = ? WHERE id = ?",
                (json.dumps(res_list), json.dumps(p_list), cap, did)
            )
            updated_drives += 1

    print(f"Updated conflict/resource data for {updated_drives} drives.")
    conn.commit()
    conn.close()
    print(f"Migration completed for {db_path} successfully!")


if __name__ == "__main__":
    migrate_db("campuslink_backend/campuslink.db")
    if os.path.exists("campuslink.db"):
        migrate_db("campuslink.db")
