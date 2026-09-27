"""
database.py — SQLite engine/session setup for CampusLink (FastAPI + SQLAlchemy).

Usage in a route:

    from database import get_db
    from fastapi import Depends
    from sqlalchemy.orm import Session

    @app.get("/students")
    def list_students(db: Session = Depends(get_db)):
        return db.query(Student).all()
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./campuslink.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
