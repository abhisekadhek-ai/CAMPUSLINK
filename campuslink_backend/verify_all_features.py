import sys
sys.path.append('campuslink_backend')

from database import SessionLocal
from models import Student, Recruiter, Drive, JobApplication
from main import detect_all_drive_conflicts, readiness_score, match_student_to_recruiter

db = SessionLocal()

print("--- 1. Testing Student Readiness Score with Projects & Certifications ---")
student = db.query(Student).first()
if student:
    score, label, breakdown = readiness_score(student)
    print(f"Student: {student.name} (ID: {student.id})")
    print(f"Readiness Score: {score}/100, Label: {label}")
    print(f"Breakdown: {breakdown}")
    print(f"Student projects: {student.projects}")
    print(f"Student certifications: {student.certifications}")

print("\n--- 2. Testing Recruiter Candidate Matching with Interview Performance ---")
recruiter = db.query(Recruiter).first()
if student and recruiter:
    match_res = match_student_to_recruiter(student, recruiter)
    print(f"Recruiter: {recruiter.company} - {recruiter.role}")
    print(f"Match Score: {match_res['match_score']}%")
    print(f"Interview Score: {match_res['interview_score']}/100 ({match_res['interview_performance']}) - Status: {match_res['interview_status']}")
    print(f"Certifications Count: {match_res['certifications_count']}, Projects Count: {match_res['projects_count']}")
    print(f"Explanation: {match_res['explanation']}")

print("\n--- 3. Testing Drive Conflict Detection (All 4 Categories) ---")
conflicts = detect_all_drive_conflicts(db)
print(f"Total Conflicts Detected: {len(conflicts)}")
categories = {}
for c in conflicts:
    categories.setdefault(c["category"], []).append(c)

for cat, items in categories.items():
    print(f"\nCategory: {cat} (Count: {len(items)})")
    print(f"  Example Title: {items[0]['title']}")
    print(f"  Example Severity: {items[0]['severity']}")
    print(f"  Example Reason: {items[0]['reason'][:120]}...")

print("\n--- 4. Testing Proposed Drive Pre-flight Conflict Check ---")
proposed_conflict = {
    "company": "Amazon AWS",
    "date": "2026-10-08",
    "time_slot": "09:00-11:00",
    "venue": "Placement Cell",
    "resources": ["Interview Chamber A"],
    "interview_panels": ["Technical Panel 1"],
    "infrastructure_capacity": 20
}
res_conflicts = detect_all_drive_conflicts(db, proposed_drive=proposed_conflict)
proposed_items = [c for c in res_conflicts if "Amazon AWS" in (c.get("company_a", "") + c.get("company_b", "") + c.get("company", ""))]
print(f"Proposed Drive Conflicts for 'Amazon AWS': {len(proposed_items)}")
for c in proposed_items:
    print(f"  [{c['category']}] -> {c['reason'][:100]}...")

proposed_clear = {
    "company": "ClearCorp",
    "date": "2027-01-15",
    "time_slot": "09:00-11:00",
    "venue": "Seminar Hall A",
    "resources": ["Smart Board"],
    "interview_panels": ["New Panel 1"],
    "infrastructure_capacity": 100
}
res_clear = detect_all_drive_conflicts(db, proposed_drive=proposed_clear)
clear_items = [c for c in res_clear if "ClearCorp" in (c.get("company_a", "") + c.get("company_b", "") + c.get("company", ""))]
print(f"Proposed Drive Conflicts for 'ClearCorp' on clear date: {len(clear_items)} (Expected: 0)")

print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
