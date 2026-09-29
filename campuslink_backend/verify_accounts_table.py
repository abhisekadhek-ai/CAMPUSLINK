import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "campuslink.db"

if not db_path.exists():
    print("ERROR: Database file not found:", db_path)
else:
    connection = sqlite3.connect(str(db_path))
    cursor = connection.cursor()

    tables = {
        row[0]
        for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    print("Database:", db_path)
    print("Students table exists:", "students" in tables)
    print("User accounts table exists:", "user_accounts" in tables)

    if "students" in tables:
        count = cursor.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]
        print("Student count:", count)

    if "user_accounts" in tables:
        count = cursor.execute(
            "SELECT COUNT(*) FROM user_accounts"
        ).fetchone()[0]
        print("User accounts count:", count)

    connection.close()