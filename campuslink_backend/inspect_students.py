import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "campuslink.db"

if not db_path.exists():
    print("Database file not found:", db_path)
else:
    connection = sqlite3.connect(str(db_path))
    cursor = connection.cursor()

    tables = [
        row[0] for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]

    print("Database found:", True)
    print("Students table exists:", "students" in tables)

    if "students" in tables:
        columns = cursor.execute(
            "PRAGMA table_info(students)"
        ).fetchall()

        print("\nStudent table columns:")
        for column in columns:
            print("-", column[1])

        count = cursor.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        print("\nStudent count:", count)

    connection.close()