"""
migrate_multisource_engine.py — Database migration and data enrichment for
the Multi-Source Data Integration & Analysis Engine.

Integrates and populates:
1. Student Academic & Resume Data (resume_text, parsed_resume_data)
2. Recruiter Job Descriptions & Eligibility Criteria (job_description, responsibilities, max_backlogs, min_mock_score, min_assessment_score, location, experience_level, allowed_batches)
3. Placement Drive Calendars (registration_deadline, round_timeline)
4. Historical Placement Records (historical_placement_records table & dataset)
5. Assessment & Mock-Interview Results (assessment_results and mock_interview_results tables & dataset)
"""

import json
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "campuslink_backend/campuslink.db"

def run_migration():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- Step 1: Upgrading existing tables with new multi-source columns ---")

    # 1. Update students table
    cursor.execute("PRAGMA table_info(students);")
    student_cols = [c[1] for c in cursor.fetchall()]

    if "resume_text" not in student_cols:
        cursor.execute("ALTER TABLE students ADD COLUMN resume_text TEXT;")
        print("  Added 'resume_text' to students.")
    if "parsed_resume_data" not in student_cols:
        cursor.execute("ALTER TABLE students ADD COLUMN parsed_resume_data TEXT DEFAULT '{}';")
        print("  Added 'parsed_resume_data' to students.")

    # 2. Update recruiters table
    cursor.execute("PRAGMA table_info(recruiters);")
    recruiter_cols = [c[1] for c in cursor.fetchall()]

    if "job_description" not in recruiter_cols:
        cursor.execute("ALTER TABLE recruiters ADD COLUMN job_description TEXT;")
        print("  Added 'job_description' to recruiters.")
    if "responsibilities" not in recruiter_cols:
        cursor.execute("ALTER TABLE recruiters ADD COLUMN responsibilities TEXT DEFAULT '[]';")
        print("  Added 'responsibilities' to recruiters.")
    if "max_backlogs" not in recruiter_cols:
        cursor.execute("ALTER TABLE recruiters ADD COLUMN max_backlogs INTEGER DEFAULT 0;")
        print("  Added 'max_backlogs' to recruiters.")
    if "min_mock_score" not in recruiter_cols:
        cursor.execute("ALTER TABLE recruiters ADD COLUMN min_mock_score INTEGER DEFAULT 50;")
        print("  Added 'min_mock_score' to recruiters.")
    if "min_assessment_score" not in recruiter_cols:
        cursor.execute("ALTER TABLE recruiters ADD COLUMN min_assessment_score INTEGER DEFAULT 50;")
        print("  Added 'min_assessment_score' to recruiters.")
    if "location" not in recruiter_cols:
        cursor.execute("ALTER TABLE recruiters ADD COLUMN location TEXT DEFAULT 'On-Campus / Hybrid';")
        print("  Added 'location' to recruiters.")
    if "experience_level" not in recruiter_cols:
        cursor.execute("ALTER TABLE recruiters ADD COLUMN experience_level TEXT DEFAULT 'Entry Level / Fresher';")
        print("  Added 'experience_level' to recruiters.")
    if "allowed_batches" not in recruiter_cols:
        cursor.execute("ALTER TABLE recruiters ADD COLUMN allowed_batches TEXT DEFAULT '[\"2026\"]';")
        print("  Added 'allowed_batches' to recruiters.")

    # 3. Update drives table
    cursor.execute("PRAGMA table_info(drives);")
    drive_cols = [c[1] for c in cursor.fetchall()]

    if "registration_deadline" not in drive_cols:
        cursor.execute("ALTER TABLE drives ADD COLUMN registration_deadline TEXT;")
        print("  Added 'registration_deadline' to drives.")
    if "round_timeline" not in drive_cols:
        cursor.execute("ALTER TABLE drives ADD COLUMN round_timeline TEXT DEFAULT '[]';")
        print("  Added 'round_timeline' to drives.")

    conn.commit()

    print("\n--- Step 2: Creating new tables for Multi-Source Integration ---")

    # Table 4: historical_placement_records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historical_placement_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_year TEXT NOT NULL,
        company TEXT NOT NULL,
        role TEXT NOT NULL,
        branch TEXT NOT NULL,
        package_ctc_lpa REAL NOT NULL,
        students_placed INTEGER NOT NULL DEFAULT 1,
        hiring_domain TEXT NOT NULL,
        key_skills_demanded TEXT NOT NULL DEFAULT '[]',
        avg_cgpa_placed REAL NOT NULL DEFAULT 7.5,
        min_cgpa_placed REAL NOT NULL DEFAULT 6.5,
        selection_ratio_percent REAL NOT NULL DEFAULT 15.0,
        placement_season TEXT NOT NULL DEFAULT 'Phase 1 - Autumn',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_batch ON historical_placement_records(batch_year);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_branch ON historical_placement_records(branch);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_domain ON historical_placement_records(hiring_domain);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_company ON historical_placement_records(company);")
    print("  Created 'historical_placement_records' table.")

    # Table 5: assessment_results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessment_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        assessment_title TEXT NOT NULL,
        assessment_type TEXT NOT NULL DEFAULT 'Comprehensive',
        aptitude_score REAL NOT NULL DEFAULT 0.0,
        coding_score REAL NOT NULL DEFAULT 0.0,
        technical_score REAL NOT NULL DEFAULT 0.0,
        total_score REAL NOT NULL DEFAULT 0.0,
        percentile REAL NOT NULL DEFAULT 0.0,
        strengths TEXT NOT NULL DEFAULT '[]',
        weaknesses TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'Completed',
        completed_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_assessment_student ON assessment_results(student_id);")
    print("  Created 'assessment_results' table.")

    # Table 6: mock_interview_results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mock_interview_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        interview_type TEXT NOT NULL DEFAULT 'Technical Mock Round',
        interviewer_name TEXT NOT NULL DEFAULT 'Placement Cell Panel',
        interviewer_designation TEXT DEFAULT 'Senior Industry Mentor',
        technical_rating REAL NOT NULL DEFAULT 0.0,
        communication_rating REAL NOT NULL DEFAULT 0.0,
        problem_solving_rating REAL NOT NULL DEFAULT 0.0,
        overall_score REAL NOT NULL DEFAULT 0.0,
        verdict TEXT NOT NULL DEFAULT 'Developing',
        feedback_notes TEXT,
        recommended_actions TEXT NOT NULL DEFAULT '[]',
        conducted_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mock_student ON mock_interview_results(student_id);")
    print("  Created 'mock_interview_results' table.")

    conn.commit()

    print("\n--- Step 3: Enriching Recruiter Job Descriptions & Eligibility Criteria ---")
    cursor.execute("SELECT id, company, role, required_skills, min_cgpa, eligible_branches, job_description FROM recruiters;")
    recruiters = cursor.fetchall()
    updated_recruiters = 0

    jd_templates = {
        "Software": "We are seeking a talented {role} to join {company}. In this role, you will design, build, and maintain highly scalable applications, write clean and testable code, collaborate with cross-functional product and engineering teams, and implement best engineering practices across modern cloud and distributed architectures.",
        "Data": "{company} is looking for an analytical {role} to extract actionable intelligence from large-scale data systems. You will develop predictive models, design robust data pipelines, collaborate with stakeholders on data-driven decision making, and evaluate algorithm accuracy using state-of-the-art analytical toolsets.",
        "Cloud": "Join {company} as a {role} to architect and manage secure, resilient cloud infrastructure. Key responsibilities include automating CI/CD pipelines, container orchestration, optimizing cloud resource usage, monitoring system reliability, and enforcing modern infrastructure-as-code principles.",
        "Core": "{company} is hiring a dynamic {role} for our engineering operations. The candidate will engage in end-to-end technical problem solving, system optimization, cross-discipline technical reviews, and engineering design compliance."
    }

    resp_templates = [
        "Design, develop, test, deploy, maintain and improve software solutions.",
        "Manage individual project priorities, deadlines and deliverables.",
        "Participate in design discussions and peer code reviews.",
        "Troubleshoot performance bottlenecks and optimize operational scalability.",
        "Collaborate with product managers and UX teams to define new features."
    ]

    for r_id, comp, role, req_skills_raw, min_cgpa, elig_branches_raw, existing_jd in recruiters:
        if not existing_jd:
            try:
                skills_list = json.loads(req_skills_raw) if req_skills_raw else []
            except:
                skills_list = []
            
            category = "Software"
            r_lower = role.lower()
            if any(k in r_lower for k in ["data", "ml", "ai", "analyst"]):
                category = "Data"
            elif any(k in r_lower for k in ["cloud", "devops", "sre", "infra", "network"]):
                category = "Cloud"
            elif any(k in r_lower for k in ["mechanical", "electrical", "embedded", "vlsi"]):
                category = "Core"

            jd_desc = jd_templates[category].format(role=role, company=comp)
            jd_desc += f" Required core technical proficiencies: {', '.join(skills_list)}."
            jd_desc += f" Must demonstrate strong analytical acumen, collaborative teamwork, and proactive communication."

            max_b = 0 if min_cgpa >= 7.5 else 1
            min_mock = 65 if min_cgpa >= 8.0 else 55
            min_assess = 65 if min_cgpa >= 8.0 else 55

            cursor.execute("""
            UPDATE recruiters
            SET job_description = ?,
                responsibilities = ?,
                max_backlogs = ?,
                min_mock_score = ?,
                min_assessment_score = ?,
                location = ?,
                experience_level = ?,
                allowed_batches = ?
            WHERE id = ?;
            """, (
                jd_desc,
                json.dumps(resp_templates),
                max_b,
                min_mock,
                min_assess,
                "Bangalore / Hyderabad / Hybrid",
                "Entry Level (Fresher)",
                json.dumps(["2026", "2027"]),
                r_id
            ))
            updated_recruiters += 1

    conn.commit()
    print(f"  Enriched {updated_recruiters} recruiters with comprehensive JDs and full eligibility criteria.")

    print("\n--- Step 4: Enriching Drives with Calendar Timelines & Deadlines ---")
    cursor.execute("SELECT id, date, time_slot, company, registration_deadline FROM drives;")
    drives = cursor.fetchall()
    updated_drives = 0

    for d_id, d_date, d_slot, comp, existing_deadline in drives:
        if not existing_deadline and d_date:
            try:
                drive_dt = datetime.strptime(d_date[:10], "%Y-%m-%d")
                deadline_dt = drive_dt - timedelta(days=3)
                deadline_str = deadline_dt.strftime("%Y-%m-%d 23:59")
            except:
                deadline_str = "2026-09-18 23:59"

            timeline = [
                {"round": "Pre-Placement Talk (PPT)", "duration": "45 mins", "mode": "Auditorium Presentation"},
                {"round": "Online Assessment (Coding & Aptitude)", "duration": "90 mins", "mode": "Computer Lab"},
                {"round": "Technical Interview Round 1", "duration": "45 mins", "mode": "Panel Interview"},
                {"round": "HR & Culture Fit Round", "duration": "30 mins", "mode": "Placement Cell Chamber"}
            ]

            cursor.execute("""
            UPDATE drives
            SET registration_deadline = ?,
                round_timeline = ?
            WHERE id = ?;
            """, (deadline_str, json.dumps(timeline), d_id))
            updated_drives += 1

    conn.commit()
    print(f"  Enriched {updated_drives} placement drives with calendar timelines and registration deadlines.")

    print("\n--- Step 5: Enriching Students with Resume Data, Assessments & Mock Interviews ---")
    cursor.execute("SELECT id, name, branch, cgpa, backlogs, skills, certifications, projects, mock_interview_score, resume_text FROM students;")
    students = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM assessment_results;")
    has_assessments = cursor.fetchone()[0] > 0

    cursor.execute("SELECT COUNT(*) FROM mock_interview_results;")
    has_mock_results = cursor.fetchone()[0] > 0

    assessment_batch = []
    mock_batch = []
    student_updates = []

    domains = ["Software Engineering", "Full Stack Development", "Cloud Architecture", "Data Science & Analytics", "Core Engineering"]

    for s_id, s_name, s_branch, s_cgpa, s_backlogs, s_skills_raw, s_certs_raw, s_projects_raw, s_mock_score, existing_r_text in students:
        try:
            skills = json.loads(s_skills_raw) if s_skills_raw else []
        except:
            skills = []
        try:
            certs = json.loads(s_certs_raw) if s_certs_raw else []
        except:
            certs = []
        try:
            projs = json.loads(s_projects_raw) if s_projects_raw else []
        except:
            projs = []

        mock_score = s_mock_score if s_mock_score is not None else 65

        # 1. Generate parsed resume data and resume text if not present
        if not existing_r_text:
            summary = f"Motivated {s_branch} engineering undergraduate with strong foundations in {', '.join(skills[:3]) if skills else 'Computer Science'}. Eager to leverage technical skills in a challenging role."
            parsed_data = {
                "full_name": s_name,
                "branch": s_branch,
                "cgpa": s_cgpa,
                "summary": summary,
                "technical_skills": skills,
                "certifications": certs,
                "projects": projs,
                "education": [
                    {
                        "degree": f"Bachelor of Technology in {s_branch}",
                        "institution": "CampusLink Partner Engineering College",
                        "cgpa": s_cgpa,
                        "batch": "2022 - 2026"
                    }
                ],
                "ats_compatibility_score": round(min(98.0, 60.0 + (s_cgpa * 2.5) + (len(skills) * 2.0) + (len(projs) * 3.0)), 1)
            }

            resume_text = f"""
==================================================
RESUME: {s_name.upper()}
Degree: B.Tech {s_branch} | CGPA: {s_cgpa} | Backlogs: {s_backlogs}
Email: {s_name.lower().replace(' ', '.')}@campuslink.edu.in
==================================================
PROFESSIONAL SUMMARY:
{summary}

TECHNICAL SKILLS:
{', '.join(skills) if skills else 'Python, C++, Java, Data Structures'}

ACADEMIC PROJECTS:
{chr(10).join(['* ' + p for p in projs]) if projs else '* University Management System with automated workflows\n* Scalable web application with relational database backend'}

CERTIFICATIONS & CREDENTIALS:
{chr(10).join(['* ' + c for c in certs]) if certs else '* Foundation in Software Architecture & Algorithms'}

EDUCATION:
Bachelor of Technology ({s_branch}), 2022-2026
Cumulative Grade Point Average: {s_cgpa}/10.0
==================================================
""".strip()

            student_updates.append((resume_text, json.dumps(parsed_data), s_id))

        # 2. Generate Assessment Results if table is empty
        if not has_assessments:
            # Baseline aligned with CGPA and mock score with natural variance
            base_skill = (s_cgpa / 10.0) * 50.0 + (mock_score / 100.0) * 45.0
            apt_score = round(max(35.0, min(99.0, base_skill + random.uniform(-6, 7))), 1)
            code_score = round(max(30.0, min(99.0, base_skill + random.uniform(-8, 6))), 1)
            tech_score = round(max(35.0, min(99.0, base_skill + random.uniform(-5, 5))), 1)
            total_score = round((apt_score * 0.3) + (code_score * 0.4) + (tech_score * 0.3), 1)
            percentile = round(min(99.5, max(15.0, total_score * 1.05 - 5.0)), 1)

            strengths = [s for s in skills[:3]] if skills else ["Object Oriented Programming", "Problem Analysis"]
            weaknesses = ["Complex Dynamic Programming", "Distributed Caching"] if total_score >= 70 else ["Time Complexity Optimization", "Algorithm Edge Cases"]
            status = "Exemplary" if total_score >= 85 else ("Passed" if total_score >= 60 else "Needs Improvement")

            assessment_batch.append((
                s_id,
                "National Placement Diagnostic Assessment 2026",
                "Comprehensive",
                apt_score,
                code_score,
                tech_score,
                total_score,
                percentile,
                json.dumps(strengths),
                json.dumps(weaknesses),
                status,
                (datetime.utcnow() - timedelta(days=random.randint(10, 45))).strftime("%Y-%m-%d %H:%M:%S")
            ))

        # 3. Generate Mock Interview Results if table is empty
        if not has_mock_results:
            tech_rating = round(max(30.0, min(98.0, mock_score + random.uniform(-5, 5))), 1)
            comm_rating = round(max(35.0, min(98.0, (s_cgpa * 9.5) + random.uniform(-5, 5))), 1)
            prob_rating = round(max(30.0, min(98.0, (tech_rating * 0.6) + (comm_rating * 0.4))), 1)
            overall_mock = round((tech_rating * 0.45) + (comm_rating * 0.30) + (prob_rating * 0.25), 1)

            if overall_mock >= 85:
                verdict = "Exceptional"
            elif overall_mock >= 68:
                verdict = "Ready"
            elif overall_mock >= 48:
                verdict = "Developing"
            else:
                verdict = "Needs Preparation"

            feedback = f"Candidate demonstrated structured communication and solid foundational grasp of {skills[0] if skills else 'CS concepts'}. Approach to coding and problem-solving is methodic."
            actions = [
                f"Continue practicing LeetCode/HackerRank coding patterns in {skills[0] if skills else 'core language'}.",
                "Refine STAR method for behavioral and leadership interview scenarios.",
                "Review system architectural design patterns and database indexing."
            ]

            mock_batch.append((
                s_id,
                "Technical & Problem Solving Mock Interview",
                random.choice(["Dr. Anand Swaminathan", "Pooja Deshmukh", "Rajeev Menon", "Kavita Rao"]),
                random.choice(["Principal Engineering Lead", "Senior Technical Architect", "VP of Engineering"]),
                tech_rating,
                comm_rating,
                prob_rating,
                overall_mock,
                verdict,
                feedback,
                json.dumps(actions),
                (datetime.utcnow() - timedelta(days=random.randint(5, 30))).strftime("%Y-%m-%d %H:%M:%S")
            ))

    if student_updates:
        cursor.executemany("UPDATE students SET resume_text = ?, parsed_resume_data = ? WHERE id = ?;", student_updates)
        conn.commit()
        print(f"  Enriched {len(student_updates)} students with parsed resume data and text.")

    if assessment_batch:
        cursor.executemany("""
        INSERT INTO assessment_results (
            student_id, assessment_title, assessment_type, aptitude_score,
            coding_score, technical_score, total_score, percentile,
            strengths, weaknesses, status, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, assessment_batch)
        conn.commit()
        print(f"  Inserted {len(assessment_batch)} student assessment evaluation records.")

    if mock_batch:
        cursor.executemany("""
        INSERT INTO mock_interview_results (
            student_id, interview_type, interviewer_name, interviewer_designation,
            technical_rating, communication_rating, problem_solving_rating,
            overall_score, verdict, feedback_notes, recommended_actions, conducted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, mock_batch)
        conn.commit()
        print(f"  Inserted {len(mock_batch)} student mock interview evaluation records.")

    print("\n--- Step 6: Populating Historical Placement Records (Multi-Year Dataset) ---")
    cursor.execute("SELECT COUNT(*) FROM historical_placement_records;")
    hist_count = cursor.fetchone()[0]

    if hist_count == 0:
        historical_records = [
            # 2024-2025
            ("2024-2025", "Google", "Software Engineer", "CSE", 32.5, 8, "Software Engineering", ["C++", "Python", "Algorithms", "Distributed Systems"], 8.9, 8.2, 4.5, "Phase 1 - Autumn"),
            ("2024-2025", "Microsoft", "Cloud Solution Architect", "CSE", 28.0, 12, "Cloud & DevOps", ["Azure", "C#", "Kubernetes", "Python"], 8.6, 7.8, 6.2, "Phase 1 - Autumn"),
            ("2024-2025", "Amazon", "SDE-1", "IT", 24.5, 18, "Software Engineering", ["Java", "AWS", "Data Structures", "SQL"], 8.3, 7.5, 8.1, "Phase 1 - Autumn"),
            ("2024-2025", "Oracle", "Database Cloud Engineer", "IT", 18.0, 15, "Cloud & DevOps", ["SQL", "Java", "Linux", "Docker"], 8.0, 7.2, 12.0, "Phase 1 - Autumn"),
            ("2024-2025", "Cisco Systems", "Network Software Engineer", "ECE", 16.5, 14, "Core Engineering", ["Python", "C", "Networking", "Embedded C"], 8.1, 7.0, 10.5, "Phase 1 - Autumn"),
            ("2024-2025", "Qualcomm", "Embedded Systems Engineer", "ECE", 22.0, 7, "Core Engineering", ["C", "C++", "VLSI", "Linux"], 8.5, 7.9, 5.0, "Phase 1 - Autumn"),
            ("2024-2025", "Deloitte", "Technology Consultant", "CSE", 10.5, 34, "Full Stack & Consulting", ["SQL", "Python", "Tableau", "Agile"], 7.6, 6.8, 22.0, "Phase 1 - Autumn"),
            ("2024-2025", "Cognizant", "GenC Next Developer", "IT", 6.8, 45, "Software Engineering", ["Java", "SQL", "HTML", "CSS"], 7.2, 6.5, 30.0, "Phase 2 - Spring"),
            ("2024-2025", "Tata Consultancy Services", "Digital Engineer", "ECE", 7.2, 50, "Software Engineering", ["Python", "Java", "SQL"], 7.3, 6.5, 35.0, "Phase 2 - Spring"),
            ("2024-2025", "Infosys", "Specialist Programmer", "CSE", 9.5, 28, "Software Engineering", ["Python", "React", "Data Structures"], 7.8, 7.0, 18.5, "Phase 2 - Spring"),
            ("2024-2025", "L&T Technology Services", "Mechanical Design Engineer", "ME", 6.5, 20, "Core Engineering", ["AutoCAD", "SolidWorks", "ANSYS", "Python"], 7.4, 6.5, 25.0, "Phase 2 - Spring"),
            ("2024-2025", "Schneider Electric", "Power Systems Engineer", "EE", 8.2, 16, "Core Engineering", ["MATLAB", "PLC", "Power Systems", "C"], 7.6, 6.7, 20.0, "Phase 1 - Autumn"),

            # 2023-2024
            ("2023-2024", "Google", "Software Engineer", "CSE", 30.0, 6, "Software Engineering", ["C++", "Python", "Data Structures", "System Design"], 9.0, 8.4, 3.8, "Phase 1 - Autumn"),
            ("2023-2024", "Amazon", "SDE-1", "CSE", 23.0, 15, "Software Engineering", ["Java", "AWS", "Algorithms", "Object Oriented Design"], 8.4, 7.7, 7.5, "Phase 1 - Autumn"),
            ("2023-2024", "Microsoft", "Software Engineer", "IT", 26.5, 10, "Software Engineering", ["C#", "Azure", "TypeScript", "SQL"], 8.5, 7.8, 6.0, "Phase 1 - Autumn"),
            ("2023-2024", "Salesforce", "Member of Technical Staff", "IT", 21.0, 8, "Cloud & DevOps", ["Java", "React", "Cloud Architecture", "Docker"], 8.4, 7.6, 7.0, "Phase 1 - Autumn"),
            ("2023-2024", "Texas Instruments", "Analog & Digital Design", "ECE", 19.5, 8, "Core Engineering", ["Verilog", "C", "Analog Circuits", "MATLAB"], 8.6, 8.0, 6.5, "Phase 1 - Autumn"),
            ("2023-2024", "Intel", "Firmware Engineer", "ECE", 18.0, 11, "Core Engineering", ["C++", "C", "Embedded Systems", "Linux Kernel"], 8.3, 7.5, 9.0, "Phase 1 - Autumn"),
            ("2023-2024", "Accenture", "Advanced App Engineering Analyst", "CSE", 6.5, 55, "Software Engineering", ["Java", "Spring Boot", "SQL"], 7.1, 6.5, 32.0, "Phase 2 - Spring"),
            ("2023-2024", "Wipro", "Turbo Developer", "IT", 6.5, 40, "Software Engineering", ["Python", "SQL", "JavaScript"], 7.0, 6.5, 30.0, "Phase 2 - Spring"),
            ("2023-2024", "PwC", "Cybersecurity Analyst", "CSE", 8.5, 18, "Cybersecurity", ["Networking", "Linux", "Python", "Cryptography"], 7.7, 6.9, 16.0, "Phase 1 - Autumn"),
            ("2023-2024", "Bosch", "Embedded Automotive Engineer", "ME", 7.8, 14, "Core Engineering", ["Embedded C", "CAN", "MATLAB", "Microcontrollers"], 7.7, 7.0, 18.0, "Phase 1 - Autumn"),
            ("2023-2024", "Siemens", "Industrial Automation Engineer", "EE", 7.5, 15, "Core Engineering", ["SCADA", "PLC", "Python", "Industrial IoT"], 7.5, 6.8, 22.0, "Phase 2 - Spring"),

            # 2022-2023
            ("2022-2023", "Adobe", "Product Engineer", "CSE", 25.0, 7, "Software Engineering", ["C++", "Algorithms", "Machine Learning", "Python"], 8.8, 8.1, 5.0, "Phase 1 - Autumn"),
            ("2022-2023", "Goldman Sachs", "Systems Analyst", "CSE", 24.0, 9, "Software Engineering", ["Java", "Data Structures", "SQL", "Spring"], 8.7, 8.0, 5.5, "Phase 1 - Autumn"),
            ("2022-2023", "Walmart Global Tech", "Software Engineer", "IT", 20.0, 14, "Software Engineering", ["Java", "Kafka", "Cloud", "Microservices"], 8.2, 7.5, 8.0, "Phase 1 - Autumn"),
            ("2022-2023", "Capgemini", "Senior Analyst", "IT", 5.8, 60, "Software Engineering", ["Java", "SQL", "Web Technologies"], 6.9, 6.2, 38.0, "Phase 2 - Spring"),
            ("2022-2023", "TCS", "Ninja Developer", "ECE", 4.5, 85, "Software Engineering", ["C", "Java", "SQL"], 6.8, 6.0, 42.0, "Phase 2 - Spring"),
            ("2022-2023", "Tata Motors", "Automotive Graduate Engineer", "ME", 6.2, 22, "Core Engineering", ["Mechanical Dynamics", "CAD", "Thermal Engineering"], 7.3, 6.5, 26.0, "Phase 1 - Autumn"),
            ("2022-2023", "ABB", "Electrical Project Engineer", "EE", 6.8, 18, "Core Engineering", ["Transformers", "Switchgears", "AutoCAD", "MATLAB"], 7.4, 6.6, 24.0, "Phase 2 - Spring"),

            # 2021-2022
            ("2021-2022", "Amazon", "Software Development Engineer", "CSE", 21.5, 12, "Software Engineering", ["Java", "Data Structures", "Linux"], 8.4, 7.8, 8.0, "Phase 1 - Autumn"),
            ("2021-2022", "IBM", "Cloud Associate", "IT", 9.0, 22, "Cloud & DevOps", ["Python", "Docker", "Red Hat Linux", "SQL"], 7.6, 6.8, 20.0, "Phase 1 - Autumn"),
            ("2021-2022", "Infosys", "Systems Engineer", "CSE", 4.8, 90, "Software Engineering", ["Python", "Java", "Database Concepts"], 6.8, 6.0, 45.0, "Phase 2 - Spring"),
            ("2021-2022", "Samsung R&D", "Software Research Engineer", "ECE", 14.5, 10, "Core Engineering", ["C++", "Image Processing", "Android", "Linux"], 8.2, 7.4, 12.0, "Phase 1 - Autumn"),
            ("2021-2022", "Maruti Suzuki", "Production Engineer Trainee", "ME", 5.8, 24, "Core Engineering", ["Manufacturing Systems", "CAD", "Quality Control"], 7.2, 6.5, 28.0, "Phase 2 - Spring"),
        ]

        cursor.executemany("""
        INSERT INTO historical_placement_records (
            batch_year, company, role, branch, package_ctc_lpa, students_placed,
            hiring_domain, key_skills_demanded, avg_cgpa_placed, min_cgpa_placed,
            selection_ratio_percent, placement_season
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, [
            (
                r[0], r[1], r[2], r[3], r[4], r[5], r[6],
                json.dumps(r[7]), r[8], r[9], r[10], r[11]
            ) for r in historical_records
        ])
        conn.commit()
        print(f"  Inserted {len(historical_records)} multi-year historical placement benchmark records.")
    else:
        print(f"  historical_placement_records already has {hist_count} records.")

    conn.close()
    print("\n[SUCCESS] Migration and multi-source data integration setup finished successfully!")

if __name__ == "__main__":
    run_migration()
