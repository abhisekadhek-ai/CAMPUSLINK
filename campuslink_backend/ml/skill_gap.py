"""
skill_gap.py — compares a student's skills to a recruiter's required
skills and returns which required skills are missing.
"""


def skill_gap(student_skills: list, required_skills: list) -> dict:
    """
    Parameters:
        student_skills    -- list of skills the student has, e.g. ["Python", "SQL"]
        required_skills    -- list of skills the role requires, e.g. ["Python", "AWS", "Docker"]

    Returns a dict with:
        matched_skills      -- required skills the student already has
        missing_skills      -- required skills the student does NOT have
        coverage_percent    -- % of required skills the student covers
    """
    # lowercase + strip so "python" and "Python " match "Python"
    have = set(s.strip().lower() for s in student_skills)
    required = set(s.strip().lower() for s in required_skills)

    matched = required & have
    missing = required - have
    coverage = round(len(matched) / len(required) * 100, 1) if required else 100.0

    return {
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "coverage_percent": coverage,
    }


if __name__ == "__main__":
    examples = [
        {
            "student_skills": ["Python", "React", "SQL", "AWS"],
            "required_skills": ["Python", "AWS", "Docker"],
        },
        {
            "student_skills": ["HTML", "CSS", "JavaScript"],
            "required_skills": ["Python", "Machine Learning", "AWS"],
        },
        {
            "student_skills": ["Python", "Docker", "AWS"],
            "required_skills": ["python", "docker", "aws"],  # case-insensitive check
        },
    ]
    for e in examples:
        print(e, "->", skill_gap(e["student_skills"], e["required_skills"]))
