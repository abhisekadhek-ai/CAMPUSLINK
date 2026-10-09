"""
readiness_score.py — computes a student's readiness/employability score
from a weighted formula of CGPA, skill count, certifications, projects, and mock-interview score.

Weights (out of 100 total):
    CGPA                 -> 30 points   (cgpa / 10 * 30)
    Skill count          -> 15 points   (3 points per skill, capped at 15)
    Certifications count -> 15 points   (5 points per cert, capped at 15)
    Projects count       -> 15 points   (5 points per project, capped at 15)
    Mock interview score -> 25 points   (score / 100 * 25)
"""


def readiness_score(
    cgpa: float,
    skill_count: int = 0,
    mock_interview_score: float = 0,
    cert_count: int = 0,
    project_count: int = 0,
) -> dict:
    """
    Returns a dict with the numeric score (0-100) and its readiness label.

    Parameters:
        cgpa                   -- 0 to 10
        skill_count            -- number of skills the student has listed
        mock_interview_score   -- 0 to 100
        cert_count             -- number of completed certifications
        project_count          -- number of completed projects
    """
    cgpa_component = (cgpa / 10) * 30
    skill_component = min(skill_count * 3, 15)
    cert_component = min(cert_count * 5, 15)
    project_component = min(project_count * 5, 15)
    interview_component = ((mock_interview_score or 0) / 100) * 25

    total = round(
        cgpa_component + skill_component + cert_component + project_component + interview_component,
        1,
    )
    total = max(0, min(100, total))

    if total >= 85:
        label = "Highly Employable"
    elif total >= 65:
        label = "Ready"
    elif total >= 40:
        label = "Developing"
    else:
        label = "Not Ready"

    return {
        "score": total,
        "label": label,
        "breakdown": {
            "cgpa_component": round(cgpa_component, 1),
            "skill_component": round(skill_component, 1),
            "certifications_component": round(cert_component, 1),
            "projects_component": round(project_component, 1),
            "interview_component": round(interview_component, 1),
        },
    }



if __name__ == "__main__":
    # Quick examples
    examples = [
        {"cgpa": 8.7, "skill_count": 4, "mock_interview_score": 78},
        {"cgpa": 6.8, "skill_count": 2, "mock_interview_score": 45},
        {"cgpa": 9.1, "skill_count": 6, "mock_interview_score": 88},
    ]
    for e in examples:
        result = readiness_score(**e)
        print(e, "->", result)
