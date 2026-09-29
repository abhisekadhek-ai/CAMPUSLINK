"""
models.py — SQLAlchemy ORM models matching campuslink_schema.sql.

`JSONList` is a small custom type so you can just assign/read Python lists
(e.g. student.skills = ["Python", "AWS"]) even though SQLite stores them
as a JSON text column underneath.
"""

import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, CheckConstraint,
    UniqueConstraint, DateTime, TypeDecorator, Text
)
from sqlalchemy.orm import relationship

from database import Base


class JSONList(TypeDecorator):
    """Stores a Python list as a JSON string; returns it as a list on read."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value if value is not None else [])

    def process_result_value(self, value, dialect):
        return json.loads(value) if value else []


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    branch = Column(String, nullable=False, index=True)
    cgpa = Column(Float, nullable=False)
    backlogs = Column(Integer, nullable=False, default=0)
    skills = Column(JSONList, nullable=False, default=list)
    certifications = Column(JSONList, nullable=False, default=list)
    mock_interview_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    offers = relationship("Offer", back_populates="student", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("cgpa >= 0 AND cgpa <= 10", name="ck_student_cgpa_range"),
        CheckConstraint(
            "mock_interview_score IS NULL OR mock_interview_score BETWEEN 0 AND 100",
            name="ck_student_interview_range",
        ),
    )


class Recruiter(Base):
    __tablename__ = "recruiters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    required_skills = Column(JSONList, nullable=False, default=list)
    min_cgpa = Column(Float, nullable=False, default=0)
    eligible_branches = Column(JSONList, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    drives = relationship("Drive", back_populates="recruiter")
    offers = relationship("Offer", back_populates="recruiter", cascade="all, delete-orphan")


class Drive(Base):
    __tablename__ = "drives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String, nullable=False)
    recruiter_id = Column(Integer, ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True)
    date = Column(String, nullable=False)          # ISO date string, e.g. "2026-09-20"
    time_slot = Column(String, nullable=False)      # e.g. "10:00-12:00"
    venue = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Scheduled")

    recruiter = relationship("Recruiter", back_populates="drives")

    __table_args__ = (
        CheckConstraint(
            "status IN ('Scheduled','Rescheduled','Cancelled','Completed')",
            name="ck_drive_status",
        ),
    )


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    recruiter_id = Column(Integer, ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="Issued")
    ctc_lpa = Column(Float)
    joining_date = Column(String)                   # ISO date string, nullable
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="offers")
    recruiter = relationship("Recruiter", back_populates="offers")

    __table_args__ = (
        CheckConstraint(
            "status IN ('Issued','Accepted','Deferred','Withdrawn','Joined')",
            name="ck_offer_status",
        ),
        UniqueConstraint("student_id", "recruiter_id", name="uq_offer_student_recruiter"),
    )
class UserAccount(Base):
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)

    # Supported roles: student, recruiter, admin
    role = Column(String, nullable=False, default="student")

    # Link an account to an existing student record.
    # Nullable so recruiter/admin accounts can be supported later.
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'recruiter', 'admin')",
            name="ck_user_account_role",
        ),
    )