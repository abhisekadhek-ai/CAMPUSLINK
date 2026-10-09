import sqlite3
import json
import random

db_paths = ["campuslink_backend/campuslink.db", "campuslink.db"]

full_master_skills = [
    ["Python", "SQL", "Java", "JavaScript", "React", "HTML", "CSS", "Machine Learning", "Deep Learning", "TensorFlow", "Git", "REST API", "Communication", "Problem Solving"],
    ["Python", "SQL", "Excel", "Power BI", "PostgreSQL", "MongoDB", "Data Science", "Machine Learning", "Communication", "Problem Solving"],
    ["Java", "Python", "Git", "Docker", "REST API", "FastAPI", "Data Structures", "Algorithms", "System Design", "Problem Solving"],
    ["Python", "Deep Learning", "NLP", "TensorFlow", "Machine Learning", "Data Structures", "Algorithms", "Git", "Linux"],
    ["JavaScript", "React", "HTML", "CSS", "MongoDB", "Node.js", "Python", "SQL", "Git", "Communication"],
    ["Python", "Java", "SQL", "Git", "Deep Learning", "Machine Learning", "Cloud Computing", "AWS", "Communication"]
]

cert_templates = [
    ["AWS Certified Cloud Practitioner", "Google Cloud Associate", "Meta Frontend Developer"],
    ["Oracle Certified Java SE", "DeepLearning.AI TensorFlow Developer", "Google Data Analytics"],
    ["Microsoft Azure Fundamentals", "AWS Certified Developer", "Docker & Kubernetes Certified"],
]

project_templates = [
    ["CampusLink Automated Placement System", "AI Job Matching Engine", "Microservices Cloud Platform"],
    ["Real-Time Collaborative Coding Hub", "Full-Stack E-Commerce Portal", "Deep Learning NLP Chatbot"],
    ["Distributed Analytics Pipeline", "High-Throughput REST API Gateway", "Cloud Infrastructure Monitor"],
]

branches = ["CSE", "IT", "ECE", "AI&DS", "EEE"]

for db_path in db_paths:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Update student 1001 (Abhisek Adhek)
    cur.execute("""
        UPDATE students 
        SET cgpa = 9.15,
            backlogs = 0,
            mock_interview_score = 92,
            branch = 'CSE',
            skills = ?,
            certifications = ?,
            projects = ?
        WHERE id = 1001
    """, (
        json.dumps(["Python", "SQL", "Java", "JavaScript", "React", "HTML", "CSS", "Machine Learning", "Deep Learning", "TensorFlow", "Git", "Docker", "REST API", "FastAPI", "Power BI", "Data Structures", "Algorithms", "Communication", "Problem Solving"]),
        json.dumps(["Google Cloud Certified Associate", "AWS Certified Developer", "Oracle Certified Java SE"]),
        json.dumps(["CampusLink AI Recruitment Platform", "High-Throughput Cloud Microservices", "Distributed Key-Value Store"])
    ))

    # Update 250 students (IDs 1 to 250) to be fully eligible and shortlisted
    for sid in range(1, 251):
        cgpa = round(random.uniform(7.85, 9.60), 2)
        score = random.randint(75, 96)
        branch = branches[sid % len(branches)]
        skills = json.dumps(full_master_skills[sid % len(full_master_skills)])
        certs = json.dumps(cert_templates[sid % len(cert_templates)])
        projs = json.dumps(project_templates[sid % len(project_templates)])

        cur.execute("""
            UPDATE students 
            SET cgpa = ?,
                backlogs = 0,
                mock_interview_score = ?,
                branch = ?,
                skills = ?,
                certifications = ?,
                projects = ?
            WHERE id = ?
        """, (cgpa, score, branch, skills, certs, projs, sid))

    conn.commit()
    conn.close()
    print(f"Boosted 250+ students in {db_path} successfully!")
