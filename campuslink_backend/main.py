"""
main.py — CampusLink FastAPI entry point.

Run with:
    uvicorn main:app --reload

Then open:
    http://127.0.0.1:8000/docs   (interactive Swagger UI)
"""

from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Student, Recruiter, Drive, Offer
from notifications import notify_shortlist, notify_drive_announcement, notify_offer_status
from ml_matching import match_student_to_recruiter, rank_recruiters_for_student, rank_students_for_recruiter

# Creates campuslink.db and all four tables on first run, if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CampusLink API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic schemas (request/response shapes)
# ---------------------------------------------------------------------------

class StudentIn(BaseModel):
    name: str
    branch: str
    cgpa: float
    backlogs: int = 0
    skills: List[str] = []
    certifications: List[str] = []
    mock_interview_score: Optional[int] = None


class StudentOut(StudentIn):
    id: int
    class Config:
        from_attributes = True


class RecruiterIn(BaseModel):
    company: str
    role: str
    required_skills: List[str] = []
    min_cgpa: float = 0
    eligible_branches: List[str] = []


class RecruiterOut(RecruiterIn):
    id: int
    class Config:
        from_attributes = True


class DriveIn(BaseModel):
    company: str
    recruiter_id: Optional[int] = None
    date: str
    time_slot: str
    venue: str


class DriveOut(DriveIn):
    id: int
    status: str
    class Config:
        from_attributes = True


class OfferIn(BaseModel):
    student_id: int
    recruiter_id: int
    ctc_lpa: Optional[float] = None


class OfferStatusUpdate(BaseModel):
    status: str
    joining_date: Optional[str] = None


class OfferOut(BaseModel):
    id: int
    student_id: int
    recruiter_id: int
    status: str
    ctc_lpa: Optional[float]
    joining_date: Optional[str]
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Business logic — readiness scoring & matching
# ---------------------------------------------------------------------------

def readiness_score(student: Student):
    breakdown = {
        "cgpa": round(min(student.cgpa / 10 * 40, 40), 1),
        "certifications": min(len(student.certifications) * 8, 20),
        "mock_interview": round((student.mock_interview_score or 0) / 100 * 30, 1),
        "backlog_penalty": -student.backlogs * 5,
    }
    total = max(0, min(100, round(sum(breakdown.values()), 1)))
    label = (
        "Highly Employable" if total >= 85 else
        "Ready" if total >= 65 else
        "Developing" if total >= 40 else
        "Not Ready"
    )
    return total, label, breakdown


def old_match_student_to_recruiter(student: Student, recruiter: Recruiter):
    required = set(s.lower() for s in recruiter.required_skills)
    have = set(s.lower() for s in student.skills)
    missing = sorted(required - have)
    coverage = round(len(required & have) / len(required) * 100, 1) if required else 100.0

    cgpa_ok = student.cgpa >= recruiter.min_cgpa
    branch_ok = student.branch in recruiter.eligible_branches

    reasons = []
    reasons.append(
        f"CGPA {student.cgpa} meets the minimum of {recruiter.min_cgpa}." if cgpa_ok
        else f"CGPA {student.cgpa} is below the required minimum of {recruiter.min_cgpa}."
    )
    reasons.append(
        "All required skills are covered." if not missing
        else f"Skill gap in: {', '.join(missing)}."
    )
    if not branch_ok:
        reasons.append(f"Branch '{student.branch}' is not in the eligible list {recruiter.eligible_branches}.")

    eligible = cgpa_ok and branch_ok
    status = "Shortlisted" if eligible and coverage >= 60 else "Below Threshold" if eligible else "Not Eligible"

    match_score = round(coverage * 0.6 + (student.cgpa / 10 * 100) * 0.2 +
                         (student.mock_interview_score or 0) * 0.2, 1)

    return {
        "student_id": student.id,
        "student_name": student.name,
        "recruiter_id": recruiter.id,
        "role": recruiter.role,
        "company": recruiter.company,
        "match_score": match_score,
        "status": status,
        "missing_skills": missing,
        "coverage_percent": coverage,
        "explanation": " ".join(reasons),
    }


def _slots_overlap(a: str, b: str) -> bool:
    a_start, a_end = [x.strip() for x in a.split("-")]
    b_start, b_end = [x.strip() for x in b.split("-")]
    return a_start < b_end and b_start < a_end


# ---------------------------------------------------------------------------
# Routes — Students
# ---------------------------------------------------------------------------

@app.post("/students", response_model=StudentOut)
def create_student(payload: StudentIn, db: Session = Depends(get_db)):
    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.get("/students", response_model=List[StudentOut])
def list_students(db: Session = Depends(get_db)):
    return db.query(Student).all()


@app.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    return student


@app.get("/students/{student_id}/readiness")
def get_readiness(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    score, label, breakdown = readiness_score(student)
    return {"score": score, "label": label, "breakdown": breakdown}


@app.get("/students/{student_id}/matches")
def get_student_matches(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    recruiters = db.query(Recruiter).all()
    results = [match_student_to_recruiter(student, r) for r in recruiters]
    return sorted(results, key=lambda r: r["match_score"], reverse=True)


# ---------------------------------------------------------------------------
# Routes — Recruiters
# ---------------------------------------------------------------------------

@app.post("/recruiters", response_model=RecruiterOut)
def create_recruiter(payload: RecruiterIn, db: Session = Depends(get_db)):
    recruiter = Recruiter(**payload.model_dump())
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)
    return recruiter


@app.get("/recruiters", response_model=List[RecruiterOut])
def list_recruiters(db: Session = Depends(get_db)):
    return db.query(Recruiter).all()


@app.get("/recruiters/{recruiter_id}/candidates")
def get_candidates(recruiter_id: int, db: Session = Depends(get_db)):
    recruiter = db.get(Recruiter, recruiter_id)
    if not recruiter:
        raise HTTPException(404, "Recruiter not found")
    students = db.query(Student).all()
    results = [match_student_to_recruiter(s, recruiter) for s in students]
    return sorted(results, key=lambda r: r["match_score"], reverse=True)


@app.post("/recruiters/{recruiter_id}/shortlist/{student_id}")
def shortlist_student(recruiter_id: int, student_id: int, db: Session = Depends(get_db)):
    """Finalizes a shortlist decision for one student against one role,
    and triggers a shortlist notification if they qualify."""
    recruiter = db.get(Recruiter, recruiter_id)
    student = db.get(Student, student_id)
    if not recruiter or not student:
        raise HTTPException(404, "Recruiter or student not found")

    match = match_student_to_recruiter(student, recruiter)
    if match["status"] == "Shortlisted":
        notify_shortlist(student.name, recruiter.role, recruiter.company)

    return match


# ---------------------------------------------------------------------------
# Routes — Drives
# ---------------------------------------------------------------------------

@app.post("/drives", response_model=DriveOut)
def create_drive(payload: DriveIn, db: Session = Depends(get_db)):
    drive = Drive(**payload.model_dump())
    db.add(drive)
    db.commit()
    db.refresh(drive)

    role = "a role"
    if drive.recruiter_id:
        recruiter = db.get(Recruiter, drive.recruiter_id)
        if recruiter:
            role = recruiter.role
    notify_drive_announcement(drive.company, role, drive.date, drive.venue)

    return drive


@app.get("/drives", response_model=List[DriveOut])
def list_drives(db: Session = Depends(get_db)):
    return db.query(Drive).all()


@app.get("/drives/conflicts")
def drive_conflicts(db: Session = Depends(get_db)):
    drives = db.query(Drive).all()
    conflicts = []
    for i in range(len(drives)):
        for j in range(i + 1, len(drives)):
            a, b = drives[i], drives[j]
            if a.date == b.date and a.venue == b.venue and _slots_overlap(a.time_slot, b.time_slot):
                conflicts.append({
                    "drive_a": a.id, "drive_b": b.id,
                    "reason": f"Venue '{a.venue}' double-booked on {a.date} "
                              f"({a.time_slot} vs {b.time_slot})."
                })
    return conflicts


# ---------------------------------------------------------------------------
# Routes — Offers
# ---------------------------------------------------------------------------

@app.post("/offers", response_model=OfferOut)
def create_offer(payload: OfferIn, db: Session = Depends(get_db)):
    offer = Offer(**payload.model_dump(), status="Issued")
    db.add(offer)
    db.commit()
    db.refresh(offer)

    student = db.get(Student, offer.student_id)
    recruiter = db.get(Recruiter, offer.recruiter_id)
    if student and recruiter:
        notify_offer_status(student.name, "Issued", recruiter.company)

    return offer


@app.get("/offers", response_model=List[OfferOut])
def list_offers(db: Session = Depends(get_db)):
    return db.query(Offer).all()


@app.put("/offers/{offer_id}/status", response_model=OfferOut)
def update_offer_status(offer_id: int, payload: OfferStatusUpdate, db: Session = Depends(get_db)):
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer.status = payload.status
    if payload.joining_date:
        offer.joining_date = payload.joining_date
    db.commit()
    db.refresh(offer)

    student = db.get(Student, offer.student_id)
    recruiter = db.get(Recruiter, offer.recruiter_id)
    if student and recruiter:
        notify_offer_status(student.name, offer.status, recruiter.company)

    return offer


# ---------------------------------------------------------------------------
# Routes — Analytics
# ---------------------------------------------------------------------------

@app.get("/analytics/dashboard")
def analytics_dashboard(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    offers = db.query(Offer).all()

    branch_wise = {}
    for s in students:
        branch_wise.setdefault(s.branch, {"total": 0, "placed": 0})
        branch_wise[s.branch]["total"] += 1

    placed_ids = {o.student_id for o in offers if o.status in ("Accepted", "Joined")}
    for s in students:
        if s.id in placed_ids:
            branch_wise[s.branch]["placed"] += 1

    accepted_ctcs = [o.ctc_lpa for o in offers if o.ctc_lpa and o.status in ("Accepted", "Joined")]

    return {
        "total_students": len(students),
        "offers_made": len(offers),
        "offers_accepted": len([o for o in offers if o.status in ("Accepted", "Joined")]),
        "offers_pending": len([o for o in offers if o.status == "Issued"]),
        "branch_wise_conversion": branch_wise,
        "average_ctc_lpa": round(sum(accepted_ctcs) / len(accepted_ctcs), 2) if accepted_ctcs else None,
        "highest_ctc_lpa": max(accepted_ctcs) if accepted_ctcs else None,
    }
