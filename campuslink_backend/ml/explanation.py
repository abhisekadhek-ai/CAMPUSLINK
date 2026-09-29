"""
explanation.py — builds a natural-language explanation sentence for a
student-recruiter match, in this style:

    "Below Threshold: CGPA meets criteria, but skill gap in cloud
    technologies, mock-interview score below benchmark."

The first clause is always the CGPA check. Then it says "but" right
before the FIRST problem it finds, and just uses commas after that —
matching how the example sentence reads.
"""


def generate_explanation(
    cgpa: float,
    min_cgpa: float,
    missing_skills: list,
    mock_interview_score: int,
    min_interview_score: int,
    branch_ok: bool = True,
) -> str:
    cgpa_ok = cgpa >= min_cgpa
    interview_ok = mock_interview_score >= min_interview_score
    skills_ok = len(missing_skills) == 0

    # Build each clause as (text, is_a_problem)
    clauses = []

    if not branch_ok:
        clauses.append(("branch is not eligible for this role", True))

    clauses.append((
        "CGPA meets criteria" if cgpa_ok else "CGPA is below the required minimum",
        not cgpa_ok,
    ))

    clauses.append((
        f"skill gap in {', '.join(missing_skills)}" if not skills_ok else "all required skills are covered",
        not skills_ok,
    ))

    clauses.append((
        "mock-interview score below benchmark" if not interview_ok else "mock-interview score meets benchmark",
        not interview_ok,
    ))

    # Decide overall status
    if not cgpa_ok or not branch_ok:
        status = "Not Eligible"
    elif not skills_ok or not interview_ok:
        status = "Below Threshold"
    else:
        status = "Shortlisted"

    # Assemble the sentence: "but" appears once, right before the first problem clause
    sentence_parts = []
    said_but = False
    for i, (text, is_problem) in enumerate(clauses):
        if i == 0:
            sentence_parts.append(text)
        elif is_problem and not said_but:
            sentence_parts.append(f"but {text}")
            said_but = True
        else:
            sentence_parts.append(text)

    body = ", ".join(sentence_parts)
    return f"{status}: {body}."


if __name__ == "__main__":
    examples = [
        {
            "cgpa": 7.8, "min_cgpa": 7.0,
            "missing_skills": ["AWS", "Docker", "Kubernetes"],
            "mock_interview_score": 52, "min_interview_score": 60,
        },
        {
            "cgpa": 8.9, "min_cgpa": 7.0,
            "missing_skills": [],
            "mock_interview_score": 82, "min_interview_score": 60,
        },
        {
            "cgpa": 6.1, "min_cgpa": 7.0,
            "missing_skills": ["Python"],
            "mock_interview_score": 40, "min_interview_score": 60,
        },
    ]
    for e in examples:
        print(generate_explanation(**e))
