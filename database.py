import sqlite3

conn = sqlite3.connect("traffic.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate TEXT,
    type TEXT,
    time TEXT,
    image TEXT
)
""")

def add_violation(plate, vtype, image):
    cursor.execute(
        "INSERT INTO violations (plate, type, time, image) VALUES (?, ?, datetime('now'), ?)",
        (plate, vtype, image)
    )
    conn.commit()

def get_all():
    cursor.execute("SELECT * FROM violations ORDER BY id DESC")
    return cursor.fetchall()