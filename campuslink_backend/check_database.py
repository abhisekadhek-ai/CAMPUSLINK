import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "campuslink.db"

print("Database file:", db_path)
print("File exists:", db_path.exists())

if db_path.exists():
    connection = sqlite3.connect(str(db_path))
    cursor = connection.cursor()

    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    print("Tables:", tables)

    if ("students",) in tables:
        count = cursor.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]
        print("Student count:", count)
    else:
        print("No students table found in this database.")

    connection.close()