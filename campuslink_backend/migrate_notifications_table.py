import sqlite3

create_table_sql = """
CREATE TABLE IF NOT EXISTS notifications (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_role           TEXT    NOT NULL DEFAULT 'student',
    recipient_id             INTEGER,
    recipient_name           TEXT,
    recipient_email          TEXT,
    recipient_phone          TEXT,
    category                 TEXT    NOT NULL,
    title                    TEXT    NOT NULL,
    message                  TEXT    NOT NULL,
    channels                 TEXT    NOT NULL DEFAULT '["in_app","email","whatsapp"]',
    dispatch_status          TEXT    NOT NULL DEFAULT 'Delivered',
    email_delivery_status    TEXT    NOT NULL DEFAULT 'Sent',
    whatsapp_delivery_status TEXT    NOT NULL DEFAULT 'Delivered',
    meta_data                TEXT    NOT NULL DEFAULT '{}',
    deadline_at              TEXT,
    read                     INTEGER NOT NULL DEFAULT 0,
    created_at               TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

indexes_sql = [
    "CREATE INDEX IF NOT EXISTS idx_notifications_role ON notifications(recipient_role);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_id);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_category ON notifications(category);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at);"
]

for db_path in ['campuslink_backend/campuslink.db', 'campuslink.db']:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(create_table_sql)
    for idx_sql in indexes_sql:
        cur.execute(idx_sql)
    conn.commit()
    conn.close()
    print(f"Notifications table verified in {db_path}")
