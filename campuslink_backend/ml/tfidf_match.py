"""
tfidf_match.py — matches students to recruiters using TF-IDF + cosine
similarity, returning a fit score from 0 to 1000.

Your database has no free-text job description field — recruiters only
have `role` and `required_skills` (a list). So the "job description" used
here is built from role + required_skills combined into one text string,
e.g. "Data Scientist Python SQL Machine Learning". Likewise, a student's
"skill profile" is their skills + certifications combined into one string.
If you later add a real jd_text field, swap it in for build_recruiter_doc()
below and nothing else changes.

Run:
    python tfidf_match.py
It connects to campuslink_seed.db (built from your uploaded .sql file),
and prints real matches for one example recruiter and one example student.
"""

import json
import sqlite3

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_data(db_path="campuslink_seed.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, name, branch, cgpa, skills, certifications FROM students")
    students = [dict(row) for row in cur.fetchall()]

    cur.execute("SELECT id, company, role, required_skills, min_cgpa FROM recruiters")
    recruiters = [dict(row) for row in cur.fetchall()]

    conn.close()
    return students, recruiters


def _as_list(value):
    """Accepts a real list (from SQLAlchemy models) or a JSON string
    (from raw sqlite rows) and always returns a list."""
    if value is None:
        return []
    if isinstance(value, str):
        return json.loads(value) if value else []
    return list(value)


def build_student_doc(student):
    skills = _as_list(student["skills"])
    certs = _as_list(student["certifications"])
    # repeat skills once more so they weigh slightly more than certifications
    return " ".join(skills + skills + certs)


def build_recruiter_doc(recruiter):
    required = _as_list(recruiter["required_skills"])
    return " ".join([recruiter["role"]] + required + required)  # role once, skills doubled


class TfidfMatcher:
    """Fits one shared TF-IDF vocabulary across all students + recruiters,
    so student and recruiter vectors live in the same space and can be
    compared with cosine similarity."""

    def __init__(self, students, recruiters):
        self.students = students
        self.recruiters = recruiters

        student_docs = [build_student_doc(s) for s in students]
        recruiter_docs = [build_recruiter_doc(r) for r in recruiters]

        self.vectorizer = TfidfVectorizer(token_pattern=r"[A-Za-z0-9\+\#\.]+")
        all_docs = student_docs + recruiter_docs
        self.tfidf_matrix = self.vectorizer.fit_transform(all_docs)

        n_students = len(students)
        self.student_vectors = self.tfidf_matrix[:n_students]
        self.recruiter_vectors = self.tfidf_matrix[n_students:]

    def fit_score(self, student_idx, recruiter_idx) -> int:
        sim = cosine_similarity(
            self.student_vectors[student_idx], self.recruiter_vectors[recruiter_idx]
        )[0][0]
        return round(sim * 1000)

    def top_students_for_recruiter(self, recruiter_idx, top_n=10):
        sims = cosine_similarity(self.recruiter_vectors[recruiter_idx], self.student_vectors)[0]
        ranked = sorted(range(len(sims)), key=lambda i: -sims[i])[:top_n]
        return [
            {
                "student_id": self.students[i]["id"],
                "name": self.students[i]["name"],
                "branch": self.students[i]["branch"],
                "fit_score": round(sims[i] * 1000),
            }
            for i in ranked
        ]

    def top_recruiters_for_student(self, student_idx, top_n=10):
        sims = cosine_similarity(self.student_vectors[student_idx], self.recruiter_vectors)[0]
        ranked = sorted(range(len(sims)), key=lambda i: -sims[i])[:top_n]
        return [
            {
                "recruiter_id": self.recruiters[i]["id"],
                "company": self.recruiters[i]["company"],
                "role": self.recruiters[i]["role"],
                "fit_score": round(sims[i] * 1000),
            }
            for i in ranked
        ]


if __name__ == "__main__":
    # campuslink.db is your actual backend database, one folder up from ml/
    students, recruiters = load_data(db_path="../campuslink.db")
    print(f"Loaded {len(students)} students and {len(recruiters)} recruiters.\n")

    matcher = TfidfMatcher(students, recruiters)

    # Example 1: pick one recruiter, show its top 10 matching students
    r_idx = 0
    r = recruiters[r_idx]
    print(f"Top 10 students for: {r['company']} — {r['role']}")
    print(f"(required skills: {r['required_skills']})\n")
    for row in matcher.top_students_for_recruiter(r_idx, top_n=10):
        print(f"  #{row['student_id']:<5} {row['name']:<22} {row['branch']:<8} fit_score={row['fit_score']}")

    print()

    # Example 2: pick one student, show their top 10 matching recruiters
    s_idx = 0
    s = students[s_idx]
    print(f"Top 10 roles for: {s['name']} ({s['branch']})")
    print(f"(skills: {s['skills']})\n")
    for row in matcher.top_recruiters_for_student(s_idx, top_n=10):
        print(f"  #{row['recruiter_id']:<5} {row['company']:<15} {row['role']:<22} fit_score={row['fit_score']}")
