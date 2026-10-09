import sqlite3

copy_sql = "SELECT id, recipient_role, recipient_id, recipient_name, recipient_email, recipient_phone, category, title, message, channels, dispatch_status, email_delivery_status, whatsapp_delivery_status, meta_data, deadline_at, read, created_at FROM notifications"

# Check root campuslink.db
conn_root = sqlite3.connect('campuslink.db')
rows_root = conn_root.cursor().execute(copy_sql).fetchall()
conn_root.close()

# Check backend campuslink.db
conn_backend = sqlite3.connect('campuslink_backend/campuslink.db')
rows_backend = conn_backend.cursor().execute(copy_sql).fetchall()

source_rows = rows_root if len(rows_root) > len(rows_backend) else rows_backend

# Sync to both
for path in ['campuslink.db', 'campuslink_backend/campuslink.db']:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    for r in source_rows:
        cur.execute("""
            INSERT OR REPLACE INTO notifications (
                id, recipient_role, recipient_id, recipient_name, recipient_email, recipient_phone,
                category, title, message, channels, dispatch_status, email_delivery_status,
                whatsapp_delivery_status, meta_data, deadline_at, read, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, r)
    conn.commit()
    conn.close()

print(f"Synced {len(source_rows)} notifications to both databases.")
