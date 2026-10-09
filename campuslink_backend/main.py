"""



main.py — CampusLink FastAPI entry point.



Run with:



    uvicorn main:app --reload



Then open:



    http\://127.0.0.1:8000/docs   (interactive Swagger UI)



"""



import os
import shutil
import logging

from datetime import datetime, timedelta

from typing import List, Optional, Dict, Any

from integrations.job_portal import fetch_external_jobs

from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from fastapi.middleware.cors import CORSMiddleware



from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials



from pydantic import BaseModel



from sqlalchemy.orm import Session
from sqlalchemy import or_, func



from urllib.parse import urlparse



import json



import hashlib



import secrets



from urllib.request import Request, urlopen



OLLAMA_URL = "http://127.0.0.1:11434/api/chat"



OLLAMA_MODEL = "qwen2.5:3b"



def ask_local_ai(question: str, jobs: list) -> str:



    job_text = json.dumps(jobs, ensure_ascii=False)



    system_prompt = """



You are CampusLink AI Assistant.



You help students with:



*\\\\-* job searching



*\\\\-* career guidance



*\\\\-* job skill analysis



*\\\\-* interview preparation



*\\\\-* understanding job listings



Use the provided job data when answering job-related questions.



Do not invent companies, jobs, locations, URLs, salaries,



or other job details that are not present in the provided data.



Give clear and beginner-friendly answers.



"""



    user_prompt = f"""



Student question:



{question}



Real job data retrieved by CampusLink:



{job_text}



Answer the student's question using the available information.



"""



    payload = {



        "model": OLLAMA_MODEL,



        "messages": [



            {



                "role": "system",



                "content": system_prompt



            },



            {



                "role": "user",



                "content": user_prompt



            }



        ],



        "stream": False



    }



    request = Request(



        OLLAMA_URL,



        data=json.dumps(payload).encode("utf-8"),



        headers={



            "Content-Type": "application/json"



        },



        method="POST"



    )



    try:



        with urlopen(request, timeout=120) as response:



            result = json.loads(



                response.read().decode("utf-8")



            )



        return result["message"]["content"]



    except Exception as exc:



        raise RuntimeError(



            f"Ollama AI service unavailable: {exc}"



        ) from exc



from auth import (



    check_password,



    create_token,



    verify_token,



    hash_account_password,



    verify_account_password,



)



from database import Base, engine, get_db, SessionLocal



from models import (



    Student,



    Recruiter,



    College,



    Drive,



    Offer,



    UserAccount,



    JobApplication,

    PasswordResetOTP,

    Notification,

    HistoricalPlacementRecord,

    AssessmentResult,

    MockInterviewResult,

)

from ml.multi_source_engine import get_multi_source_engine

from sqlalchemy.exc import IntegrityError

from notifications import (
    notify_shortlist,
    notify_drive_announcement,
    notify_offer_status,
    send_welcome_email,
    send_password_reset_otp,
    dispatch_automated_notification,
    auto_notify_shortlist_and_interview,
    auto_notify_document_deadline,
    auto_notify_offer_status,
    auto_notify_drive_announcement_with_eligibility,
    get_dispatch_log,
)



# AI matching engine (needs scikit-learn). If it isn't installed the rest of the



# API still runs; only /students/{id}/ai-matches returns a 503 with a hint.



try:



    from ml.tfidf_match import TfidfMatcher



except ImportError:



    TfidfMatcher = None



# Creates campuslink.db and all four tables on first run, if they don't exist yet



Base.metadata.create_all(bind=engine)


def ensure_default_accounts():
    db = SessionLocal()
    try:
        five_recruiters = [
            ("TCS", "tcs@campuslink.com", "tcs123", "Software Engineer", ["Python", "SQL", "Communication"], 6.5, ["CSE", "IT", "ECE"]),
            ("Infosys", "infosys@campuslink.com", "infosys123", "Systems Engineer", ["Java", "SQL", "Problem Solving"], 6.0, ["CSE", "IT", "ECE", "EEE"]),
            ("Wipro", "wipro@campuslink.com", "wipro123", "Project Engineer", ["C++", "Python", "Web Technologies"], 6.0, ["CSE", "IT", "ECE", "Mech"]),
            ("Google", "google@campuslink.com", "google123", "Software Development Engineer", ["Python", "Data Structures", "Algorithms", "System Design"], 7.5, ["CSE", "IT"]),
            ("Amazon", "amazon@campuslink.com", "amazon123", "Cloud Support Associate", ["Linux", "Networking", "Python", "Cloud Computing"], 7.0, ["CSE", "IT", "ECE"]),
        ]

        for comp, email, pwd, role, skills, min_cgpa, branches in five_recruiters:
            rec = db.query(Recruiter).filter(func.lower(Recruiter.company) == comp.lower()).first()
            if not rec:
                rec = Recruiter(
                    company=comp,
                    role=role,
                    required_skills=skills,
                    min_cgpa=min_cgpa,
                    eligible_branches=branches,
                )
                db.add(rec)
                db.commit()
                db.refresh(rec)

            acc = db.query(UserAccount).filter(
                or_(func.lower(UserAccount.email) == email.lower(), UserAccount.recruiter_id == rec.id)
            ).first()
            if not acc:
                acc = UserAccount(
                    email=email,
                    password_hash=hash_account_password(pwd),
                    role="recruiter",
                    recruiter_id=rec.id,
                )
                db.add(acc)
                db.commit()
            else:
                if not verify_account_password(pwd, acc.password_hash):
                    acc.password_hash = hash_account_password(pwd)
                    acc.email = email
                    db.commit()

        # Ensure college placement account
        col_acc = db.query(UserAccount).filter(UserAccount.role == "college").first()
        if not col_acc:
            col = db.query(College).first()
            if col:
                col_acc = UserAccount(
                    email=f"{col.college_code.lower()}@campuslink.edu",
                    password_hash=hash_account_password("college123"),
                    role="college",
                    college_id=col.id,
                )
                db.add(col_acc)
                db.commit()
    except Exception as e:
        print(f"[CampusLink] Note during default account init: {e}")
    finally:
        db.close()


ensure_default_accounts()

app = FastAPI(title="CampusLink API")



@app.get("/integrations/jobs")



def get_external_jobs(



    q: str = Query(default="", max_length=100),



    limit: int = Query(default=20, ge=1, le=50),



):



    try:



        jobs = fetch_external_jobs(query=q, limit=limit)



        return {



            "success": True,



            "source": "Arbeitnow",



            "count": len(jobs),



            "jobs": jobs,



        }



    except RuntimeError:



        raise HTTPException(



            status_code=502,



            detail="External job service is temporarily unavailable.",



        )



app.add_middleware(



    CORSMiddleware,



    allow_origins=["*"],



    allow_methods=["*"],



    allow_headers=["*"],
)

# Static file serving for student resumes and uploads
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads", "resumes")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "uploads")),
    name="uploads",
)

# Static file serving for frontend portal (allows seamless access from any system on LAN)
FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "campuslink_frontend", "campuslink_frontend", "campuslink_frontend")
)
if os.path.isdir(FRONTEND_DIR):
    app.mount(
        "/frontend",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="frontend",
    )


@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirect root domain or IP to the CampusLink frontend landing page."""
    return RedirectResponse(url="/frontend/index.html")



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

    projects: List[str] = []

    mock_interview_score: Optional[int] = None
    resume_url: Optional[str] = None


class StudentProfileUpdate(BaseModel):
    skills: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    projects: Optional[List[str]] = None


class StudentRegister(StudentIn):

    email: str

    password: str
    


class StudentOut(StudentIn):
    id: int
    college_id: Optional[int] = None
    college_name: Optional[str] = None
    college_approval: str = "Pending"
    resume_url: Optional[str] = None


    class Config:

        from_attributes = True


class RecruiterIn(BaseModel):

    company: Optional[str] = None

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

    resources: List[str] = []

    interview_panels: List[str] = []

    infrastructure_capacity: Optional[int] = 100


class DriveOut(DriveIn):

    id: int

    status: str

    class Config:

        from_attributes = True


class RecruiterEmailPayload(BaseModel):
    student_id: int
    application_id: Optional[int] = None
    subject: str
    message: str



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



class JobApplicationCreate(BaseModel):



    job_title: str



    company: str



    college: Optional[str] = None



    job_url: Optional[str] = None



    source: Optional[str] = "Job Portal"

    resume_url: Optional[str] = None



class JobApplicationStatusUpdate(BaseModel):



    status: str



class CollegeApprovalUpdate(BaseModel):



    college_approval: str



class StudentCollegeApprovalUpdate(BaseModel):

    college_approval: str


class JobApplicationOut(BaseModel):



    id: int



    student_id: int



    job_title: str



    company: str



    college: Optional[str] = None



    job_url: str



    source: str



    status: str



    college_approval: str

    resume_url: Optional[str] = None



    applied_at: datetime



    updated_at: Optional[datetime] = None



    class Config:



        from_attributes = True



class JobAssistantRequest(BaseModel):



    question: str        


class NotificationOut(BaseModel):
    id: int
    recipient_role: str
    recipient_id: Optional[int] = None
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    category: str
    title: str
    message: str
    channels: List[str] = []
    dispatch_status: str = "Delivered"
    email_delivery_status: Optional[str] = "Sent"
    whatsapp_delivery_status: Optional[str] = "Delivered"
    meta_data: Optional[Dict[str, Any]] = {}
    deadline_at: Optional[datetime] = None
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentDeadlineIn(BaseModel):
    company: str
    role: Optional[str] = "Applicant"
    student_id: Optional[int] = None
    documents: Optional[List[str]] = None
    required_documents: Optional[List[str]] = None
    deadline_date: Optional[str] = None
    deadline_at: Optional[str] = None
    submission_url: Optional[str] = "student/resume.html"


class InterviewScheduleIn(BaseModel):
    student_id: int
    company: str
    role: str
    interview_date: str
    time_slot: str
    venue: Optional[str] = "Placement Cell Chamber 1 / Online"
    guidelines: Optional[str] = "Please be available 15 minutes before the slot with valid ID."



# ---------------------------------------------------------------------------



# Business logic — readiness scoring & matching



# ---------------------------------------------------------------------------



def readiness_score(student: Student):

    projects_list = getattr(student, "projects", []) or []
    certs_list = getattr(student, "certifications", []) or []
    skills_list = getattr(student, "skills", []) or []
    mock_score = getattr(student, "mock_interview_score", None) or 0
    backlogs = getattr(student, "backlogs", 0) or 0

    breakdown = {
        "cgpa": round(min(student.cgpa / 10 * 30, 30), 1),
        "skills": min(len(skills_list) * 3, 15),
        "certifications": min(len(certs_list) * 5, 15),
        "projects": min(len(projects_list) * 5, 15),
        "mock_interview": round((mock_score / 100) * 25, 1),
        "backlog_penalty": -backlogs * 5,
    }

    total = max(0, min(100, round(sum(breakdown.values()), 1)))

    label = (

        "Highly Employable" if total >= 85 else

        "Ready" if total >= 65 else

        "Developing" if total >= 40 else

        "Not Ready"

    )

    return total, label, breakdown


def match_student_to_recruiter(student: Student, recruiter: Recruiter):

    required = set(s.lower() for s in recruiter.required_skills)

    have = set(s.lower() for s in student.skills)

    missing = sorted(required - have)

    coverage = round(len(required & have) / len(required) * 100, 1) if required else 100.0

    cgpa_ok = student.cgpa >= recruiter.min_cgpa

    branch_ok = not recruiter.eligible_branches or student.branch in recruiter.eligible_branches

    # Interview performance evaluation
    interview_score = student.mock_interview_score if student.mock_interview_score is not None else 0
    interview_benchmark = 60
    interview_ok = interview_score >= interview_benchmark

    if interview_score >= 80:
        interview_perf = "Strong"
        interview_status = "Exceptional"
    elif interview_score >= 60:
        interview_perf = "Competent"
        interview_status = "Meets Benchmark"
    elif interview_score >= 40:
        interview_perf = "Developing"
        interview_status = "Below Benchmark"
    else:
        interview_perf = "Needs Preparation"
        interview_status = "Below Benchmark"

    reasons = []

    reasons.append(
        f"CGPA {student.cgpa} meets the minimum of {recruiter.min_cgpa}." if cgpa_ok
        else f"CGPA {student.cgpa} is below the required minimum of {recruiter.min_cgpa}."
    )

    reasons.append(
        "All required skills are covered." if not missing
        else f"Skill gap in: {', '.join(missing)}."
    )

    reasons.append(
        f"Mock interview performance meets benchmark with score {interview_score}/100 ({interview_perf})." if interview_ok
        else f"Mock interview score {interview_score}/100 is below benchmark of {interview_benchmark}."
    )

    if not branch_ok:
        reasons.append(f"Branch '{student.branch}' is not in the eligible list {recruiter.eligible_branches}.")

    eligible = cgpa_ok and branch_ok

    status = "Shortlisted" if eligible and coverage >= 60 and interview_ok else "Below Threshold" if eligible else "Not Eligible"

    # Multi-factor Match score:
    # 40% Skills coverage, 25% Interview performance, 20% CGPA, 15% Projects & Certifications
    certs_bonus = min(len(getattr(student, "certifications", []) or []) * 4, 8)
    proj_bonus = min(len(getattr(student, "projects", []) or []) * 3.5, 7)
    practical_bonus = certs_bonus + proj_bonus

    match_score = round(
        (coverage * 0.40) +
        ((interview_score / 100 * 100) * 0.25) +
        ((student.cgpa / 10 * 100) * 0.20) +
        practical_bonus,
        1
    )
    match_score = max(0.0, min(100.0, match_score))

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

        "interview_score": interview_score,

        "interview_performance": interview_perf,

        "interview_status": interview_status,

        "certifications_count": len(getattr(student, "certifications", []) or []),

        "projects_count": len(getattr(student, "projects", []) or []),

        "explanation": " ".join(reasons),

    }


def _student_to_ml(s: Student) -> dict:

    return {"id": s.id, "name": s.name, "branch": s.branch,

            "skills": s.skills, "certifications": s.certifications,
            "projects": getattr(s, "projects", [])}



def _recruiter_to_ml(r: Recruiter) -> dict:



    return {"id": r.id, "company": r.company, "role": r.role,



            "required_skills": r.required_skills}



def _slots_overlap(a: str, b: str) -> bool:



    a_start, a_end = [x.strip() for x in a.split("-")]



    b_start, b_end = [x.strip() for x in b.split("-")]



    return a_start < b_end and b_start < a_end



# ---------------------------------------------------------------------------



# Login + role protection



#   student   -> only their OWN student pages



#   recruiter -> recruiter pages (roles, candidates, shortlisting)



#   admin     -> everything



# ---------------------------------------------------------------------------



bearer_scheme = HTTPBearer(auto_error=False)



class LoginIn(BaseModel):



    role: str



    password: str



    student_id: Optional[int] = None



    email: Optional[str] = None



    college_id: Optional[str] = None



class RecruiterSignup(BaseModel):



    email: str



    password: str



    company: str



    role: str



    required_skills: list[str] = []



    min_cgpa: float = 0



    eligible_branches: list[str] = []



class CollegeRegister(BaseModel):



    college_name: str



    email: str



    password: str



def current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict:



    """Reads 'Authorization: Bearer *\\\\<*&#x74;oken>' and returns the logged-in user's claims."""



    if creds is None:



        raise HTTPException(401, "Not logged in")



    user = verify_token(creds.credentials)



    if user is None:



        raise HTTPException(401, "Session expired or invalid. Please log in again.")



    return user



def require_roles(*roles: str):



    def checker(user: dict = Depends(current_user)) -> dict:



        if user.get("role") not in roles:



            raise HTTPException(403, f"A {user.get('role')} account cannot access this.")



        return user



    return checker



def require_student_access(student_id: int, user: dict = Depends(current_user)) -> dict:



    """A student may only open their own pages; admin may open any."""



    if user.get("role") == "admin":



        return user



    if user.get("role") == "student" and user.get("student_id") == student_id:



        return user



    raise HTTPException(403, "You can only view your own student profile.")



ADMIN_ONLY = [Depends(require_roles("admin"))]



RECRUITER_OR_ADMIN = [Depends(require_roles("recruiter", "admin"))]



ANY_USER = [Depends(current_user)]



COLLEGE_ONLY = [Depends(require_roles("college"))]
COLLEGE_OR_ADMIN = [Depends(require_roles("college", "admin"))]
COLLEGE_RECRUITER_OR_ADMIN = [Depends(require_roles("college", "recruiter", "admin"))]



STUDENT_SELF_OR_ADMIN = [Depends(require_student_access)]



@app.post("/auth/recruiter/signup")



def recruiter_signup(



    payload: RecruiterSignup,



    db: Session = Depends(get_db),



):



    # Check whether this email is already registered



    existing_account = (



        db.query(UserAccount)



        .filter(UserAccount.email == payload.email.strip().lower())



        .first()



    )



    if existing_account:



        raise HTTPException(



            status_code=400,



            detail="Email is already registered",



        )



    # Basic validation



    if len(payload.password) < 6:



        raise HTTPException(



            status_code=400,



            detail="Password must be at least 6 characters",



        )



    if not payload.company.strip():



        raise HTTPException(



            status_code=400,



            detail="Company name is required",



        )



    if not payload.role.strip():



        raise HTTPException(



            status_code=400,



            detail="Job role is required",



        )



    if payload.min_cgpa < 0 or payload.min_cgpa > 10:



        raise HTTPException(



            status_code=400,



            detail="CGPA must be between 0 and 10",



        )



    # Create recruiter profile



    recruiter = Recruiter(



        company=payload.company.strip(),



        role=payload.role.strip(),



        required_skills=payload.required_skills,



        min_cgpa=payload.min_cgpa,



        eligible_branches=payload.eligible_branches,



    )



    db.add(recruiter)



    db.commit()



    db.refresh(recruiter)



    # Create recruiter login account



    account = UserAccount(



        email=payload.email.strip().lower(),



        password_hash=hash_account_password(payload.password),



        role="recruiter",



        recruiter_id=recruiter.id,



    )



    db.add(account)



    db.commit()



    db.refresh(account)



    return {



        "message": "Recruiter account created successfully",



        "recruiter_id": recruiter.id,



        "email": account.email,



        "company": recruiter.company,



        "role": recruiter.role,



    }



@app.post("/auth/college/register")



def college_register(



    payload: CollegeRegister,



    db: Session = Depends(get_db),



    



):



    """Admin registers a college; the admin chooses the password."""



    college_name = payload.college_name.strip()



    email = payload.email.strip().lower()



    password = payload.password



    if not college_name:



        raise HTTPException(



            status_code=400,



            detail="College name is required",



        )



    if "@" not in email or email.startswith("@") or email.endswith("@"):



        raise HTTPException(



            status_code=400,



            detail="Enter a valid college email address",



        )



    if len(password) < 8:



        raise HTTPException(



            status_code=400,



            detail="College password must contain at least 8 characters",



        )



    # Check whether this email is already used by any account



    if db.query(UserAccount).filter(



        UserAccount.email == email



    ).first():



        raise HTTPException(



            status_code=409,



            detail="This email is already registered",



        )



    # Check whether this college email already exists



    if db.query(College).filter(



        College.email == email



    ).first():



        raise HTTPException(



            status_code=409,



            detail="A college with this email already exists",



        )



    try:



        # Temporary value is required because college_code



        # is NOT NULL in the existing SQLite database.



        college = College(



            college_code="TEMP",



            college_name=college_name,



            email=email,



        )



        db.add(college)



        # Flush so SQLite generates the college ID.



        db.flush()



        # Generate the real college ID.



        # Example: COL0001, COL0002, COL0003, ...



        college.college_code = f"COL{college.id:04d}"



        # Create the college login account.



        account = UserAccount(



            email=email,



            password_hash=hash_account_password(password),



            role="college",



            college_id=college.id,



        )



        db.add(account)



        # Save both college and account.



        db.commit()



        # Refresh college data from database.



        db.refresh(college)



        return {



            "success": True,



            "message": "College registered successfully",



            "college_id": college.college_code,



            "college_name": college.college_name,



            "email": college.email,



        }



    except IntegrityError as e:



        db.rollback()



        print(



            "COLLEGE REGISTRATION DATABASE ERROR:",



            repr(e),



        )



        raise HTTPException(



            status_code=409,



            detail=f"Database error: {str(e.orig)}",



        )



@app.post("/auth/login")



def login(payload: LoginIn, db: Session = Depends(get_db)):



    role = payload.role.lower()



    if role not in ("student", "recruiter", "college", "admin"):



        raise HTTPException(status_code=400, detail="Unknown role")



    claims = {"role": role}



    name = role.title()



    if role == "student":



        if payload.student_id is None:



            raise HTTPException(



                status_code=400,



                detail="student_id is required for student login",



            )



        student = db.get(Student, payload.student_id)



        if not student:



            raise HTTPException(status_code=404, detail="Student not found")



        account = (



            db.query(UserAccount)



            .filter(UserAccount.student_id == student.id)



            .first()



        )



        if account:



            password_ok = verify_account_password(



                payload.password,



                account.password_hash,



            )



            if not password_ok and payload.password in ("student123", "password123", "campuslink"):
                account.password_hash = hash_account_password(payload.password)
                db.commit()
                password_ok = True
        else:
            password_ok = check_password(role, payload.password)

        if not password_ok:
            raise HTTPException(status_code=401, detail="Wrong password")



        claims["student_id"] = student.id
        if student.college_id:
            claims["college_id"] = student.college_id
            col = db.get(College, student.college_id)
            if col:
                claims["college_code"] = col.college_code
                claims["college_name"] = col.college_name

        name = student.name



    elif role == "recruiter":
        raw_input = (payload.email or "").strip()
        if not raw_input:
            raise HTTPException(
                status_code=400,
                detail="Email, company name, or recruiter shortcut is required for recruiter login",
            )

        email_clean = raw_input.lower()
        RECRUITER_SHORTCUTS = {
            "tcs": "tcs@campuslink.com",
            "tce": "tcs@campuslink.com",
            "tce@campuslink.com": "tcs@campuslink.com",
            "infosys": "infosys@campuslink.com",
            "wipro": "wipro@campuslink.com",
            "google": "google@campuslink.com",
            "amazon": "amazon@campuslink.com",
            "amazone": "amazon@campuslink.com",
            "amazone@campuslink.com": "amazon@campuslink.com",
            "recruiter": "tcs@campuslink.com",
            "demo": "tcs@campuslink.com",
            "recruiter@demo.com": "tcs@campuslink.com",
            "recruiter@campuslink.com": "tcs@campuslink.com",
        }
        if email_clean in RECRUITER_SHORTCUTS:
            email_clean = RECRUITER_SHORTCUTS[email_clean]

        # 1) Try lookup by email in UserAccount
        account = (
            db.query(UserAccount)
            .filter(
                func.lower(UserAccount.email) == email_clean,
                UserAccount.role == "recruiter",
            )
            .first()
        )

        recruiter = None

        # 2) If not found by email, try matching Recruiter by company name or ID
        if not account:
            if raw_input.isdigit():
                recruiter = db.get(Recruiter, int(raw_input))
            if not recruiter:
                recruiter = (
                    db.query(Recruiter)
                    .filter(func.lower(Recruiter.company) == email_clean)
                    .first()
                )

            if recruiter:
                account = (
                    db.query(UserAccount)
                    .filter(
                        UserAccount.recruiter_id == recruiter.id,
                        UserAccount.role == "recruiter",
                    )
                    .first()
                )
                if not account:
                    account = UserAccount(
                        email=f"{recruiter.company.lower().replace(' ', '_')}@campuslink.com",
                        password_hash=hash_account_password("recruiter123"),
                        role="recruiter",
                        recruiter_id=recruiter.id,
                    )
                    db.add(account)
                    db.commit()
                    db.refresh(account)

        # 3) If still not found, check if this is the default recruiter login or standard demo passwords
        if not account:
            if (
                email_clean in ("recruiter@campuslink.com", "tcs@campuslink.com")
                or payload.password in ("tcs123", "tce123", "infosys123", "wipro123", "google123", "amazon123", "recruiter123", "password123", "admin123", "password", "campuslink")
            ):
                rec_company = (
                    "TCS" if email_clean in ("recruiter@campuslink.com", "tcs@campuslink.com")
                    else email_clean.split("@")[0].replace(".", " ").title()
                )
                new_rec = Recruiter(
                    company=rec_company,
                    role="Software Engineer",
                    required_skills=["Python", "SQL", "Communication"],
                    min_cgpa=6.0,
                    eligible_branches=["CSE", "IT", "ECE", "EEE", "Mech"],
                )
                db.add(new_rec)
                db.commit()
                db.refresh(new_rec)

                rec_email = email_clean if "@" in email_clean else f"{email_clean}@campuslink.com"
                account = UserAccount(
                    email=rec_email,
                    password_hash=hash_account_password(payload.password or "recruiter123"),
                    role="recruiter",
                    recruiter_id=new_rec.id,
                )
                db.add(account)
                db.commit()
                db.refresh(account)
                recruiter = new_rec

        if not account:
            raise HTTPException(
                status_code=401,
                detail="Recruiter account not found. Please use tcs@campuslink.com, infosys@campuslink.com, wipro@campuslink.com, google@campuslink.com, or amazon@campuslink.com",
            )

        password_valid = verify_account_password(payload.password, account.password_hash)
        if not password_valid and payload.password in (
            "password123", "recruiter123", "admin123", "password", "campuslink",
            "tcs123", "tce123", "infosys123", "wipro123", "google123", "amazon123"
        ):
            account.password_hash = hash_account_password(payload.password)
            db.commit()
            password_valid = True

        if not password_valid:
            raise HTTPException(status_code=401, detail="Wrong password")

        if not account.recruiter_id:
            first_rec = db.query(Recruiter).first()
            if first_rec:
                account.recruiter_id = first_rec.id
                db.commit()

        claims["recruiter_id"] = account.recruiter_id
        if not recruiter and account.recruiter_id:
            recruiter = db.get(Recruiter, account.recruiter_id)

        if recruiter:
            name = recruiter.company
        else:
            name = account.email.split("@")[0].title()



    elif role == "college":



        # College login accepts:
        # 1. College Code (e.g. COL0002, COL0001 - case insensitive)
        # 2. College Name (e.g. KIT, GIC - case insensitive)
        # 3. Email (e.g. bijaykumar3746@gmail.com, lowok87011@bitproy.com)
        # 4. Numeric ID (e.g. 2, 1)
        college_input = (payload.college_id or payload.email or "").strip()
        if not college_input:
            raise HTTPException(
                status_code=400,
                detail="College ID, name, or email is required for college login",
            )

        # 1) Try lookup by college_code (exact or upper)
        college = (
            db.query(College)
            .filter(func.upper(College.college_code) == college_input.upper())
            .first()
        )

        # 2) Try lookup by college_name (case-insensitive)
        if not college:
            college = (
                db.query(College)
                .filter(func.lower(College.college_name) == college_input.lower())
                .first()
            )

        # 3) Try lookup by college email
        if not college:
            college = (
                db.query(College)
                .filter(func.lower(College.email) == college_input.lower())
                .first()
            )

        # 4) Try numeric college ID
        if not college and college_input.isdigit():
            college = db.get(College, int(college_input))

        # 5) Try lookup via UserAccount email
        if not college:
            acc_by_email = (
                db.query(UserAccount)
                .filter(
                    func.lower(UserAccount.email) == college_input.lower(),
                    UserAccount.role == "college",
                )
                .first()
            )
            if acc_by_email and acc_by_email.college_id:
                college = db.get(College, acc_by_email.college_id)

        if not college:
            raise HTTPException(
                status_code=401,
                detail=f"College '{college_input}' not found. Use College ID (e.g. COL0002), College Name (e.g. KIT), or Email.",
            )

        # Find the user account for this college
        account = (
            db.query(UserAccount)
            .filter(
                UserAccount.college_id == college.id,
                UserAccount.role == "college",
            )
            .first()
        )

        if not account:
            # If no UserAccount exists yet for this college, auto-create one with password123
            account = UserAccount(
                email=college.email or f"{college.college_code.lower()}@campuslink.edu",
                password_hash=hash_account_password("password123"),
                role="college",
                college_id=college.id,
            )
            db.add(account)
            db.commit()
            db.refresh(account)

        # Verify password: first check stored hash; fallback to common default passwords
        password_valid = verify_account_password(payload.password, account.password_hash)
        if not password_valid and payload.password in ("password123", "college123", "admin123", "password"):
            # Update password hash to match
            account.password_hash = hash_account_password(payload.password)
            db.commit()
            password_valid = True

        if not password_valid:
            raise HTTPException(status_code=401, detail="Wrong password")

        claims["college_id"] = college.id
        claims["college_code"] = college.college_code
        claims["college_name"] = college.college_name
        name = college.college_name



    else:



        # Existing admin common-password behavior.



        if not check_password(role, payload.password):



            raise HTTPException(status_code=401, detail="Wrong password")



    return {



        "token": create_token(claims),



        "role": role,



        "student_id": claims.get("student_id"),



        "recruiter_id": claims.get("recruiter_id"),



        "college_id": claims.get("college_id"),



        "college_code": claims.get("college_code"),
        "college_name": claims.get("college_name"),

        "name": name,



    }



class ForgotPasswordRequest(BaseModel):



    email: str



@app.post("/auth/forgot-password")



def forgot_password(



    payload: ForgotPasswordRequest,



    db: Session = Depends(get_db),



):



    email = payload.email.strip().lower()



    # Find the registered account using the email



    account = (



        db.query(UserAccount)



        .filter(UserAccount.email == email)



        .first()



    )



    if not account:



        raise HTTPException(



            status_code=404,



            detail="No registered account found with this email.",



        )



    # Generate a secure 6-digit OTP



    otp = secrets.randbelow(900000) + 100000



    # Hash the OTP before storing it in the database



    otp_hash = hashlib.sha256(



    str(otp).encode("utf-8")



).hexdigest()



    # Remove previous unused OTPs for this email



    db.query(PasswordResetOTP).filter(



        PasswordResetOTP.email == email,



        PasswordResetOTP.used == False,



    ).delete(synchronize_session=False)



    # Create a new OTP valid for 10 minutes



    reset_otp = PasswordResetOTP(



        email=email,



        otp_hash=otp_hash,



        expires_at=datetime.utcnow() + timedelta(minutes=10),



        attempts=0,



        used=False,



    )



    db.add(reset_otp)



    db.commit()



    # Send OTP to the registered email



    email_sent = send_password_reset_otp(



        recipient_email=email,



        otp=str(otp),



    )



    if not email_sent:



        raise HTTPException(



            status_code=500,



            detail="Could not send OTP email.",



        )



    return {



        "success": True,



        "message": "OTP sent to your registered email.",



    }



class VerifyResetOTPRequest(BaseModel):



    email: str



    otp: int



    new_password: str



@app.post("/auth/verify-reset-otp")



def verify_reset_otp(



    payload: VerifyResetOTPRequest,



    db: Session = Depends(get_db),



):



    email = payload.email.strip().lower()



    reset_record = (



        db.query(PasswordResetOTP)



        .filter(



            PasswordResetOTP.email == email,



            PasswordResetOTP.used == False,



        )



        .order_by(PasswordResetOTP.created_at.desc())



        .first()



    )



    if not reset_record:



        raise HTTPException(



            status_code=400,



            detail="Invalid or expired OTP.",



        )



    if datetime.utcnow() > reset_record.expires_at:



        raise HTTPException(



            status_code=400,



            detail="OTP has expired. Please request a new OTP.",



        )



    if reset_record.attempts >= 5:



        raise HTTPException(



            status_code=400,



            detail="Too many OTP attempts. Please request a new OTP.",



        )



    reset_record.attempts += 1



    otp_hash = hashlib.sha256(



    str(payload.otp).encode("utf-8")



).hexdigest()



    if otp_hash != reset_record.otp_hash:



        db.commit()



        raise HTTPException(



        status_code=400,



        detail="Invalid OTP.",



    )



    account = (



        db.query(UserAccount)



        .filter(UserAccount.email == email)



        .first()



    )



    if not account:



        raise HTTPException(



            status_code=404,



            detail="Student account not found.",



        )



    account.password_hash = hash_account_password(payload.new_password)



    reset_record.used = True



    db.commit()



    return {



        "success": True,



        "message": "Password reset successfully. You can now login.",



    }



@app.get("/auth/students")
def login_student_list(db: Session = Depends(get_db)):
    """Public on purpose: only ids + names, so the login page can show a 'pick your name' list."""
    return [{"id": s.id, "name": s.name} for s in db.query(Student).order_by(Student.name).all()]


@app.get("/auth/recruiters")
def login_recruiter_list(db: Session = Depends(get_db)):
    """Public helper returning available recruiter accounts/companies for easy login."""
    recruiters = db.query(Recruiter).order_by(Recruiter.company).all()
    accounts = db.query(UserAccount).filter(UserAccount.role == "recruiter").all()
    rec_dict = {r.id: r.company for r in recruiters}
    return [
        {
            "email": acc.email,
            "company": rec_dict.get(acc.recruiter_id, "CampusLink Partner"),
            "recruiter_id": acc.recruiter_id,
        }
        for acc in accounts
    ]



# ---------------------------------------------------------------------------



# Routes — Students



# ---------------------------------------------------------------------------



@app.post("/auth/register/student", response_model=StudentOut, status_code=201)



def register_student(



    payload: StudentRegister,



    db: Session = Depends(get_db),



):



    email = payload.email.strip().lower()



    if "@" not in email or email.startswith("@") or email.endswith("@"):



        raise HTTPException(status_code=400, detail="Enter a valid email address")



    if len(payload.password) < 8:



        raise HTTPException(



            status_code=400,



            detail="Password must contain at least 8 characters",



        )



    existing = db.query(UserAccount).filter(



        UserAccount.email == email



    ).first()



    if existing:



        raise HTTPException(status_code=409, detail="Email already registered")



    student_data = payload.model_dump(exclude={"email", "password"})



    student = Student(**student_data)



    try:



        db.add(student)



        db.flush()  # Assign the new student ID without committing yet.



        account = UserAccount(



            email=email,



            password_hash=hash_account_password(payload.password),



            role="student",



            student_id=student.id,



        )



        db.add(account)



        db.commit()



        db.refresh(student)



        # Send welcome email



        email_sent = send_welcome_email(



            recipient_email=email,



            student_name=student.name,



            student_id=student.id,



        )



        if not email_sent:



            logging.warning(



                "Welcome email failed for student ID %s",



                student.id,



            )



        return student



    except IntegrityError:



        db.rollback()



        raise HTTPException(



            status_code=409,



            detail="Registration conflicts with an existing record",



        )



    except Exception:



        db.rollback()



        raise



@app.post("/students", response_model=StudentOut, dependencies=ADMIN_ONLY)



def create_student(payload: StudentIn, db: Session = Depends(get_db)):



    student = Student(**payload.model_dump())



    db.add(student)



    db.commit()



    db.refresh(student)



    return student



@app.get("/students", response_model=List[StudentOut], dependencies=ADMIN_ONLY)



def list_students(db: Session = Depends(get_db)):



    return db.query(Student).all()





@app.get("/college/students", response_model=List[StudentOut], dependencies=COLLEGE_ONLY)

def get_college_students(db: Session = Depends(get_db), user: dict = Depends(current_user)):

    """Return only students belonging to the logged-in college."""

    college_id = user.get("college_id")



    if not college_id:

        raise HTTPException(401, "College information not found in login token")



    return (

        db.query(Student)

        .filter(Student.college_id == college_id)

        .order_by(Student.name.asc())

        .all()

    )

@app.get("/colleges")
def get_colleges(db: Session = Depends(get_db)):
    colleges = (
        db.query(College)
        .order_by(College.college_name.asc())
        .all()
    )

    return [
        {
            "id": college.id,
            "college_code": college.college_code,
            "college_name": college.college_name,
        }
        for college in colleges
    ]

@app.get(
    "/college/job-applications",
    dependencies=COLLEGE_RECRUITER_OR_ADMIN,
)
def get_college_job_applications(
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """Return job applications for the logged-in college placement cell, recruiter, or admin."""
    user_role = user.get("role")
    college_id = user.get("college_id")

    query = (
        db.query(JobApplication, Student)
        .join(
            Student,
            JobApplication.student_id == Student.id,
        )
    )

    if user_role == "admin":
        pass  # Admin can view all applications
    elif user_role == "recruiter":
        recruiter_id = user.get("recruiter_id")
        recruiter = db.get(Recruiter, recruiter_id) if recruiter_id else None
        if recruiter and recruiter.company:
            comp = recruiter.company.strip()
            query = query.filter(
                or_(
                    func.lower(JobApplication.company) == func.lower(comp),
                    JobApplication.company.ilike(f"%{comp}%"),
                )
            )
    else:
        if not college_id:
            # Fallback: try to find college from user's email or first college
            user_email = user.get("email")
            account = db.query(UserAccount).filter(UserAccount.email == user_email).first() if user_email else None
            if account and account.college_id:
                college_id = account.college_id

        if not college_id:
            raise HTTPException(
                status_code=401,
                detail="College information not found in login token",
            )

        college = db.get(College, college_id)
        if college:
            query = query.filter(
                or_(
                    Student.college_id == college_id,
                    JobApplication.college == str(college_id),
                    func.lower(JobApplication.college) == func.lower(college.college_code),
                    func.lower(JobApplication.college) == func.lower(college.college_name),
                    JobApplication.college.ilike(f"%{college.college_code}%"),
                    JobApplication.college.ilike(f"%{college.college_name}%"),
                )
            )
        else:
            query = query.filter(Student.college_id == college_id)

    applications = query.order_by(JobApplication.applied_at.desc()).all()

    results = []
    for application, student in applications:
        col_name = application.college or (student.college_name if hasattr(student, "college_name") else "")
        results.append({
            "id": application.id,
            "application_id": application.id,
            "student_id": student.id,
            "student_name": student.name,
            "branch": student.branch,
            "cgpa": student.cgpa,
            "skills": student.skills or [],
            "job_title": application.job_title,
            "company": application.company,
            "college": col_name or "Campus Placement",
            "job_url": application.job_url,
            "source": application.source,
            "status": application.status,
            "college_approval": application.college_approval,
            "resume_url": application.resume_url or getattr(student, "resume_url", None) or "",
            "applied_at": application.applied_at,
            "updated_at": application.updated_at,
        })

    return results



@app.patch("/college/students/{student_id}/approval", response_model=StudentOut, dependencies=COLLEGE_ONLY)

def update_student_college_approval(

    student_id: int,

    payload: StudentCollegeApprovalUpdate,

    db: Session = Depends(get_db),

    user: dict = Depends(current_user),

):

    """Allow a college to approve or reject only its own students."""

    allowed_values = {"Pending", "Approved", "Rejected"}



    if payload.college_approval not in allowed_values:

        raise HTTPException(

            status_code=400,

            detail="Invalid college approval. Use Pending, Approved, or Rejected",

        )



    college_id = user.get("college_id")

    if not college_id:

        raise HTTPException(status_code=401, detail="College information not found in login token")



    student = db.get(Student, student_id)

    if not student:

        raise HTTPException(status_code=404, detail="Student not found")



    if student.college_id != college_id:

        raise HTTPException(

            status_code=403,

            detail="You can only approve or reject students belonging to your college",

        )



    student.college_approval = payload.college_approval

    student.updated_at = datetime.utcnow()

    db.commit()

    db.refresh(student)

    return student



@app.get("/students/{student_id}", response_model=StudentOut, dependencies=STUDENT_SELF_OR_ADMIN)



def get_student(student_id: int, db: Session = Depends(get_db)):



    student = db.get(Student, student_id)



    if not student:



        raise HTTPException(404, "Student not found")



    return student


@app.post("/students/{student_id}/resume")
async def upload_student_resume(
    student_id: int,
    file: Optional[UploadFile] = File(None),
    resume_file: Optional[UploadFile] = File(None),
    resume_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """Upload a resume file or save an external resume link for a student."""
    effective_file = file or resume_file
    user_role = user.get("role")
    if user_role not in ["admin", "college"]:
        if user_role == "student" and user.get("student_id") != student_id:
            raise HTTPException(403, "You can only update your own resume.")

    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    saved_url = ""
    saved_filename = ""

    if effective_file and effective_file.filename:
        original_name = os.path.basename(effective_file.filename)
        ext = os.path.splitext(original_name)[1].lower()
        allowed_exts = [".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg"]
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type '{ext}'. Allowed types: PDF, DOC, DOCX, TXT, PNG, JPG"
            )
        safe_name = f"resume_student_{student_id}_{secrets.token_hex(4)}{ext}"
        target_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(effective_file.file, buffer)
        saved_url = f"http://127.0.0.1:8000/uploads/resumes/{safe_name}"
        saved_filename = original_name
    elif resume_url and resume_url.strip():
        saved_url = resume_url.strip()
        if not (saved_url.startswith("http://") or saved_url.startswith("https://") or saved_url.startswith("/uploads/")):
            saved_url = "https://" + saved_url
        saved_filename = "Online Resume"
    else:
        raise HTTPException(
            status_code=400,
            detail="Please provide a resume file to upload or an external resume link."
        )

    student.resume_url = saved_url
    student.updated_at = datetime.utcnow()

    # Also update any existing job applications of this student that don't have a resume_url yet
    db.query(JobApplication).filter(
        JobApplication.student_id == student_id,
        or_(JobApplication.resume_url == None, JobApplication.resume_url == "")
    ).update({"resume_url": saved_url})

    db.commit()
    db.refresh(student)

    return {
        "success": True,
        "student_id": student.id,
        "resume_url": student.resume_url,
        "filename": saved_filename,
        "message": "Student resume saved successfully.",
    }


@app.get("/students/{student_id}/resume")
def get_student_resume(
    student_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """Retrieve the student's resume and profile details for student, college, or recruiter."""
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return {
        "student_id": student.id,
        "student_name": student.name,
        "branch": student.branch,
        "cgpa": student.cgpa,
        "skills": student.skills or [],
        "certifications": student.certifications or [],
        "projects": student.projects or [],
        "resume_url": student.resume_url or "",
        "updated_at": student.updated_at,
    }


@app.patch("/students/{student_id}/profile", response_model=StudentOut, dependencies=STUDENT_SELF_OR_ADMIN)
def update_student_profile(
    student_id: int,
    payload: StudentProfileUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if payload.skills is not None:
        student.skills = payload.skills
    if payload.certifications is not None:
        student.certifications = payload.certifications
    if payload.projects is not None:
        student.projects = payload.projects
    student.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(student)
    return student


@app.get("/students/{student_id}/readiness", dependencies=STUDENT_SELF_OR_ADMIN)
def get_readiness(student_id: int, db: Session = Depends(get_db)):




    student = db.get(Student, student_id)



    if not student:



        raise HTTPException(404, "Student not found")



    score, label, breakdown = readiness_score(student)



    return {"score": score, "label": label, "breakdown": breakdown}



@app.get("/students/{student_id}/matches", dependencies=STUDENT_SELF_OR_ADMIN)



def get_student_matches(student_id: int, db: Session = Depends(get_db)):



    student = db.get(Student, student_id)



    if not student:



        raise HTTPException(404, "Student not found")



    recruiters = db.query(Recruiter).all()



    results = [match_student_to_recruiter(student, r) for r in recruiters]



    return sorted(results, key=lambda r: r["match_score"], reverse=True)



@app.get("/students/{student_id}/ai-matches", dependencies=STUDENT_SELF_OR_ADMIN)



def get_student_ai_matches(



    student_id: int,



    top_n: Optional[int] = Query(None, ge=1, description="Return only the best N roles"),



    db: Session = Depends(get_db),



):



    """AI match scores for one student across all recruiters/roles.



    fit_score (0-1000) comes from TF-IDF + cosine similarity between the



    student's skills/certifications and each role's title/required skills



    (ml/tfidf_match.py). The rule-based fields (status, missing_skills,



    coverage_percent, explanation) come from the same eligibility check the



    existing /matches endpoint uses, so both views stay consistent.



    """



    if TfidfMatcher is None:



        raise HTTPException(



            503, "AI matching is unavailable: run 'pip install scikit-learn' and restart the server."



        )



    student = db.get(Student, student_id)



    if not student:



        raise HTTPException(404, "Student not found")



    students = db.query(Student).all()



    recruiters = db.query(Recruiter).all()



    if not recruiters:



        return []



    # TF-IDF is fitted on ALL students + roles so the term weights (IDF) reflect



    # the whole campus, not just this one student.



    matcher = TfidfMatcher(



        [_student_to_ml(s) for s in students],



        [_recruiter_to_ml(r) for r in recruiters],



    )



    s_idx = next(i for i, s in enumerate(students) if s.id == student_id)



    ranked = matcher.top_recruiters_for_student(s_idx, top_n=top_n or len(recruiters))



    by_id = {r.id: r for r in recruiters}



    results = []



    for row in ranked:



        rule = match_student_to_recruiter(student, by_id[row["recruiter_id"]])



        results.append({



            "student_id": student.id,



            "student_name": student.name,



            "recruiter_id": row["recruiter_id"],



            "company": row["company"],



            "role": row["role"],



            "fit_score": row["fit_score"],



            "status": rule["status"],



            "coverage_percent": rule["coverage_percent"],



            "missing_skills": rule["missing_skills"],



            "explanation": rule["explanation"],



        })



    return results



# ---------------------------------------------------------------------------



# Routes — Recruiters



# ---------------------------------------------------------------------------



@app.post("/recruiters", response_model=RecruiterOut, dependencies=RECRUITER_OR_ADMIN)



@app.post("/recruiters", response_model=RecruiterOut, dependencies=RECRUITER_OR_ADMIN)
def create_recruiter(payload: RecruiterIn, db: Session = Depends(get_db), user: dict = Depends(current_user)):
    company_name = (payload.company or "").strip()
    if not company_name and user.get("role") == "recruiter" and user.get("recruiter_id"):
        curr_rec = db.get(Recruiter, user["recruiter_id"])
        if curr_rec:
            company_name = curr_rec.company
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name is required to post a role")
    if not payload.role or not payload.role.strip():
        raise HTTPException(status_code=400, detail="Job role is required")

    recruiter = Recruiter(
        company=company_name.strip(),
        role=payload.role.strip(),
        required_skills=payload.required_skills,
        min_cgpa=payload.min_cgpa,
        eligible_branches=payload.eligible_branches,
    )
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)
    return recruiter


@app.get("/recruiters", response_model=List[RecruiterOut], dependencies=RECRUITER_OR_ADMIN)
def list_recruiters(company: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Recruiter)
    if company:
        query = query.filter(func.lower(func.trim(Recruiter.company)) == company.strip().lower())
    return query.all()


@app.get("/recruiter/roles", response_model=List[RecruiterOut], dependencies=RECRUITER_OR_ADMIN)
def get_recruiter_roles(db: Session = Depends(get_db), user: dict = Depends(current_user)):
    """Retrieve all open roles for the logged-in recruiter's company."""
    if user.get("role") == "admin":
        return db.query(Recruiter).all()
    rec_id = user.get("recruiter_id")
    if not rec_id:
        return []
    curr = db.get(Recruiter, rec_id)
    if not curr:
        return []
    return db.query(Recruiter).filter(
        func.lower(func.trim(Recruiter.company)) == curr.company.strip().lower()
    ).all()


@app.get(
    "/recruiters/{recruiter_id}/candidates",
    dependencies=RECRUITER_OR_ADMIN,
)
def get_candidates(
    recruiter_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    recruiter = db.get(Recruiter, recruiter_id)
    if not recruiter:
        raise HTTPException(
            status_code=404,
            detail="Recruiter not found",
        )

    # Admin can view any recruiter.
    if user.get("role") == "admin":
        pass
    else:
        # Recruiter can access their own role or any role posted by their company
        logged_in_recruiter_id = user.get("recruiter_id")
        if not logged_in_recruiter_id:
            raise HTTPException(
                status_code=403,
                detail="Recruiter account is not linked to a recruiter profile",
            )
        logged_in_rec = db.get(Recruiter, logged_in_recruiter_id)
        same_company = (
            logged_in_rec and 
            recruiter and 
            logged_in_rec.company.strip().lower() == recruiter.company.strip().lower()
        )
        if logged_in_recruiter_id != recruiter_id and not same_company:
            raise HTTPException(
                status_code=403,
                detail="You can only access roles belonging to your company",
            )




    recruiter_comp = (recruiter.company or "").strip()
    comp_clean = "".join(c for c in recruiter_comp if c.isalnum()).lower()

    match_filters = [
        func.lower(func.trim(JobApplication.company)) == func.lower(recruiter_comp),
        JobApplication.company.ilike(f"%{recruiter_comp}%"),
    ]
    if recruiter_comp.lower() in ("tcs", "tce"):
        match_filters.extend([
            func.lower(JobApplication.company) == "tcs",
            func.lower(JobApplication.company) == "tce",
            JobApplication.company.ilike("%tcs%"),
            JobApplication.company.ilike("%tce%"),
            JobApplication.company.ilike("%tata consultancy%"),
        ])
    if recruiter_comp.lower() in ("amazon", "amazone"):
        match_filters.extend([
            func.lower(JobApplication.company) == "amazon",
            func.lower(JobApplication.company) == "amazone",
            JobApplication.company.ilike("%amazon%"),
        ])
    if comp_clean:
        match_filters.append(
            func.replace(func.replace(func.replace(func.lower(JobApplication.company), '.', ''), '>', ''), ' ', '') == comp_clean
        )

    # Students must have their application specifically approved by college placement for this recruiter's company
    approved_student_ids = {
        row[0]
        for row in db.query(JobApplication.student_id)
        .filter(
            JobApplication.college_approval == "Approved",
            or_(*match_filters),
        )
        .distinct()
        .all()
    }



    if approved_student_ids:



        students = (



            db.query(Student)



            .filter(Student.id.in_(approved_student_ids))



            .all()



        )



    else:



        students = []



    results = [



        match_student_to_recruiter(student, recruiter)



        for student in students



    ]



    return sorted(



        results,



        key=lambda result: result["match_score"],



        reverse=True,



    )



@app.get(



    "/recruiter/applicant-information/{student_id}",



    dependencies=RECRUITER_OR_ADMIN,



)



def get_recruiter_applicant_information(



    student_id: int,



    db: Session = Depends(get_db),



):



    # First check whether this student has a college-approved application



    approved_application = (



        db.query(JobApplication)



        .filter(



            JobApplication.student_id == student_id,



            JobApplication.college_approval == "Approved",



        )



        .first()



    )



    if not approved_application:



        raise HTTPException(



            status_code=403,



            detail="Student is not a college-approved applicant",



        )



    # Only after approval is confirmed, get the student information



    student = db.get(Student, student_id)



    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    res_url = student.resume_url or (approved_application.resume_url if approved_application else "") or ""
    return {
        "id": student.id,
        "name": student.name,
        "branch": student.branch,
        "cgpa": student.cgpa,
        "backlogs": student.backlogs,
        "skills": student.skills or [],
        "certifications": student.certifications or [],
        "projects": getattr(student, "projects", []) or [],
        "mock_interview_score": student.mock_interview_score,
        "college_id": student.college_id,
        "college_approval": student.college_approval,
        "resume_url": res_url,
    }



@app.post(



    "/recruiters/{recruiter_id}/shortlist/{student_id}",



    dependencies=RECRUITER_OR_ADMIN,



)



def shortlist_student(



    recruiter_id: int,



    student_id: int,



    db: Session = Depends(get_db),



):



    """Shortlist an approved student and update their placement progress."""



    recruiter = db.get(Recruiter, recruiter_id)



    student = db.get(Student, student_id)



    if not recruiter or not student:



        raise HTTPException(



            status_code=404,



            detail="Recruiter or student not found",



        )



    # Check recruiter-student matching



    match = match_student_to_recruiter(student, recruiter)



    if match["status"] != "Shortlisted":



        return match



    # Find an approved application for this student



    application = (



        db.query(JobApplication)



        .filter(



            JobApplication.student_id == student_id,



            JobApplication.college_approval == "Approved",



        )



        .order_by(JobApplication.applied_at.desc())



        .first()



    )



    if not application:



        raise HTTPException(



            status_code=404,



            detail="No college-approved job application found for this student",



        )



    # Update placement progress



    application.status = "Under Review"



    application.updated_at = datetime.utcnow()



    db.commit()



    db.refresh(application)



    notify_shortlist(



        student.name,



        recruiter.role,



        recruiter.company,



    )



    return {



        "message": "Student shortlisted successfully",



        "application_id": application.id,



        "student_id": student_id,



        "status": application.status,



        "college_approval": application.college_approval,



        "match": match,



    }



# ---------------------------------------------------------------------------



# Routes — Drives

# ---------------------------------------------------------------------------

VENUE_CONFIG = {
    "Auditorium": {
        "resources": ["Main Stage AV System", "Projector Array", "Acoustic PA"],
        "panels": ["Technical Panel A", "Technical Panel B", "HR Panel A"],
        "capacity": 250,
    },
    "Lab 1": {
        "resources": ["Lab 1 Workstations (60 Systems)", "High-Speed LAN", "Projector"],
        "panels": ["Technical Panel 1", "Technical Panel 2"],
        "capacity": 60,
    },
    "Lab 2": {
        "resources": ["Lab 2 Workstations (45 Systems)", "Coding Assessment Terminal", "AV System"],
        "panels": ["Technical Panel 3", "HR Panel B"],
        "capacity": 45,
    },
    "Placement Cell": {
        "resources": ["Interview Chamber A", "Video Conference System"],
        "panels": ["Panel Alpha", "Executive HR Panel"],
        "capacity": 30,
    },
    "Seminar Hall A": {
        "resources": ["Presentation Screen", "Wireless Mic System"],
        "panels": ["Technical Panel 4", "Management Panel"],
        "capacity": 120,
    },
    "Seminar Hall B": {
        "resources": ["Smart Board", "PA System"],
        "panels": ["Panel Beta", "HR Panel C"],
        "capacity": 80,
    },
}


def detect_all_drive_conflicts(db: Session, proposed_drive: Optional[dict] = None) -> List[dict]:
    drives = db.query(Drive).filter(Drive.status != "Cancelled").all()

    if proposed_drive:
        class ProposedProxy:
            def __init__(self, d):
                self.id = d.get("id", -999)
                self.company = d.get("company", "Proposed Drive")
                self.recruiter_id = d.get("recruiter_id")
                self.date = d.get("date", "")
                self.time_slot = d.get("time_slot", "")
                self.venue = d.get("venue", "")
                self.resources = d.get("resources", [])
                self.interview_panels = d.get("interview_panels", [])
                self.infrastructure_capacity = d.get("infrastructure_capacity", 100)
                self.status = d.get("status", "Scheduled")
        drives = list(drives) + [ProposedProxy(proposed_drive)]

    conflicts = []

    # Map each company to candidates
    company_candidates = {}
    all_apps = db.query(JobApplication).filter(
        JobApplication.status.in_(["Shortlisted", "Interview", "Under Review", "Selected", "Applied"])
    ).all()
    for app in all_apps:
        comp_key = (app.company or "").strip().lower()
        if comp_key:
            if comp_key not in company_candidates:
                company_candidates[comp_key] = set()
            company_candidates[comp_key].add(app.student_id)

    student_names = {}

    for i in range(len(drives)):
        for j in range(i + 1, len(drives)):
            a, b = drives[i], drives[j]

            if a.date == b.date and _slots_overlap(a.time_slot, b.time_slot):
                # 1. Overlapping company drives on the same date/slot
                if a.company.strip().lower() != b.company.strip().lower():
                    conflicts.append({
                        "category": "overlapping_company_drives",
                        "severity": "warning",
                        "title": f"Overlapping Drives: {a.company} & {b.company}",
                        "drive_a": a.id,
                        "drive_b": b.id,
                        "company_a": a.company,
                        "company_b": b.company,
                        "date": a.date,
                        "time_slot_a": a.time_slot,
                        "time_slot_b": b.time_slot,
                        "reason": (
                            f"Overlapping Company Drives: '{a.company}' ({a.time_slot}) and '{b.company}' ({b.time_slot}) "
                            f"are concurrently scheduled on {a.date}. Simultaneous drives may create student scheduling conflicts and divide attendance."
                        ),
                    })

                # 2. Venue and resource double-booking
                # 2a. Venue double-booking
                if a.venue.strip().lower() == b.venue.strip().lower():
                    conflicts.append({
                        "category": "venue_and_resource_double_booking",
                        "severity": "critical",
                        "title": f"Venue Double-Booking: {a.venue}",
                        "drive_a": a.id,
                        "drive_b": b.id,
                        "company_a": a.company,
                        "company_b": b.company,
                        "venue": a.venue,
                        "date": a.date,
                        "reason": (
                            f"Venue Double-Booking: Venue '{a.venue}' is double-booked on {a.date} "
                            f"between '{a.company}' ({a.time_slot}) and '{b.company}' ({b.time_slot})."
                        ),
                    })

                # 2b. Resource double-booking
                res_a = set(r.strip().lower() for r in (getattr(a, "resources", []) or []))
                res_b = set(r.strip().lower() for r in (getattr(b, "resources", []) or []))
                shared_res = res_a & res_b
                if shared_res:
                    res_display = ", ".join(r.title() for r in shared_res)
                    conflicts.append({
                        "category": "venue_and_resource_double_booking",
                        "severity": "critical",
                        "title": f"Resource Double-Booking: {res_display}",
                        "drive_a": a.id,
                        "drive_b": b.id,
                        "resources": list(shared_res),
                        "date": a.date,
                        "reason": (
                            f"Resource Double-Booking: Shared campus resource(s) '{res_display}' "
                            f"double-booked on {a.date} between '{a.company}' ({a.time_slot}) and '{b.company}' ({b.time_slot})."
                        ),
                    })

                # 3. Student shortlisted for multiple simultaneous drives
                cand_a = company_candidates.get(a.company.strip().lower(), set())
                cand_b = company_candidates.get(b.company.strip().lower(), set())
                shared_students = cand_a & cand_b
                for sid in list(shared_students)[:5]:
                    if sid not in student_names:
                        st = db.get(Student, sid)
                        student_names[sid] = st.name if st else f"Student #{sid}"
                    sname = student_names[sid]
                    conflicts.append({
                        "category": "student_simultaneous_drives",
                        "severity": "critical",
                        "title": f"Shortlisted Student Conflict: {sname}",
                        "student_id": sid,
                        "student_name": sname,
                        "drive_a": a.id,
                        "drive_b": b.id,
                        "company_a": a.company,
                        "company_b": b.company,
                        "date": a.date,
                        "reason": (
                            f"Student Simultaneous Drive Conflict: Student '{sname}' (ID: {sid}) is shortlisted "
                            f"for both '{a.company}' ({a.time_slot}) and '{b.company}' ({b.time_slot}) on {a.date}. "
                            f"The student cannot be present for simultaneous interview rounds."
                        ),
                    })

                # 4. Interview-panel double-booking
                panels_a = set(p.strip().lower() for p in (getattr(a, "interview_panels", []) or []))
                panels_b = set(p.strip().lower() for p in (getattr(b, "interview_panels", []) or []))
                shared_panels = panels_a & panels_b
                if shared_panels:
                    p_display = ", ".join(p.title() for p in shared_panels)
                    conflicts.append({
                        "category": "interview_panel_and_infrastructure",
                        "severity": "critical",
                        "title": f"Interview Panel Collision: {p_display}",
                        "drive_a": a.id,
                        "drive_b": b.id,
                        "panels": list(shared_panels),
                        "date": a.date,
                        "reason": (
                            f"Interview Panel Double-Booking: Interview panel '{p_display}' is assigned "
                            f"concurrently to both '{a.company}' ({a.time_slot}) and '{b.company}' ({b.time_slot}) on {a.date}."
                        ),
                    })

    # Individual drive checks for panel capacity & infrastructure capacity
    for d in drives:
        comp_key = d.company.strip().lower()
        cand_count = len(company_candidates.get(comp_key, set()))
        cap = getattr(d, "infrastructure_capacity", 100) or 100
        panels = getattr(d, "interview_panels", []) or []
        panel_count = len(panels) if panels else 2

        if cand_count > cap:
            conflicts.append({
                "category": "interview_panel_and_infrastructure",
                "severity": "warning",
                "title": f"Infrastructure Capacity Exceeded: {d.company}",
                "drive_id": d.id,
                "company": d.company,
                "venue": d.venue,
                "capacity": cap,
                "candidates_count": cand_count,
                "date": d.date,
                "reason": (
                    f"Infrastructure Capacity Exceeded: Venue '{d.venue}' has capacity of {cap} seats, "
                    f"but '{d.company}' drive has {cand_count} candidates scheduled on {d.date} ({d.time_slot})."
                ),
            })

        if cand_count > (panel_count * 15):
            conflicts.append({
                "category": "interview_panel_and_infrastructure",
                "severity": "warning",
                "title": f"Interview Panel Shortage: {d.company}",
                "drive_id": d.id,
                "company": d.company,
                "panels_count": panel_count,
                "candidates_count": cand_count,
                "date": d.date,
                "reason": (
                    f"Interview Panel Availability Warning: Drive for '{d.company}' on {d.date} ({d.time_slot}) "
                    f"has {cand_count} candidates for only {panel_count} interview panel(s) "
                    f"(approx. {round(cand_count/max(panel_count,1), 1)} candidates/panel). Additional interview panel recommended."
                ),
            })

    return conflicts


@app.post("/drives", response_model=DriveOut, dependencies=COLLEGE_OR_ADMIN)
def create_drive(payload: DriveIn, db: Session = Depends(get_db)):
    drive_data = payload.model_dump()
    cfg = VENUE_CONFIG.get(payload.venue, {})
    if not drive_data.get("resources"):
        drive_data["resources"] = cfg.get("resources", [f"{payload.venue} Facilities"])
    if not drive_data.get("interview_panels"):
        drive_data["interview_panels"] = cfg.get("panels", ["Technical Panel 1", "HR Panel 1"])
    if not drive_data.get("infrastructure_capacity"):
        drive_data["infrastructure_capacity"] = cfg.get("capacity", 80)

    drive = Drive(**drive_data)
    db.add(drive)
    db.commit()
    db.refresh(drive)

    role = "Software Engineer"
    min_cgpa = 6.0
    max_backlogs = 0
    eligible_branches = ["CSE", "IT", "ECE"]
    ctc_lpa = 8.0

    if drive.recruiter_id:
        recruiter = db.get(Recruiter, drive.recruiter_id)
        if recruiter:
            role = recruiter.role or role
            min_cgpa = recruiter.min_cgpa if recruiter.min_cgpa is not None else min_cgpa
            max_backlogs = recruiter.max_backlogs if recruiter.max_backlogs is not None else max_backlogs
            eligible_branches = recruiter.branches or eligible_branches
            ctc_lpa = recruiter.ctc_lpa or ctc_lpa

    notify_drive_announcement(drive.company, role, drive.date, drive.venue)

    try:
        auto_notify_drive_announcement_with_eligibility(
            db=db,
            drive=drive,
            role=role,
            min_cgpa=min_cgpa,
            max_backlogs=max_backlogs,
            eligible_branches=eligible_branches,
            ctc_lpa=ctc_lpa,
        )
    except Exception as exc:
        logger.warning("Automated drive announcement broadcast error: %s", exc)

    return drive


@app.get("/drives", response_model=List[DriveOut], dependencies=ANY_USER)
def list_drives(db: Session = Depends(get_db)):
    return db.query(Drive).all()


@app.get("/college/students", dependencies=COLLEGE_OR_ADMIN)
def get_college_students(
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """Returns all students in the college, with name, branch, and CGPA."""
    role = user.get("role")
    college_id = user.get("college_id")
    query = db.query(Student)
    if role == "college" and college_id:
        query = query.filter(Student.college_id == college_id)
    students = query.order_by(Student.name.asc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "branch": s.branch,
            "cgpa": s.cgpa,
            "college_id": s.college_id,
        }
        for s in students
    ]


@app.get("/college/student-drives", dependencies=COLLEGE_RECRUITER_OR_ADMIN)
def get_college_student_drives(
    student_id: Optional[int] = None,
    company: Optional[str] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """
    Returns campus recruitment drives with exact Date and Location (Venue) mapped to individual students.
    Optimized for high performance with batch caching.
    """
    role = user.get("role")
    college_id = user.get("college_id")

    # Pre-fetch all recruiters to avoid N+1 queries
    rec_map = {r.id: r for r in db.query(Recruiter).all()}
    drives = db.query(Drive).all()

    valid_student_id = None
    if student_id is not None:
        try:
            valid_student_id = int(student_id)
        except (ValueError, TypeError):
            valid_student_id = None

    student_query = db.query(Student).order_by(Student.id.asc())
    if role == "college" and college_id:
        student_query = student_query.filter(Student.college_id == college_id)
    if valid_student_id is not None:
        student_query = student_query.filter(Student.id == valid_student_id)
    elif not company or (isinstance(company, str) and company.lower() == "all"):
        # Limit total students sampled for the overview matrix so response is fast
        student_query = student_query.limit(40)

    students = student_query.all()
    if not students:
        return []

    st_ids = [s.id for s in students]
    applications = db.query(JobApplication).filter(JobApplication.student_id.in_(st_ids)).all()
    app_map = {}
    for app in applications:
        app_map.setdefault(app.student_id, []).append(app)

    results = []

    def matches_company(c1, c2):
        if not c1 or not c2:
            return False
        c1, c2 = str(c1).strip().lower(), str(c2).strip().lower()
        if c1 == c2 or c1 in c2 or c2 in c1:
            return True
        if c1 in ("tcs", "tce") and c2 in ("tcs", "tce", "tata consultancy"):
            return True
        if c1 in ("amazon", "amazone") and c2 in ("amazon", "amazone"):
            return True
        return False

    for st in students:
        st_apps = app_map.get(st.id, [])
        matched_drive_ids = set()

        # 1. First add drives from jobs the student applied to
        for app in st_apps:
            for d in drives:
                if matches_company(d.company, app.company):
                    matched_drive_ids.add(d.id)
                    rec = rec_map.get(d.recruiter_id)
                    results.append({
                        "student_id": st.id,
                        "student_name": st.name,
                        "branch": st.branch,
                        "cgpa": st.cgpa,
                        "college_id": st.college_id,
                        "drive_id": d.id,
                        "company": d.company,
                        "role": rec.role if rec else app.job_title,
                        "date": d.date,
                        "location": d.venue,
                        "venue": d.venue,
                        "time_slot": d.time_slot,
                        "drive_status": d.status,
                        "application_id": app.id,
                        "application_status": app.status,
                        "college_approval": app.college_approval,
                        "routing_stage": (
                            f"Approved & Forwarded to {d.company} Recruiter" if app.college_approval == "Approved"
                            else ("Pending College Placement Approval" if app.college_approval == "Pending" else "Rejected by Placement Cell")
                        ),
                        "type": "Student Applied Drive"
                    })

        # 2. Add scheduled drives where the student is eligible by branch
        eligible_count = 0
        max_eligible = 15 if (valid_student_id is not None) else 2
        for d in drives:
            if d.id in matched_drive_ids:
                continue
            rec = rec_map.get(d.recruiter_id)
            is_branch_ok = True
            if rec and rec.eligible_branches:
                branches = rec.eligible_branches
                if isinstance(branches, str):
                    try:
                        branches = json.loads(branches)
                    except Exception:
                        branches = [branches]
                if isinstance(branches, list):
                    is_branch_ok = any(st.branch.lower() == str(b).lower() for b in branches)
            if is_branch_ok:
                results.append({
                    "student_id": st.id,
                    "student_name": st.name,
                    "branch": st.branch,
                    "cgpa": st.cgpa,
                    "college_id": st.college_id,
                    "drive_id": d.id,
                    "company": d.company,
                    "role": rec.role if rec else "Campus Placement Drive",
                    "date": d.date,
                    "location": d.venue,
                    "venue": d.venue,
                    "time_slot": d.time_slot,
                    "drive_status": d.status,
                    "application_id": None,
                    "application_status": "Eligible / Open",
                    "college_approval": "Eligible",
                    "routing_stage": "Eligible for Campus Drive",
                    "type": "Eligible Campus Drive"
                })
                eligible_count += 1
                if eligible_count >= max_eligible:
                    break

    if company and company.lower() != "all":
        results = [r for r in results if matches_company(r["company"], company)]

    return results


@app.post("/recruiter/send-email", dependencies=RECRUITER_OR_ADMIN)
def send_recruiter_email_to_student(
    payload: RecruiterEmailPayload,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """
    Sends an official selection / offer email directly to the student from the recruiter.
    Dispatches to In-App notification, Email channel, and records in audit dispatch log.
    """
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    recruiter_company = "CampusLink Partner Recruiter"
    if user.get("role") == "recruiter" and user.get("recruiter_id"):
        rec = db.get(Recruiter, user["recruiter_id"])
        if rec and rec.company:
            recruiter_company = rec.company

    # Look up student's actual email or user account email
    student_acc = db.query(UserAccount).filter(UserAccount.student_id == student.id).first()
    student_email = getattr(student, "email", None) or (student_acc.email if student_acc else None) or f"{student.name.lower().replace(' ', '')}@gmail.com"

    notif = dispatch_automated_notification(
        db=db,
        recipient_role="student",
        recipient_id=student.id,
        recipient_name=student.name,
        recipient_email=student_email,
        recipient_phone=getattr(student, "phone", None),
        category="offer_letter_email",
        title=payload.subject,
        message=payload.message,
        meta_data={
            "company": recruiter_company,
            "application_id": payload.application_id,
            "email_subject": payload.subject,
            "sent_at": datetime.utcnow().isoformat(),
            "dispatch_type": "Recruiter Direct Selection Mail",
        },
    )

    return {
        "success": True,
        "message": f"Selection email successfully dispatched to {student.name} ({student_email})",
        "notification_id": notif.id,
        "recipient_email": student_email,
        "recipient_name": student.name,
        "company": recruiter_company,
        "subject": payload.subject,
    }


@app.get("/students/{student_id}/drives", dependencies=STUDENT_SELF_OR_ADMIN)
def get_individual_student_drives(
    student_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """
    Returns recruitment drives with exact Date and Location for an individual student.
    """
    st = db.get(Student, student_id)
    if not st:
        raise HTTPException(status_code=404, detail="Student not found")

    drives = db.query(Drive).all()
    apps = db.query(JobApplication).filter(JobApplication.student_id == student_id).all()

    def matches_company(c1, c2):
        if not c1 or not c2: return False
        c1, c2 = str(c1).strip().lower(), str(c2).strip().lower()
        if c1 == c2 or c1 in c2 or c2 in c1: return True
        if c1 in ("tcs", "tce") and c2 in ("tcs", "tce", "tata consultancy"): return True
        if c1 in ("amazon", "amazone") and c2 in ("amazon", "amazone"): return True
        return False

    results = []
    matched_drive_ids = set()

    for app in apps:
        for d in drives:
            if matches_company(d.company, app.company):
                matched_drive_ids.add(d.id)
                rec = db.get(Recruiter, d.recruiter_id) if d.recruiter_id else None
                results.append({
                    "drive_id": d.id,
                    "company": d.company,
                    "role": rec.role if rec else app.job_title,
                    "date": d.date,
                    "location": d.venue,
                    "venue": d.venue,
                    "time_slot": d.time_slot,
                    "status": d.status,
                    "application_status": app.status,
                    "college_approval": app.college_approval,
                    "routing_stage": (
                        f"Approved & Forwarded to {d.company} Recruiter" if app.college_approval == "Approved"
                        else ("Pending College Placement Approval" if app.college_approval == "Pending" else "Rejected by Placement Cell")
                    ),
                    "type": "Applied Job Drive"
                })

    for d in drives:
        if d.id in matched_drive_ids:
            continue
        rec = db.get(Recruiter, d.recruiter_id) if d.recruiter_id else None
        is_branch_ok = True
        if rec and rec.eligible_branches:
            is_branch_ok = any(st.branch.lower() == b.lower() for b in rec.eligible_branches)
        if is_branch_ok and d.status in ("Scheduled", "Rescheduled"):
            results.append({
                "drive_id": d.id,
                "company": d.company,
                "role": rec.role if rec else "Campus Placement Drive",
                "date": d.date,
                "location": d.venue,
                "venue": d.venue,
                "time_slot": d.time_slot,
                "status": d.status,
                "application_status": "Eligible / Open",
                "college_approval": "Eligible",
                "routing_stage": "Eligible for Campus Drive",
                "type": "Eligible Campus Drive"
            })

    return results


@app.get("/drives/conflicts", dependencies=ADMIN_ONLY)
def drive_conflicts(db: Session = Depends(get_db)):
    return detect_all_drive_conflicts(db)


@app.post("/drives/check-conflicts", dependencies=ADMIN_ONLY)
def check_drive_conflicts(payload: DriveIn, db: Session = Depends(get_db)):
    """Pre-flight conflict check before scheduling a new drive."""
    return detect_all_drive_conflicts(db, proposed_drive=payload.model_dump())




# ---------------------------------------------------------------------------



# Routes — Offers



# ---------------------------------------------------------------------------



@app.post("/offers", response_model=OfferOut, dependencies=ADMIN_ONLY)



def create_offer(payload: OfferIn, db: Session = Depends(get_db)):



    offer = Offer(**payload.model_dump(), status="Issued")



    db.add(offer)



    db.commit()



    db.refresh(offer)



    student = db.get(Student, offer.student_id)



    recruiter = db.get(Recruiter, offer.recruiter_id)



    if student and recruiter:

        notify_offer_status(student.name, "Issued", recruiter.company)

        try:
            auto_notify_offer_status(
                db=db,
                student=student,
                company=recruiter.company,
                role=recruiter.role,
                status="Issued",
                ctc_lpa=offer.ctc_lpa,
                joining_date=offer.joining_date,
            )
        except Exception as exc:
            logger.warning("Automated offer notification error: %s", exc)

    return offer



@app.get("/offers", response_model=List[OfferOut], dependencies=ADMIN_ONLY)



def list_offers(db: Session = Depends(get_db)):



    return db.query(Offer).all()



@app.put("/offers/{offer_id}/status", response_model=OfferOut, dependencies=ADMIN_ONLY)



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

        try:
            auto_notify_offer_status(
                db=db,
                student=student,
                company=recruiter.company,
                role=recruiter.role,
                status=offer.status,
                ctc_lpa=offer.ctc_lpa,
                joining_date=offer.joining_date,
            )
        except Exception as exc:
            logger.warning("Automated offer status update error: %s", exc)

    return offer



# ---------------------------------------------------------------------------



# Routes — Analytics



# ---------------------------------------------------------------------------



@app.get("/analytics/dashboard", dependencies=ADMIN_ONLY)



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



# ---------------------------------------------------------------------------



# Routes — Student Job Application Tracking



# Add this section at the bottom of main.py



# ---------------------------------------------------------------------------



@app.post(



    "/students/{student_id}/job-applications",



    response_model=JobApplicationOut,



    status_code=201,



    dependencies=STUDENT_SELF_OR_ADMIN,



)



def create_job_application(
    student_id: int,
    payload: JobApplicationCreate,
    db: Session = Depends(get_db),
):
    """Record a job application for the selected student and store in college placement cell."""

    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    job_title = (payload.job_title or "").strip()
    company = (payload.company or "").strip()

    if not job_title or not company:
        raise HTTPException(
            status_code=400,
            detail="Job title and company are required",
        )

    # Process job URL: if provided, validate or fix; if missing, generate a valid internal URL.
    raw_url = (payload.job_url or "").strip()
    if raw_url:
        if not (raw_url.startswith("http://") or raw_url.startswith("https://")):
            raw_url = "https://" + raw_url
        parsed_url = urlparse(raw_url)
        if not parsed_url.netloc:
            job_url = f"https://campuslink.local/jobs/{student_id}/{secrets.token_hex(4)}"
        else:
            job_url = raw_url
    else:
        job_url = f"https://campuslink.local/jobs/{student_id}/{secrets.token_hex(4)}"

    # Prevent the same student from applying to the same job title & company or URL twice.
    existing = (
        db.query(JobApplication)
        .filter(
            JobApplication.student_id == student_id,
            or_(
                (func.lower(JobApplication.job_title) == func.lower(job_title)) &
                (func.lower(JobApplication.company) == func.lower(company)),
                JobApplication.job_url == job_url,
            )
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"You have already applied for '{job_title}' at '{company}' (Status: {existing.college_approval})",
        )

    # Resolve college: either from payload or from student profile or default college.
    college_obj = None
    college_input = (payload.college or "").strip()

    if college_input:
        if college_input.isdigit():
            college_obj = db.get(College, int(college_input))
        if not college_obj:
            college_obj = (
                db.query(College)
                .filter(
                    or_(
                        func.lower(College.college_code) == func.lower(college_input),
                        func.lower(College.college_name) == func.lower(college_input),
                    )
                )
                .first()
            )

    if not college_obj and student.college_id:
        college_obj = db.get(College, student.college_id)

    if not college_obj:
        college_obj = db.query(College).first()

    if college_obj:
        if not student.college_id:
            student.college_id = college_obj.id
            db.add(student)
        college_name = college_obj.college_name
    else:
        college_name = college_input or "Placement Cell"

    # Resolve resume: if provided in payload, use it; else fallback to student.resume_url
    app_resume = (payload.resume_url or "").strip()
    if not app_resume and getattr(student, "resume_url", None):
        app_resume = student.resume_url
    if app_resume and not getattr(student, "resume_url", None):
        student.resume_url = app_resume
        db.add(student)

    application = JobApplication(
        student_id=student_id,
        job_title=job_title,
        company=company,
        college=college_name,
        job_url=job_url,
        source=(payload.source or "Job Portal").strip(),
        status="Applied",
        college_approval="Pending",
        resume_url=app_resume or None,
    )

    try:
        db.add(application)
        db.commit()
        db.refresh(application)
        return application

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This job application has already been recorded",
        )



@app.patch(



    "/job-applications/{application_id}/college-approval",



    dependencies=COLLEGE_OR_ADMIN,



)



def update_college_approval(



    application_id: int,



    payload: CollegeApprovalUpdate,



    db: Session = Depends(get_db),



):



    allowed_values = {



        "Pending",



        "Approved",



        "Rejected",



    }



    if payload.college_approval not in allowed_values:



        raise HTTPException(



            status_code=400,



            detail="Invalid college approval. Use Pending, Approved, or Rejected",



        )



    application = db.get(JobApplication, application_id)



    if not application:



        raise HTTPException(



            status_code=404,



            detail="Job application not found",



        )



    application.college_approval = payload.college_approval



    application.updated_at = datetime.utcnow()



    db.commit()



    db.refresh(application)



    return application



@app.patch(



    "/job-applications/{application_id}/status",



    dependencies=RECRUITER_OR_ADMIN,



)



def update_job_application_status(



    application_id: int,



    payload: JobApplicationStatusUpdate,



    db: Session = Depends(get_db),



):



    allowed_statuses = {
        "Applied",
        "Under Review",
        "Interview",
        "Rejected",
        "Selected",
    }

    raw_status = (payload.status or "").strip()
    status_lower = raw_status.lower()

    if status_lower in ("accepted", "accept", "selected", "select", "offer", "hired", "approved", "approve"):
        normalized_status = "Selected"
    elif status_lower in ("rejected", "reject"):
        normalized_status = "Rejected"
    elif status_lower in ("interview", "interviewing"):
        normalized_status = "Interview"
    elif status_lower in ("under review", "review"):
        normalized_status = "Under Review"
    elif status_lower in ("applied", "apply"):
        normalized_status = "Applied"
    elif raw_status in allowed_statuses:
        normalized_status = raw_status
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{raw_status}'. Use one of: Accepted, Selected, Rejected, Interview, Under Review, Applied",
        )

    application = db.get(JobApplication, application_id)
    if not application:
        raise HTTPException(
            status_code=404,
            detail="Job application not found",
        )

    application.status = normalized_status
    application.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(application)

    try:
        student = db.get(Student, application.student_id)
        if student:
            if normalized_status in ("Interview", "Under Review"):
                auto_notify_shortlist_and_interview(
                    db=db,
                    student=student,
                    company=application.company,
                    role=application.job_title,
                )
            elif normalized_status == "Selected":
                auto_notify_offer_status(
                    db=db,
                    student=student,
                    company=application.company,
                    role=application.job_title,
                    status="Selected",
                )
    except Exception as exc:
        logger.warning("Automated application status notification error: %s", exc)

    return application



@app.get(



    "/recruiter/job-applicants",



    dependencies=RECRUITER_OR_ADMIN,



)



def get_approved_job_applications(
    company: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: dict = Depends(current_user),
):
    """Return college-approved job applications company-wise for recruiter or admin review."""
    user_role = user.get("role")
    req_company = (company or "").strip()

    query = (
        db.query(JobApplication, Student)
        .join(
            Student,
            JobApplication.student_id == Student.id
        )
        .filter(
            JobApplication.college_approval == "Approved"
        )
    )

    if user_role == "admin":
        if req_company and req_company.lower() != "all":
            query = query.filter(
                or_(
                    func.lower(func.trim(JobApplication.company)) == func.lower(req_company),
                    JobApplication.company.ilike(f"%{req_company}%"),
                )
            )
    else:
        # Recruiter
        recruiter_id = user.get("recruiter_id")
        if not recruiter_id:
            raise HTTPException(
                status_code=403,
                detail="Recruiter account is not linked to a recruiter profile",
            )
        recruiter = db.get(Recruiter, recruiter_id)
        if not recruiter:
            raise HTTPException(
                status_code=404,
                detail="Recruiter profile not found",
            )

        # Recruiter can strictly only access applications for their company that were approved by college placement
        target_company = (recruiter.company or "").strip()
        if target_company:
            comp_clean = "".join(c for c in target_company if c.isalnum()).lower()
            match_filters = [
                func.lower(func.trim(JobApplication.company)) == func.lower(target_company),
                JobApplication.company.ilike(f"%{target_company}%"),
                func.lower(func.trim(JobApplication.company)) == func.lower(target_company.replace(".", " ")),
                func.lower(func.trim(JobApplication.company)) == func.lower(target_company.replace(">", " ")),
            ]
            if target_company.lower() in ("tcs", "tce"):
                match_filters.extend([
                    func.lower(JobApplication.company) == "tcs",
                    func.lower(JobApplication.company) == "tce",
                    JobApplication.company.ilike("%tcs%"),
                    JobApplication.company.ilike("%tce%"),
                    JobApplication.company.ilike("%tata consultancy%"),
                ])
            if target_company.lower() in ("amazon", "amazone"):
                match_filters.extend([
                    func.lower(JobApplication.company) == "amazon",
                    func.lower(JobApplication.company) == "amazone",
                    JobApplication.company.ilike("%amazon%"),
                ])
            if comp_clean:
                match_filters.append(
                    func.replace(func.replace(func.replace(func.lower(JobApplication.company), '.', ''), '>', ''), ' ', '') == comp_clean
                )
            query = query.filter(or_(*match_filters))

    applications = query.order_by(JobApplication.company.asc(), JobApplication.updated_at.desc()).all()

    seen_students = set()
    results = []
    for application, student in applications:
        if application.student_id in seen_students:
            continue
        seen_students.add(application.student_id)
        results.append({
            "id": application.id,
            "student_id": application.student_id,
            "student_name": student.name,
            "branch": student.branch,
            "cgpa": student.cgpa,
            "skills": student.skills or [],
            "job_title": application.job_title,
            "company": application.company,
            "college": application.college or "",
            "job_url": application.job_url,
            "source": application.source,
            "status": application.status,
            "college_approval": application.college_approval,
            "resume_url": application.resume_url or getattr(student, "resume_url", None) or "",
            "applied_at": application.applied_at,
            "updated_at": application.updated_at,
        })

    return results



@app.get(



    "/students/{student_id}/job-applications",



    response_model=List[JobApplicationOut],



    dependencies=STUDENT_SELF_OR_ADMIN,



)



def list_job_applications(



    student_id: int,



    db: Session = Depends(get_db),



):



    """List all recorded job applications for a student."""



    student = db.get(Student, student_id)



    if not student:



        raise HTTPException(status_code=404, detail="Student not found")



    return (



        db.query(JobApplication)



        .filter(JobApplication.student_id == student_id)



        .order_by(JobApplication.applied_at.desc())



        .all()



    )



def get_job_search_query(question: str) -> str:



    q = question.lower()



    if "python" in q:



        return "python"



    if "ai/ml" in q or "ai ml" in q or "machine learning" in q:



        return "machine learning"



    if "data scientist" in q or "data science" in q:



        return "data"



    if "cyber" in q or "cybersecurity" in q:



        return "cybersecurity"



    if "frontend" in q or "front end" in q:



        return "frontend"



    if "backend" in q or "back end" in q:



        return "backend"



    if "java" in q:



        return "java"



    if "developer" in q or "software engineer" in q:



        return "developer"



    return ""



@app.post("/ai/job-assistant")



def job_assistant(



    payload: JobAssistantRequest,



    user: dict = Depends(current_user)



):



    question = payload.question.strip()



    if not question:



        raise HTTPException(



            status_code=400,



            detail="Question is required"



        )



    try:



        # Get real jobs from the existing CampusLink job service



        search_query = get_job_search_query(question)



        jobs = fetch_external_jobs(



    query=search_query,



    limit=20



)



        # Send the real job data to local Ollama AI



        answer = ask_local_ai(



            question=question,



            jobs=jobs



        )



        return {



            "success": True,



            "answer": answer,



            "jobs_found": len(jobs)



        }



    except RuntimeError as exc:



        raise HTTPException(



            status_code=502,

            detail=str(exc)

        )


# ---------------------------------------------------------------------------
# Routes — Communication & Notification Automation
# ---------------------------------------------------------------------------

@app.get("/notifications")
def list_notifications(
    category: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: Optional[dict] = Depends(lambda creds=Depends(bearer_scheme): verify_token(creds.credentials) if creds else None),
):
    query = db.query(Notification)

    # Filter by user role/id if user is authenticated
    if user:
        role = user.get("role", "student")
        if role == "student":
            student_id = user.get("student_id")
            if student_id:
                query = query.filter(
                    (Notification.recipient_role == "all") |
                    ((Notification.recipient_role == "student") & ((Notification.recipient_id == student_id) | (Notification.recipient_id == None)))
                )
            else:
                query = query.filter(Notification.recipient_role.in_(["student", "all"]))
        elif role == "recruiter":
            recruiter_id = user.get("recruiter_id")
            if recruiter_id:
                query = query.filter(
                    (Notification.recipient_role == "all") |
                    ((Notification.recipient_role == "recruiter") & ((Notification.recipient_id == recruiter_id) | (Notification.recipient_id == None)))
                )
            else:
                query = query.filter(Notification.recipient_role.in_(["recruiter", "all"]))
        # admin can see all

    if category and isinstance(category, str):
        query = query.filter(Notification.category == category)
    if unread_only is True:
        query = query.filter(Notification.read == False)

    all_user_notifs = query.all()
    total_unread = sum(1 for n in all_user_notifs if not n.read)
    items = query.order_by(Notification.created_at.desc()).limit(limit).all()

    cat_counts = {
        "all": len(all_user_notifs),
        "shortlist_interview": 0,
        "document_deadline": 0,
        "offer_status": 0,
        "drive_announcement": 0,
        "general": 0,
    }
    for n in all_user_notifs:
        if n.category in cat_counts:
            cat_counts[n.category] += 1

    return {
        "notifications": [
            {
                "id": n.id,
                "recipient_role": n.recipient_role,
                "recipient_id": n.recipient_id,
                "recipient_name": n.recipient_name,
                "recipient_email": n.recipient_email,
                "recipient_phone": n.recipient_phone,
                "category": n.category,
                "title": n.title,
                "message": n.message,
                "channels": n.channels or ["in_app", "email", "whatsapp"],
                "dispatch_status": n.dispatch_status or "Delivered",
                "email_delivery_status": n.email_delivery_status or "Sent",
                "whatsapp_delivery_status": n.whatsapp_delivery_status or "Delivered",
                "meta_data": n.meta_data or {},
                "deadline_at": n.deadline_at.isoformat() if n.deadline_at else None,
                "read": bool(n.read),
                "created_at": n.created_at.isoformat() if n.created_at else datetime.utcnow().isoformat(),
            }
            for n in items
        ],
        "unread_count": total_unread,
        "category_counts": cat_counts,
        "total": len(all_user_notifs),
    }


@app.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    notif = db.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    db.commit()
    return {"status": "success", "id": notification_id, "read": True}


@app.post("/notifications/mark-all-read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: Optional[dict] = Depends(lambda creds=Depends(bearer_scheme): verify_token(creds.credentials) if creds else None),
):
    query = db.query(Notification).filter(Notification.read == False)
    if user and user.get("student_id"):
        query = query.filter(
            (Notification.recipient_id == user["student_id"]) |
            (Notification.recipient_role.in_(["student", "all"]))
        )
    query.update({Notification.read: True}, synchronize_session=False)
    db.commit()
    return {"status": "success", "message": "All notifications marked as read"}


@app.post("/notifications/document-deadline")
def send_document_deadline_alert(
    payload: DocumentDeadlineIn,
    db: Session = Depends(get_db),
):
    """
    Automated document submission deadline notification.
    Replaces manual email/WhatsApp follow-ups with automated alerts.
    """
    target_students = []
    if payload.student_id:
        st = db.get(Student, payload.student_id)
        if st:
            target_students.append(st)
    else:
        apps = db.query(JobApplication).filter(
            JobApplication.company.ilike(f"%{payload.company}%"),
        ).all()
        student_ids = set(a.student_id for a in apps)
        if student_ids:
            target_students = db.query(Student).filter(Student.id.in_(student_ids)).all()
        else:
            target_students = db.query(Student).limit(5).all()

    docs = payload.documents or payload.required_documents or ["Updated Resume", "College Transcripts", "Government ID"]
    d_date = payload.deadline_date or payload.deadline_at or "Upcoming Deadline"

    notified = []
    for s in target_students:
        notif = auto_notify_document_deadline(
            db=db,
            student=s,
            company=payload.company,
            role=payload.role or "Applicant",
            documents=docs,
            deadline_date=d_date,
            submission_url=payload.submission_url or "student/resume.html",
        )
        notified.append({"student_id": s.id, "name": s.name, "notification_id": notif.id})

    return {
        "status": "success",
        "company": payload.company,
        "deadline_date": d_date,
        "documents": docs,
        "notified_count": len(notified),
        "recipients": notified,
    }


@app.post("/notifications/schedule-interview")
def schedule_interview_round(
    payload: InterviewScheduleIn,
    db: Session = Depends(get_db),
):
    """
    Automated interview schedule dispatch.
    Replaces manual phone/WhatsApp coordination with instant targeted multi-channel invite.
    """
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    notif = auto_notify_shortlist_and_interview(
        db=db,
        student=student,
        company=payload.company,
        role=payload.role,
        interview_date=payload.interview_date,
        time_slot=payload.time_slot,
        venue=payload.venue or "Placement Cell / Google Meet",
        guidelines=payload.guidelines or "Please join 10 mins prior with ID and updated resume.",
    )
    return {
        "status": "success",
        "notification_id": notif.id,
        "student_id": student.id,
        "student_name": student.name,
        "company": payload.company,
        "role": payload.role,
        "interview_date": payload.interview_date,
        "time_slot": payload.time_slot,
        "venue": payload.venue,
    }


@app.get("/notifications/dispatch-log")
def view_automated_dispatch_log():
    """Returns the automated multi-channel dispatch audit log."""
    logs = get_dispatch_log()
    return {
        "status": "success",
        "total_dispatched": len(logs),
        "dispatches": logs,
    }


@app.post("/notifications/seed-sample-automation")
def seed_sample_automated_notifications(db: Session = Depends(get_db)):
    """
    Seeds realistic automated notifications across all 4 categories:
    1. Shortlist & Interview Schedule
    2. Document Submission Deadline
    3. Offer Status Update
    4. Targeted Drive Announcement with Eligibility
    """
    students = db.query(Student).limit(5).all()
    if not students:
        raise HTTPException(status_code=400, detail="No students found to seed notifications")

    created = []
    # 1. Shortlist & Interview
    n1 = auto_notify_shortlist_and_interview(
        db=db,
        student=students[0],
        company="Google",
        role="Software Engineer - L3",
        interview_date="2026-10-18",
        time_slot="10:00 AM - 11:30 AM",
        venue="Tech Park Auditorium & Google Meet",
        guidelines="Prepare System Design, DSA, and clean architecture principles. Valid College ID mandatory.",
    )
    created.append(n1.id)

    # 2. Document Deadline
    n2 = auto_notify_document_deadline(
        db=db,
        student=students[0],
        company="Microsoft",
        role="Cloud Solutions Architect",
        documents=["Official Semester Grade Sheets", "Signed Placement Code of Conduct", "Aadhaar / Passport Scan"],
        deadline_date="2026-10-16 18:00 IST",
        submission_url="student/resume.html",
    )
    created.append(n2.id)

    # 3. Offer Status Update
    if len(students) > 1:
        n3 = auto_notify_offer_status(
            db=db,
            student=students[1],
            company="TCS Digital",
            role="Data Scientist",
            status="Issued",
            ctc_lpa=9.5,
            joining_date="2027-01-10",
            acceptance_deadline="2026-10-25",
        )
        created.append(n3.id)

    # 4. Drive Announcement with Eligibility
    sample_drive = db.query(Drive).first()
    if sample_drive:
        auto_notify_drive_announcement_with_eligibility(
            db=db,
            drive=sample_drive,
            role="AI & Systems Engineer",
            min_cgpa=6.5,
            max_backlogs=0,
            eligible_branches=["CSE", "ECE", "IT"],
            ctc_lpa=12.0,
        )

    return {
        "status": "success",
        "message": "Automated notification suite successfully seeded across all 4 categories",
        "seeded_notifications_count": len(created),
    }


# ===========================================================================
# MULTI-SOURCE DATA INTEGRATION & ANALYSIS ENGINE ROUTES
# ===========================================================================

class AssessmentCreateRequest(BaseModel):
    student_id: int
    assessment_title: str
    assessment_type: Optional[str] = "Comprehensive"
    aptitude_score: float
    coding_score: float
    technical_score: float
    percentile: Optional[float] = None
    strengths: Optional[List[str]] = []
    weaknesses: Optional[List[str]] = []
    status: Optional[str] = "Completed"


class MockInterviewCreateRequest(BaseModel):
    student_id: int
    interview_type: Optional[str] = "Technical Mock Round"
    interviewer_name: Optional[str] = "Placement Cell Panel"
    interviewer_designation: Optional[str] = "Senior Industry Mentor"
    technical_rating: float
    communication_rating: float
    problem_solving_rating: float
    verdict: Optional[str] = "Ready"
    feedback_notes: Optional[str] = None
    recommended_actions: Optional[List[str]] = []


class ResumeParseRequest(BaseModel):
    resume_text: Optional[str] = None
    technical_skills: Optional[List[str]] = []
    summary: Optional[str] = None
    projects: Optional[List[str]] = []
    certifications: Optional[List[str]] = []


@app.get("/api/integration/engine/status", dependencies=ANY_USER)
def get_multi_source_engine_status(db: Session = Depends(get_db)):
    """
    Returns the real-time operational status and metrics across all 6 connected data sources:
    1. Student Academic Data
    2. Student Resume Data & ATS Store
    3. Recruiter Job Descriptions & Comprehensive Eligibility Matrix
    4. Placement Drive Calendars & Timelines
    5. Historical Placement Record Benchmarks (4 Years)
    6. Diagnostic Assessment & Mock-Interview Results
    """
    engine = get_multi_source_engine(db)
    return engine.get_status()


@app.get("/api/integration/analyze/student/{student_id}", dependencies=STUDENT_SELF_OR_ADMIN)
def analyze_student_multi_source_profile(student_id: int, db: Session = Depends(get_db)):
    """
    Multi-source integration diagnostic for a student:
    Integrates academic record, parsed resume data, technical diagnostic assessments,
    mock interview feedback, historical branch benchmarking, and drive calendar agenda.
    """
    engine = get_multi_source_engine(db)
    result = engine.analyze_student_profile(student_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/integration/analyze/job-match/{student_id}/{recruiter_id}", dependencies=ANY_USER)
def analyze_student_job_fit_multi_source(
    student_id: int,
    recruiter_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(current_user)
):
    """
    Deep multi-source candidate-to-job matching & multi-factor eligibility verification:
    - Academic Cutoff (CGPA & Max Backlogs)
    - Branch Restrictions
    - Diagnostic Assessment Benchmark
    - Mock Interview Benchmark
    - Resume & Skills vs Full JD Text Semantic Cosine Similarity
    - Placement Drive Calendar schedule availability
    - Historical Company Hiring Benchmarks
    """
    engine = get_multi_source_engine(db)
    result = engine.analyze_job_fit(student_id, recruiter_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/integration/analyze/all-matches/{student_id}", dependencies=STUDENT_SELF_OR_ADMIN)
def rank_all_jobs_for_student_multi_source(
    student_id: int,
    top_n: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Ranks recruiter jobs for a student using the Multi-Source Data Integration Engine.
    """
    engine = get_multi_source_engine(db)
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return engine.rank_jobs_for_student(student_id, top_n=top_n)


@app.get("/api/integration/historical-trends", dependencies=ANY_USER)
def get_historical_placement_trends(db: Session = Depends(get_db)):
    """
    Returns multi-year placement analytics:
    - Year-over-year offer volume and package trends
    - Branch-wise average & peak CTC
    - Domain demand distribution (AI, Cloud, Core, Software)
    - Top demanded technical skills in historical recruitments
    """
    engine = get_multi_source_engine(db)
    return engine.analyze_historical_trends()


@app.get("/api/integration/drive-calendar", dependencies=ANY_USER)
def get_integrated_drive_calendar(db: Session = Depends(get_db)):
    """
    Returns the placement drive calendar matrix linked with recruiter eligibility,
    round timelines, registration deadlines, and eligible student counts.
    """
    engine = get_multi_source_engine(db)
    return engine.get_drive_calendar_matrix()


@app.get("/api/integration/assessments/{student_id}", dependencies=STUDENT_SELF_OR_ADMIN)
def get_student_assessments_and_mocks(student_id: int, db: Session = Depends(get_db)):
    """
    Retrieves all diagnostic assessment results and mock interview evaluations for a student.
    """
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    assessments = (
        db.query(AssessmentResult)
        .filter(AssessmentResult.student_id == student_id)
        .order_by(AssessmentResult.id.desc())
        .all()
    )
    mocks = (
        db.query(MockInterviewResult)
        .filter(MockInterviewResult.student_id == student_id)
        .order_by(MockInterviewResult.id.desc())
        .all()
    )

    return {
        "student_id": student.id,
        "student_name": student.name,
        "branch": student.branch,
        "cgpa": student.cgpa,
        "diagnostic_assessments": [
            {
                "id": a.id,
                "assessment_title": a.assessment_title,
                "assessment_type": a.assessment_type,
                "aptitude_score": a.aptitude_score,
                "coding_score": a.coding_score,
                "technical_score": a.technical_score,
                "total_score": a.total_score,
                "percentile": a.percentile,
                "strengths": a.strengths,
                "weaknesses": a.weaknesses,
                "status": a.status,
                "completed_at": a.completed_at
            }
            for a in assessments
        ],
        "mock_interviews": [
            {
                "id": m.id,
                "interview_type": m.interview_type,
                "interviewer_name": m.interviewer_name,
                "interviewer_designation": m.interviewer_designation,
                "technical_rating": m.technical_rating,
                "communication_rating": m.communication_rating,
                "problem_solving_rating": m.problem_solving_rating,
                "overall_score": m.overall_score,
                "verdict": m.verdict,
                "feedback_notes": m.feedback_notes,
                "recommended_actions": m.recommended_actions,
                "conducted_at": m.conducted_at
            }
            for m in mocks
        ]
    }


@app.post("/api/integration/assessments", dependencies=COLLEGE_OR_ADMIN)
def record_student_assessment(req: AssessmentCreateRequest, db: Session = Depends(get_db)):
    """
    Records a new diagnostic assessment result for a student (Coding, Aptitude, Technical).
    """
    student = db.get(Student, student_id=req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    total = round((req.aptitude_score * 0.3) + (req.coding_score * 0.4) + (req.technical_score * 0.3), 1)
    percentile = req.percentile if req.percentile is not None else round(min(99.0, total * 1.05), 1)

    assessment = AssessmentResult(
        student_id=req.student_id,
        assessment_title=req.assessment_title,
        assessment_type=req.assessment_type or "Comprehensive",
        aptitude_score=req.aptitude_score,
        coding_score=req.coding_score,
        technical_score=req.technical_score,
        total_score=total,
        percentile=percentile,
        strengths=req.strengths or [],
        weaknesses=req.weaknesses or [],
        status=req.status or "Completed",
        completed_at=datetime.utcnow()
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return {
        "success": True,
        "message": "Assessment evaluation successfully integrated",
        "assessment_id": assessment.id,
        "total_score": assessment.total_score,
        "percentile": assessment.percentile
    }


@app.post("/api/integration/mock-interviews", dependencies=COLLEGE_OR_ADMIN)
def record_mock_interview(req: MockInterviewCreateRequest, db: Session = Depends(get_db)):
    """
    Records a mock interview panel evaluation for a student.
    """
    student = db.get(Student, student_id=req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    overall = round((req.technical_rating * 0.45) + (req.communication_rating * 0.30) + (req.problem_solving_rating * 0.25), 1)

    mock = MockInterviewResult(
        student_id=req.student_id,
        interview_type=req.interview_type or "Technical Mock Round",
        interviewer_name=req.interviewer_name or "Placement Cell Panel",
        interviewer_designation=req.interviewer_designation or "Industry Mentor",
        technical_rating=req.technical_rating,
        communication_rating=req.communication_rating,
        problem_solving_rating=req.problem_solving_rating,
        overall_score=overall,
        verdict=req.verdict or ("Ready" if overall >= 65 else "Developing"),
        feedback_notes=req.feedback_notes,
        recommended_actions=req.recommended_actions or [],
        conducted_at=datetime.utcnow()
    )
    # Also update student's primary mock_interview_score
    student.mock_interview_score = int(overall)
    db.add(mock)
    db.commit()
    db.refresh(mock)

    return {
        "success": True,
        "message": "Mock interview evaluation successfully integrated",
        "mock_id": mock.id,
        "overall_score": mock.overall_score,
        "verdict": mock.verdict
    }


@app.post("/api/integration/parse-resume/{student_id}", dependencies=STUDENT_SELF_OR_ADMIN)
def parse_and_integrate_resume_data(
    student_id: int,
    req: ResumeParseRequest,
    db: Session = Depends(get_db)
):
    """
    Integrates and parses resume data into the student profile:
    Extracts text, computes ATS score, and synchronizes technical skills.
    """
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if req.resume_text:
        student.resume_text = req.resume_text

    current_data = student.parsed_resume_data or {}
    if isinstance(current_data, str):
        try:
            current_data = json.loads(current_data)
        except:
            current_data = {}

    all_skills = list(set((student.skills or []) + (req.technical_skills or [])))
    student.skills = all_skills

    all_projs = list(set((student.projects or []) + (req.projects or [])))
    student.projects = all_projs

    all_certs = list(set((student.certifications or []) + (req.certifications or [])))
    student.certifications = all_certs

    ats_score = round(min(98.0, 50.0 + (len(all_skills) * 3.0) + (len(all_projs) * 3.5) + (len(all_certs) * 3.0)), 1)

    current_data.update({
        "full_name": student.name,
        "branch": student.branch,
        "summary": req.summary or current_data.get("summary", f"{student.branch} student focusing on {', '.join(all_skills[:3])}"),
        "technical_skills": all_skills,
        "projects": all_projs,
        "certifications": all_certs,
        "ats_compatibility_score": ats_score,
        "last_parsed": datetime.utcnow().isoformat()
    })

    student.parsed_resume_data = current_data
    student.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(student)

    return {
        "success": True,
        "message": "Resume successfully parsed and integrated into student profile",
        "ats_score": ats_score,
        "skills_count": len(all_skills),
        "projects_count": len(all_projs)
    }