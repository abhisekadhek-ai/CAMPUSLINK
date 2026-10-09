"""

models.py — CampusLink SQLAlchemy ORM models.



Preserves existing student, recruiter, drive, offer, and account

models. Adds College and JobApplication for placement tracking.

"""



import json

from datetime import datetime



from sqlalchemy import (

    Column,

    Integer,

    String,

    Float,

    ForeignKey,

    CheckConstraint,

    UniqueConstraint,

    DateTime,

    TypeDecorator,

    Text,

    Boolean,

)

from sqlalchemy.orm import relationship



from database import Base





class JSONList(TypeDecorator):
    """Store Python lists as JSON text in SQLite."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value if value is not None else [])

    def process_result_value(self, value, dialect):
        return json.loads(value) if value else []


class JSONDict(TypeDecorator):
    """Store Python dicts as JSON text in SQLite."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value if value is not None else {})

    def process_result_value(self, value, dialect):
        return json.loads(value) if value else {}





# ============================================================

# COLLEGE

# ============================================================



class College(Base):

    __tablename__ = "colleges"



    id = Column(

        Integer,

        primary_key=True,

        autoincrement=True,

    )



    # Example: COL001, COL002, COL003

    college_code = Column(

        String,

        nullable=False,

        unique=True,

        index=True,

    )



    college_name = Column(

        String,

        nullable=False,

        index=True,

    )



    email = Column(

        String,

        nullable=False,

        unique=True,

        index=True,

    )



    created_at = Column(

        DateTime,

        default=datetime.utcnow,

    )



    students = relationship(

        "Student",

        back_populates="college",

    )



    user_account = relationship(

        "UserAccount",

        back_populates="college",

        uselist=False,

    )





# ============================================================

# STUDENT

# ============================================================



class Student(Base):

    __tablename__ = "students"



    id = Column(

        Integer,

        primary_key=True,

        autoincrement=True,

    )



    name = Column(

        String,

        nullable=False,

    )



    branch = Column(

        String,

        nullable=False,

        index=True,

    )



    cgpa = Column(

        Float,

        nullable=False,

    )



    backlogs = Column(

        Integer,

        nullable=False,

        default=0,

    )



    skills = Column(

        JSONList,

        nullable=False,

        default=list,

    )



    certifications = Column(

        JSONList,

        nullable=False,

        default=list,

    )



    projects = Column(

        JSONList,

        nullable=False,

        default=list,

    )



    mock_interview_score = Column(

        Integer,

    )




    # --------------------------------------------------------

    # NEW: Student belongs to a College

    #

    # IMPORTANT:

    # nullable=True keeps your existing 1000 students safe.

    # We will assign their college later.

    # --------------------------------------------------------



    college_id = Column(

        Integer,

        ForeignKey(

            "colleges.id",

            ondelete="SET NULL",

        ),

        nullable=True,

        index=True,

    )



    college_approval = Column(
        String,
        nullable=False,
        default="Pending",
    )

    resume_url = Column(
        String,
        nullable=True,
    )

    resume_text = Column(
        Text,
        nullable=True,
    )

    parsed_resume_data = Column(
        JSONDict,
        nullable=False,
        default=dict,
    )

    created_at = Column(

        DateTime,

        default=datetime.utcnow,

    )



    updated_at = Column(

        DateTime,

        default=datetime.utcnow,

        onupdate=datetime.utcnow,

    )



    # --------------------------------------------------------

    # RELATIONSHIPS

    # --------------------------------------------------------



    college = relationship(

        "College",

        back_populates="students",

    )



    offers = relationship(

        "Offer",

        back_populates="student",

        cascade="all, delete-orphan",

    )



    job_applications = relationship(

        "JobApplication",

        back_populates="student",

        cascade="all, delete-orphan",

    )

    assessment_results = relationship(
        "AssessmentResult",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    mock_interview_results = relationship(
        "MockInterviewResult",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    @property
    def college_name(self):
        return self.college.college_name if self.college else None



    __table_args__ = (

        CheckConstraint(

            "cgpa >= 0 AND cgpa <= 10",

            name="ck_student_cgpa_range",

        ),



        CheckConstraint(

            "mock_interview_score IS NULL OR "

            "mock_interview_score BETWEEN 0 AND 100",

            name="ck_student_interview_range",

        ),

    )





# ============================================================

# RECRUITER

# ============================================================



class Recruiter(Base):

    __tablename__ = "recruiters"



    id = Column(

        Integer,

        primary_key=True,

        autoincrement=True,

    )



    company = Column(

        String,

        nullable=False,

        index=True,

    )



    role = Column(

        String,

        nullable=False,

    )



    required_skills = Column(

        JSONList,

        nullable=False,

        default=list,

    )



    min_cgpa = Column(

        Float,

        nullable=False,

        default=0,

    )



    eligible_branches = Column(

        JSONList,

        nullable=False,

        default=list,

    )

    job_description = Column(
        Text,
        nullable=True,
    )

    responsibilities = Column(
        JSONList,
        nullable=False,
        default=list,
    )

    max_backlogs = Column(
        Integer,
        nullable=False,
        default=0,
    )

    min_mock_score = Column(
        Integer,
        nullable=False,
        default=50,
    )

    min_assessment_score = Column(
        Integer,
        nullable=False,
        default=50,
    )

    location = Column(
        String,
        nullable=True,
        default="On-Campus / Hybrid",
    )

    experience_level = Column(
        String,
        nullable=True,
        default="Entry Level / Fresher",
    )

    allowed_batches = Column(
        JSONList,
        nullable=False,
        default=list,
    )

    created_at = Column(

        DateTime,

        default=datetime.utcnow,

    )



    drives = relationship(

        "Drive",

        back_populates="recruiter",

    )



    offers = relationship(

        "Offer",

        back_populates="recruiter",

        cascade="all, delete-orphan",

    )





# ============================================================

# DRIVE

# ============================================================



class Drive(Base):

    __tablename__ = "drives"



    id = Column(

        Integer,

        primary_key=True,

        autoincrement=True,

    )



    company = Column(

        String,

        nullable=False,

    )



    recruiter_id = Column(

        Integer,

        ForeignKey(

            "recruiters.id",

            ondelete="SET NULL",

        ),

        nullable=True,

    )



    date = Column(

        String,

        nullable=False,

    )



    time_slot = Column(

        String,

        nullable=False,

    )



    venue = Column(

        String,

        nullable=False,

    )



    status = Column(

        String,

        nullable=False,

        default="Scheduled",

    )



    resources = Column(

        JSONList,

        nullable=False,

        default=list,

    )



    interview_panels = Column(

        JSONList,

        nullable=False,

        default=list,

    )



    infrastructure_capacity = Column(

        Integer,

        nullable=True,

        default=100,

    )

    registration_deadline = Column(
        String,
        nullable=True,
    )

    round_timeline = Column(
        JSONList,
        nullable=False,
        default=list,
    )



    recruiter = relationship(

        "Recruiter",

        back_populates="drives",

    )



    __table_args__ = (

        CheckConstraint(

            "status IN "

            "('Scheduled','Rescheduled','Cancelled','Completed')",

            name="ck_drive_status",

        ),

    )





# ============================================================

# OFFER

# ============================================================



class Offer(Base):

    __tablename__ = "offers"



    id = Column(

        Integer,

        primary_key=True,

        autoincrement=True,

    )



    student_id = Column(

        Integer,

        ForeignKey(

            "students.id",

            ondelete="CASCADE",

        ),

        nullable=False,

    )



    recruiter_id = Column(

        Integer,

        ForeignKey(

            "recruiters.id",

            ondelete="CASCADE",

        ),

        nullable=False,

    )



    status = Column(

        String,

        nullable=False,

        default="Issued",

    )



    ctc_lpa = Column(

        Float,

    )



    joining_date = Column(

        String,

    )



    created_at = Column(

        DateTime,

        default=datetime.utcnow,

    )



    student = relationship(

        "Student",

        back_populates="offers",

    )



    recruiter = relationship(

        "Recruiter",

        back_populates="offers",

    )



    __table_args__ = (

        CheckConstraint(

            "status IN "

            "('Issued','Accepted','Deferred','Withdrawn','Joined')",

            name="ck_offer_status",

        ),



        UniqueConstraint(

            "student_id",

            "recruiter_id",

            name="uq_offer_student_recruiter",

        ),

    )





# ============================================================

# USER ACCOUNT

# ============================================================



class UserAccount(Base):

    __tablename__ = "user_accounts"



    id = Column(

        Integer,

        primary_key=True,

        autoincrement=True,

    )



    email = Column(

        String,

        nullable=False,

        unique=True,

        index=True,

    )



    password_hash = Column(

        String,

        nullable=False,

    )



    role = Column(

        String,

        nullable=False,

        default="student",

    )



    # --------------------------------------------------------

    # EXISTING STUDENT ACCOUNT CONNECTION

    # --------------------------------------------------------



    student_id = Column(

        Integer,

        ForeignKey(

            "students.id",

            ondelete="CASCADE",

        ),

        nullable=True,

        unique=True,

    )



    # --------------------------------------------------------

    # EXISTING RECRUITER ACCOUNT CONNECTION

    # --------------------------------------------------------



    recruiter_id = Column(

        Integer,

        ForeignKey(

            "recruiters.id",

            ondelete="CASCADE",

        ),

        nullable=True,

        unique=True,

    )



    # --------------------------------------------------------

    # NEW COLLEGE ACCOUNT CONNECTION

    #

    # One college login account belongs to one college.

    # --------------------------------------------------------



    college_id = Column(

        Integer,

        ForeignKey(

            "colleges.id",

            ondelete="CASCADE",

        ),

        nullable=True,

        unique=True,

    )



    created_at = Column(

        DateTime,

        default=datetime.utcnow,

    )



    # --------------------------------------------------------

    # RELATIONSHIPS

    # --------------------------------------------------------



    college = relationship(

        "College",

        back_populates="user_account",

    )



    __table_args__ = (

        CheckConstraint(

            "role IN "

            "('student', 'recruiter', 'college', 'admin')",

            name="ck_user_account_role",

        ),

    )





# ============================================================

# PASSWORD RESET OTP

# ============================================================



class PasswordResetOTP(Base):

    __tablename__ = "password_reset_otps"



    id = Column(

        Integer,

        primary_key=True,

        autoincrement=True,

    )



    email = Column(

        String,

        nullable=False,

        index=True,

    )



    otp_hash = Column(

        String,

        nullable=False,

    )



    expires_at = Column(

        DateTime,

        nullable=False,

    )



    attempts = Column(

        Integer,

        nullable=False,

        default=0,

    )



    used = Column(

        Boolean,

        nullable=False,

        default=False,

    )



    created_at = Column(

        DateTime,

        default=datetime.utcnow,

    )





# ============================================================

# JOB APPLICATION

# ============================================================



class JobApplication(Base):

    __tablename__ = "job_applications"



    id = Column(

        Integer,

        primary_key=True,

        autoincrement=True,

    )



    student_id = Column(

        Integer,

        ForeignKey(

            "students.id",

            ondelete="CASCADE",

        ),

        nullable=False,

        index=True,

    )



    job_title = Column(

        String,

        nullable=False,

    )



    company = Column(

        String,

        nullable=False,

    )



    college = Column(

        String,

        nullable=True,

    )



    job_url = Column(

        Text,

        nullable=False,

    )



    source = Column(

        String,

        nullable=False,

        default="External",

    )



    status = Column(

        String,

        nullable=False,

        default="Applied",

    )



    college_approval = Column(

        String,

        nullable=False,

        default="Pending",

    )

    resume_url = Column(

        String,

        nullable=True,

    )



    applied_at = Column(

        DateTime,

        default=datetime.utcnow,

        nullable=False,

    )



    updated_at = Column(

        DateTime,

        default=datetime.utcnow,

        onupdate=datetime.utcnow,

        nullable=False,

    )



    student = relationship(

        "Student",

        back_populates="job_applications",

    )



    __table_args__ = (

        UniqueConstraint(

            "student_id",

            "job_url",

            name="uq_job_application_student_url",

        ),



        CheckConstraint(

            "status IN "

            "('Applied', 'Under Review', 'Shortlisted', 'Interview', "

            "'Rejected', 'Selected')",

            name="ck_job_application_status",

        ),

    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_role = Column(String, nullable=False, default="student", index=True)  # student, recruiter, admin, all
    recipient_id = Column(Integer, nullable=True, index=True)
    recipient_name = Column(String, nullable=True)
    recipient_email = Column(String, nullable=True)
    recipient_phone = Column(String, nullable=True)

    category = Column(String, nullable=False, index=True)
    # categories:
    # 'shortlist_interview' (Shortlisting and interview schedules)
    # 'document_deadline' (Document submission deadlines)
    # 'offer_status' (Offer status updates)
    # 'drive_announcement' (Drive announcements and eligibility criteria)
    # 'general'

    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    channels = Column(JSONList, default=list)  # ["in_app", "email", "whatsapp"]
    dispatch_status = Column(String, default="Delivered")

    email_delivery_status = Column(String, default="Sent")
    whatsapp_delivery_status = Column(String, default="Delivered")

    meta_data = Column(JSONList, default=dict)
    deadline_at = Column(DateTime, nullable=True)

    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ============================================================
# HISTORICAL PLACEMENT RECORD
# ============================================================

class HistoricalPlacementRecord(Base):
    __tablename__ = "historical_placement_records"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    batch_year = Column(
        String,
        nullable=False,
        index=True,
    )  # e.g., "2023-2024", "2024-2025"

    company = Column(
        String,
        nullable=False,
        index=True,
    )

    role = Column(
        String,
        nullable=False,
    )

    branch = Column(
        String,
        nullable=False,
        index=True,
    )

    package_ctc_lpa = Column(
        Float,
        nullable=False,
    )

    students_placed = Column(
        Integer,
        nullable=False,
        default=1,
    )

    hiring_domain = Column(
        String,
        nullable=False,
        index=True,
    )  # e.g., "Software Engineering", "Cloud & DevOps", "Data & AI"

    key_skills_demanded = Column(
        JSONList,
        nullable=False,
        default=list,
    )

    avg_cgpa_placed = Column(
        Float,
        nullable=False,
        default=7.5,
    )

    min_cgpa_placed = Column(
        Float,
        nullable=False,
        default=6.5,
    )

    selection_ratio_percent = Column(
        Float,
        nullable=False,
        default=15.0,
    )

    placement_season = Column(
        String,
        nullable=False,
        default="Phase 1 - Autumn",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# ASSESSMENT RESULT
# ============================================================

class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assessment_title = Column(
        String,
        nullable=False,
    )

    assessment_type = Column(
        String,
        nullable=False,
        default="Comprehensive",
    )  # Coding, Aptitude, Technical MCQ, Comprehensive

    aptitude_score = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    coding_score = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    technical_score = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    total_score = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    percentile = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    strengths = Column(
        JSONList,
        nullable=False,
        default=list,
    )

    weaknesses = Column(
        JSONList,
        nullable=False,
        default=list,
    )

    status = Column(
        String,
        nullable=False,
        default="Completed",
    )

    completed_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    student = relationship(
        "Student",
        back_populates="assessment_results",
    )


# ============================================================
# MOCK INTERVIEW RESULT
# ============================================================

class MockInterviewResult(Base):
    __tablename__ = "mock_interview_results"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interview_type = Column(
        String,
        nullable=False,
        default="Technical Mock Round",
    )  # Technical Mock Round, System Design, HR & Behavioral

    interviewer_name = Column(
        String,
        nullable=False,
        default="Placement Cell Panel",
    )

    interviewer_designation = Column(
        String,
        nullable=True,
        default="Senior Industry Mentor",
    )

    technical_rating = Column(
        Float,
        nullable=False,
        default=0.0,
    )  # 0-100

    communication_rating = Column(
        Float,
        nullable=False,
        default=0.0,
    )  # 0-100

    problem_solving_rating = Column(
        Float,
        nullable=False,
        default=0.0,
    )  # 0-100

    overall_score = Column(
        Float,
        nullable=False,
        default=0.0,
    )  # 0-100

    verdict = Column(
        String,
        nullable=False,
        default="Developing",
    )  # Exceptional, Ready, Developing, Needs Preparation

    feedback_notes = Column(
        Text,
        nullable=True,
    )

    recommended_actions = Column(
        JSONList,
        nullable=False,
        default=list,
    )

    conducted_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    student = relationship(
        "Student",
        back_populates="mock_interview_results",
    )