# auth.py
import sqlite3

DB_PATH = "lms.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# ---------- MIGRATE USERS TABLE ----------
def migrate_users_table():
    """
    Ensure that the users table has an email column.
    """
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT CHECK(role IN ('Student','Teacher'))
        )
    """)
    try:
        c.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except Exception:
        pass
    conn.commit()

migrate_users_table()

# ---------- AUTH FUNCTIONS ----------
def signup_user(username, email, password, role):
    try:
        c.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                  (username, email, password, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_login(email, password, role):
    """
    Return (id, username, role) if credentials are valid, else None.
    """
    c.execute("SELECT id, username, role FROM users WHERE email=? AND password=? AND role=?",
              (email, password, role))
    return c.fetchone()
