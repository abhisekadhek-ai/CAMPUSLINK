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

            "('Applied', 'Under Review', 'Interview', "

            "'Rejected', 'Selected')",

            name="ck_job_application_status",

        ),

    )