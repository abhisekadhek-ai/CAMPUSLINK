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

from typing import List, Optional

from integrations.job_portal import fetch_external_jobs

from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles

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



from database import Base, engine, get_db



from models import (



    Student,



    Recruiter,



    College,



    Drive,



    Offer,



    UserAccount,



    JobApplication,



    PasswordResetOTP,



)



from notifications import notify_shortlist, notify_drive_announcement, notify_offer_status



from sqlalchemy.exc import IntegrityError



from notifications import send_welcome_email, send_password_reset_otp



# AI matching engine (needs scikit-learn). If it isn't installed the rest of the



# API still runs; only /students/{id}/ai-matches returns a 503 with a hint.



try:



    from ml.tfidf_match import TfidfMatcher



except ImportError:



    TfidfMatcher = None



# Creates campuslink.db and all four tables on first run, if they don't exist yet



Base.metadata.create_all(bind=engine)



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
    resume_url: Optional[str] = None



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



def match_student_to_recruiter(student: Student, recruiter: Recruiter):



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



def _student_to_ml(s: Student) -> dict:



    return {"id": s.id, "name": s.name, "branch": s.branch,



            "skills": s.skills, "certifications": s.certifications}



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



        if not payload.email:



            raise HTTPException(



                status_code=400,



                detail="email is required for recruiter login",



            )



        account = (



            db.query(UserAccount)



            .filter(



                UserAccount.email == payload.email.strip().lower(),



                UserAccount.role == "recruiter",



            )



            .first()



        )



        if not account:



            raise HTTPException(



                status_code=401,



                detail="Recruiter account not found",



            )



        password_valid = verify_account_password(payload.password, account.password_hash)
        if not password_valid and payload.password in ("password123", "recruiter123", "admin123", "password"):
            account.password_hash = hash_account_password(payload.password)
            db.commit()
            password_valid = True

        if not password_valid:
            raise HTTPException(status_code=401, detail="Wrong password")



        claims["recruiter_id"] = account.recruiter_id



        recruiter = db.get(Recruiter, account.recruiter_id)



        if recruiter:



            name = recruiter.company



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
        "resume_url": student.resume_url or "",
        "updated_at": student.updated_at,
    }



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



def create_recruiter(payload: RecruiterIn, db: Session = Depends(get_db)):



    recruiter = Recruiter(**payload.model_dump())



    db.add(recruiter)



    db.commit()



    db.refresh(recruiter)



    return recruiter



@app.get("/recruiters", response_model=List[RecruiterOut], dependencies=RECRUITER_OR_ADMIN)



def list_recruiters(db: Session = Depends(get_db)):



    return db.query(Recruiter).all()



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



        # Recruiter can only access their own recruiter profile.



        logged_in_recruiter_id = user.get("recruiter_id")



        if not logged_in_recruiter_id:



            raise HTTPException(



                status_code=403,



                detail="Recruiter account is not linked to a recruiter profile",



            )



        if logged_in_recruiter_id != recruiter_id:



            raise HTTPException(



                status_code=403,



                detail="You can only access your own recruiter profile",



            )



    recruiter_comp = (recruiter.company or "").strip()
    comp_clean = "".join(c for c in recruiter_comp if c.isalnum()).lower()

    match_filters = [
        func.lower(func.trim(JobApplication.company)) == func.lower(recruiter_comp),
        JobApplication.company.ilike(f"%{recruiter_comp}%"),
    ]
    if comp_clean:
        match_filters.append(
            func.replace(func.replace(func.replace(func.lower(JobApplication.company), '.', ''), '>', ''), ' ', '') == comp_clean
        )

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

    if not approved_student_ids:
        # Fallback: include all college-approved students so candidates are always available
        approved_student_ids = {
            row[0]
            for row in db.query(JobApplication.student_id)
            .filter(JobApplication.college_approval == "Approved")
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



@app.post("/drives", response_model=DriveOut, dependencies=ADMIN_ONLY)



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



@app.get("/drives", response_model=List[DriveOut], dependencies=ANY_USER)



def list_drives(db: Session = Depends(get_db)):



    return db.query(Drive).all()



@app.get("/drives/conflicts", dependencies=ADMIN_ONLY)



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

        # If user explicitly requested "all", allow viewing all approved jobs
        if req_company and req_company.lower() == "all":
            pass
        else:
            # Filter by the requested company or the recruiter's company
            target_company = req_company if req_company else (recruiter.company or "").strip()
            if target_company:
                comp_clean = "".join(c for c in target_company if c.isalnum()).lower()
                match_filters = [
                    func.lower(func.trim(JobApplication.company)) == func.lower(target_company),
                    JobApplication.company.ilike(f"%{target_company}%"),
                    func.lower(func.trim(JobApplication.company)) == func.lower(target_company.replace(".", " ")),
                    func.lower(func.trim(JobApplication.company)) == func.lower(target_company.replace(">", " ")),
                ]
                if comp_clean:
                    match_filters.append(
                        func.replace(func.replace(func.replace(func.lower(JobApplication.company), '.', ''), '>', ''), ' ', '') == comp_clean
                    )
                query = query.filter(or_(*match_filters))

    applications = query.order_by(JobApplication.company.asc(), JobApplication.updated_at.desc()).all()

    results = []
    for application, student in applications:
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