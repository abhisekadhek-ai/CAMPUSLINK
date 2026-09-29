"""
generate_data.py — creates sample data for the CampusLink AI matching engine.

Run:
    python generate_data.py

Produces two files in the same folder:
    students.csv     — 50 fake students
    recruiters.csv   — 10 fake recruiters / roles

These match the same fields used by the FastAPI backend, so this data can
be loaded straight into the students/recruiters tables, or used on its own
to train and test a matching model in pandas / scikit-learn.
"""

import random
import csv

random.seed(42)  # remove this line if you want different data every run

BRANCHES = ["CSE", "IT", "ECE", "EEE", "MECH", "CIVIL"]

SKILL_POOL = [
    "Python", "Java", "C++", "JavaScript", "SQL", "AWS", "Azure", "Docker",
    "Kubernetes", "React", "Node.js", "Django", "Spring Boot", "Machine Learning",
    "TensorFlow", "Data Structures", "Git", "Linux", "HTML", "CSS", "MongoDB",
    "REST APIs", "Pandas", "NumPy", "Excel", "PowerBI", "Figma",
]

CERT_POOL = [
    "AWS Cloud Practitioner", "AWS Solutions Architect", "Google Cloud Associate",
    "Azure Fundamentals", "ML Specialization", "Docker Essentials",
    "Scrum Master Certified", "Data Science Professional", "CCNA",
]

FIRST_NAMES = [
    "Aisha", "Rohan", "Priya", "Sameer", "Neha", "Kabir", "Ananya", "Arjun",
    "Ishita", "Vikram", "Meera", "Aditya", "Riya", "Karan", "Sneha", "Rahul",
    "Divya", "Amit", "Pooja", "Nikhil", "Tanvi", "Yash", "Kavya", "Manish",
    "Sanya", "Dev", "Ritu", "Varun", "Simran", "Harsh", "Anjali", "Suresh",
    "Tara", "Gaurav", "Nisha", "Rakesh", "Isha", "Vivek", "Payal", "Ashwin",
    "Deepika", "Manoj", "Swati", "Rajat", "Bhavna", "Siddharth", "Komal",
    "Abhishek", "Preeti", "Naveen",
]
LAST_NAMES = [
    "Khan", "Mehta", "Nair", "Iyer", "Verma", "Singh", "Sharma", "Gupta",
    "Reddy", "Das", "Chatterjee", "Joshi", "Kapoor", "Malhotra", "Rao",
    "Bose", "Kulkarni", "Chowdhury", "Patel", "Pillai",
]

COMPANIES = [
    "NimbusCloud Technologies", "ByteForge Systems", "Vertex Analytics",
    "Quantum Retail Labs", "GreenGrid Energy", "Skyline Fintech",
    "Orbit Health Systems", "Pixelworks Studio", "CoreStack Solutions",
    "Northwind Logistics",
]

ROLES = [
    "Cloud Engineer", "Full Stack Developer", "ML Engineer", "Data Analyst",
    "Backend Engineer", "DevOps Engineer", "Frontend Developer",
    "QA Automation Engineer", "Business Analyst", "Product Engineer",
]


def random_skills(k_range=(3, 6)):
    k = random.randint(*k_range)
    return random.sample(SKILL_POOL, k)


def random_certs(max_count=2):
    k = random.randint(0, max_count)
    return random.sample(CERT_POOL, k)


def generate_students(n=50):
    students = []
    used_names = set()
    for _ in range(n):
        while True:
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break
        backlogs = random.choices([0, 1, 2, 3], weights=[60, 20, 12, 8])[0]
        students.append({
            "name": name,
            "branch": random.choice(BRANCHES),
            "cgpa": round(random.uniform(5.0, 9.8), 2),
            "backlogs": backlogs,
            "skills": ",".join(random_skills()),
            "certifications": ",".join(random_certs()),
            "mock_interview_score": random.randint(30, 95),
        })
    return students


def generate_recruiters(n=10):
    recruiters = []
    for i in range(n):
        n_branches = random.randint(1, 3)
        recruiters.append({
            "company": COMPANIES[i % len(COMPANIES)],
            "role": random.choice(ROLES),
            "required_skills": ",".join(random_skills((2, 4))),
            "min_cgpa": round(random.uniform(6.0, 8.5), 1),
            "eligible_branches": ",".join(random.sample(BRANCHES, n_branches)),
        })
    return recruiters


def write_csv(rows, path, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    students = generate_students(50)
    recruiters = generate_recruiters(10)

    write_csv(
        students, "students.csv",
        ["name", "branch", "cgpa", "backlogs", "skills", "certifications", "mock_interview_score"],
    )
    write_csv(
        recruiters, "recruiters.csv",
        ["company", "role", "required_skills", "min_cgpa", "eligible_branches"],
    )

    print(f"Wrote {len(students)} students to students.csv")
    print(f"Wrote {len(recruiters)} recruiters to recruiters.csv")
