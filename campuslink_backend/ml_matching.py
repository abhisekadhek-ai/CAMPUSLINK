"""
ml_matching.py — CampusLink AI matching engine (scikit-learn).

Drop-in replacement for the rule-based `match_student_to_recruiter` in main.py.
Works directly on the SQLAlchemy `Student` / `Recruiter` objects and returns
the SAME dict shape the frontend already expects (plus `ml_similarity`).

Score (0-100) = weighted blend of
    40%  skill coverage      (required skills the student has, after alias normalisation)
    30%  ML text similarity  (char n-gram TF-IDF cosine: student skills+certs vs role+required skills)
    15%  CGPA
    15%  mock interview score

Eligibility (CGPA minimum, branch list) is a hard gate: ineligible candidates
are always ranked below eligible ones.
"""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

W_COVERAGE = 0.40
W_SIMILARITY = 0.30
W_CGPA = 0.15
W_MOCK = 0.15
SHORTLIST_COVERAGE = 60.0  # same threshold as the original rule-based logic

# Map common spellings to one canonical skill name
ALIASES = {
    "js": "javascript", "reactjs": "react", "react.js": "react",
    "node": "nodejs", "node.js": "nodejs", "py": "python",
    "ml": "machine learning", "dl": "deep learning",
    "postgres": "postgresql", "mongo": "mongodb", "c++": "cpp",
    "sklearn": "scikit-learn", "tf": "tensorflow", "dsa": "data structures",
}


def _canon(skill: str) -> str:
    s = skill.strip().lower()
    return ALIASES.get(s, s)


def _skills(items) -> set[str]:
    return {_canon(x) for x in (items or []) if x and str(x).strip()}


def _student_text(s) -> str:
    return " ".join(sorted(_skills(s.skills)) + sorted(_skills(s.certifications)))


def _recruiter_text(r) -> str:
    return f"{r.role} " + " ".join(sorted(_skills(r.required_skills)))


def _vectorizer() -> TfidfVectorizer:
    # char n-grams tolerate spelling variants ("ReactJS" vs "React") and typos
    return TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)


def _similarity_matrix(students: list, recruiters: list):
    """Rows = students, cols = recruiters. IDF is learned from ALL texts at once."""
    if not students or not recruiters:
        return []
    s_texts = [_student_text(s) for s in students]
    r_texts = [_recruiter_text(r) for r in recruiters]
    vec = _vectorizer().fit(s_texts + r_texts)
    return cosine_similarity(vec.transform(s_texts), vec.transform(r_texts))


def _build_match(student, recruiter, sim: float) -> dict:
    required = _skills(recruiter.required_skills)
    have = _skills(student.skills)
    missing = sorted(required - have)
    coverage = round(len(required & have) / len(required) * 100, 1) if required else 100.0

    cgpa_ok = student.cgpa >= (recruiter.min_cgpa or 0)
    branches = {b.strip().lower() for b in (recruiter.eligible_branches or [])}
    branch_ok = not branches or student.branch.strip().lower() in branches  # empty list = open to all
    eligible = cgpa_ok and branch_ok

    reasons = [
        f"CGPA {student.cgpa} meets the minimum of {recruiter.min_cgpa}." if cgpa_ok
        else f"CGPA {student.cgpa} is below the required minimum of {recruiter.min_cgpa}.",
        "All required skills are covered." if not missing
        else f"Skill gap in: {', '.join(missing)}.",
    ]
    if not branch_ok:
        reasons.append(
            f"Branch '{student.branch}' is not in the eligible list {recruiter.eligible_branches}."
        )

    score = 100 * (
        W_COVERAGE * coverage / 100
        + W_SIMILARITY * float(sim)
        + W_CGPA * min(student.cgpa / 10, 1)
        + W_MOCK * (student.mock_interview_score or 0) / 100
    )

    status = (
        "Shortlisted" if eligible and coverage >= SHORTLIST_COVERAGE
        else "Below Threshold" if eligible
        else "Not Eligible"
    )
    return {
        "student_id": student.id,
        "student_name": student.name,
        "recruiter_id": recruiter.id,
        "role": recruiter.role,
        "company": recruiter.company,
        "match_score": round(score, 1),
        "status": status,
        "missing_skills": missing,
        "coverage_percent": coverage,
        "ml_similarity": round(float(sim) * 100, 1),
        "explanation": " ".join(reasons),
    }


def _sort(results: list[dict]) -> list[dict]:
    # Eligible first, then by score
    return sorted(results, key=lambda m: (m["status"] != "Not Eligible", m["match_score"]), reverse=True)


# ---------------------------------------------------------------------------
# Public API used by main.py
# ---------------------------------------------------------------------------

def match_student_to_recruiter(student, recruiter) -> dict:
    """Single pair (used by the /shortlist route)."""
    sim = _similarity_matrix([student], [recruiter])[0][0]
    return _build_match(student, recruiter, sim)


def rank_recruiters_for_student(student, recruiters: list) -> list[dict]:
    """Student view: best roles for this student."""
    sims = _similarity_matrix([student], recruiters)
    if len(sims) == 0:
        return []
    return _sort([_build_match(student, r, sims[0][j]) for j, r in enumerate(recruiters)])


def rank_students_for_recruiter(recruiter, students: list) -> list[dict]:
    """Recruiter view: best candidates for this role."""
    sims = _similarity_matrix(students, [recruiter])
    if len(sims) == 0:
        return []
    return _sort([_build_match(s, recruiter, sims[i][0]) for i, s in enumerate(students)])


# ---------------------------------------------------------------------------
# Quick self-test:  python ml_matching.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from types import SimpleNamespace as NS

    alice = NS(id=1, name="Alice", branch="CSE", cgpa=8.5, backlogs=0,
               skills=["Python", "ReactJS", "SQL", "ML"],
               certifications=["AWS Cloud Practitioner"], mock_interview_score=80)
    bob = NS(id=2, name="Bob", branch="MECH", cgpa=7.0, backlogs=1,
             skills=["AutoCAD", "SolidWorks"], certifications=[], mock_interview_score=60)
    dev = NS(id=1, company="Acme", role="Full Stack Developer",
             required_skills=["python", "react", "sql"], min_cgpa=7.0, eligible_branches=["CSE", "IT"])
    cad = NS(id=2, company="Gearz", role="Design Engineer",
             required_skills=["autocad", "solidworks"], min_cgpa=6.5, eligible_branches=["MECH"])

    for m in rank_recruiters_for_student(alice, [dev, cad]):
        print(m["company"], m["match_score"], m["status"], m["missing_skills"])
    print()
    for m in rank_students_for_recruiter(cad, [alice, bob]):
        print(m["student_name"], m["match_score"], m["status"])
