"""
seed_data.py — populates campuslink.db with sample data.

Run once, after main.py has created the tables:
    python seed_data.py
"""

from database import SessionLocal, Base, engine
from models import Student, Recruiter, Drive, Offer

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Wipe existing rows so this script is safe to re-run
db.query(Offer).delete()
db.query(Drive).delete()
db.query(Recruiter).delete()
db.query(Student).delete()
db.commit()

students = [
    Student(name="Aisha Khan", branch="CSE", cgpa=8.7, backlogs=0,
            skills=["Python", "React", "SQL", "AWS"],
            certifications=["AWS Cloud Practitioner"], mock_interview_score=78),
    Student(name="Rohan Mehta", branch="CSE", cgpa=7.1, backlogs=1,
            skills=["Java", "Spring Boot", "SQL"],
            certifications=[], mock_interview_score=55),
    Student(name="Priya Nair", branch="ECE", cgpa=9.1, backlogs=0,
            skills=["Python", "Machine Learning", "Docker", "AWS"],
            certifications=["ML Specialization"], mock_interview_score=88),
    Student(name="Sameer Iyer", branch="IT", cgpa=6.8, backlogs=2,
            skills=["HTML", "CSS", "JavaScript"],
            certifications=[], mock_interview_score=45),
    Student(name="Neha Verma", branch="CSE", cgpa=8.2, backlogs=0,
            skills=["Python", "Django", "SQL", "Docker"],
            certifications=["Docker Essentials"], mock_interview_score=70),
]
db.add_all(students)
db.commit()
for s in students:
    db.refresh(s)

recruiters = [
    Recruiter(company="NimbusCloud Technologies", role="Cloud Engineer",
              required_skills=["Python", "AWS", "Docker"], min_cgpa=7.5,
              eligible_branches=["CSE", "IT", "ECE"]),
    Recruiter(company="ByteForge Systems", role="Full Stack Developer",
              required_skills=["React", "JavaScript", "SQL"], min_cgpa=7.0,
              eligible_branches=["CSE", "IT"]),
    Recruiter(company="Vertex Analytics", role="ML Engineer",
              required_skills=["Python", "Machine Learning", "AWS"], min_cgpa=8.0,
              eligible_branches=["CSE", "ECE"]),
]
db.add_all(recruiters)
db.commit()
for r in recruiters:
    db.refresh(r)

drives = [
    Drive(company="NimbusCloud Technologies", recruiter_id=recruiters[0].id,
          date="2026-09-20", time_slot="10:00-12:00", venue="Auditorium A"),
    Drive(company="ByteForge Systems", recruiter_id=recruiters[1].id,
          date="2026-09-20", time_slot="11:00-13:00", venue="Auditorium A"),  # deliberately overlaps -> conflict
    Drive(company="Vertex Analytics", recruiter_id=recruiters[2].id,
          date="2026-09-22", time_slot="10:00-12:00", venue="Seminar Hall B"),
]
db.add_all(drives)
db.commit()

offer = Offer(student_id=students[2].id, recruiter_id=recruiters[2].id,
              status="Issued", ctc_lpa=12.0)
db.add(offer)
db.commit()

db.close()
print("Seeded: 5 students, 3 recruiters, 3 drives (2 of them clash on purpose), 1 offer.")
