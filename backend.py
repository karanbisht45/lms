import sqlite3
from datetime import datetime

# ---------------- DATABASE CONNECTION -----------------
conn = sqlite3.connect("lms.db", check_same_thread=False)
c = conn.cursor()

# ---------------- SAFE MIGRATION HELPERS -----------------
def try_alter(table, sql):
    """Try to run ALTER; ignore failures (e.g., column exists)."""
    try:
        c.execute(sql)
        conn.commit()
    except Exception:
        pass  

# ---------------- CREATE / MIGRATE TABLES -----------------
def create_tables_and_migrate():
    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    role TEXT CHECK(role IN ('Student','Teacher'))
                )''')

    # Courses
    c.execute('''CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    teacher_id INTEGER,
                    FOREIGN KEY (teacher_id) REFERENCES users(id)
                )''')

    # Enrollments
    c.execute('''CREATE TABLE IF NOT EXISTS enrollments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    course_id INTEGER,
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )''')

    # Assignments
    c.execute('''CREATE TABLE IF NOT EXISTS assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER,
                    title TEXT,
                    description TEXT,
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )''')
    # If an older assignments table lacked description, try to add it
    try_alter('assignments', "ALTER TABLE assignments ADD COLUMN description TEXT")

    # Submissions (students' assignment answers)
    c.execute('''CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    assignment_id INTEGER,
                    answer TEXT,
                    submission_date TEXT,
                    grade INTEGER,
                    feedback TEXT,
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (assignment_id) REFERENCES assignments(id)
                )''')
    # Add grade/feedback columns if missing
    try_alter('submissions', "ALTER TABLE submissions ADD COLUMN grade INTEGER")
    try_alter('submissions', "ALTER TABLE submissions ADD COLUMN feedback TEXT")

    # Notes
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER,
                    content TEXT,
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )''')

    # Exams
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER,
                    title TEXT,
                    content TEXT,
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )''')

    # Exam submissions
    c.execute('''CREATE TABLE IF NOT EXISTS exam_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    exam_id INTEGER,
                    answer TEXT,
                    submission_date TEXT,
                    grade INTEGER,
                    feedback TEXT,
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (exam_id) REFERENCES exams(id)
                )''')
    try_alter('exam_submissions', "ALTER TABLE exam_submissions ADD COLUMN grade INTEGER")
    try_alter('exam_submissions', "ALTER TABLE exam_submissions ADD COLUMN feedback TEXT")

    # Points/leaderboard
    c.execute('''CREATE TABLE IF NOT EXISTS points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER UNIQUE,
                    points INTEGER DEFAULT 0,
                    FOREIGN KEY (student_id) REFERENCES users(id)
                )''')

    conn.commit()

# Run create / migration at import time
create_tables_and_migrate()

# ---------------- USER FUNCTIONS -----------------
def signup(username, password, role):
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  (username, password, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login(username, password, role):
    c.execute("SELECT id FROM users WHERE username=? AND password=? AND role=?",
              (username, password, role))
    return c.fetchone()

def get_all_users():
    c.execute("SELECT id, username, role FROM users")
    return c.fetchall()

# ---------------- COURSE FUNCTIONS -----------------
def add_course(name, teacher_id):
    c.execute("INSERT INTO courses (name, teacher_id) VALUES (?, ?)", (name, teacher_id))
    conn.commit()

def get_courses():
    c.execute("SELECT id, name, teacher_id FROM courses")
    return c.fetchall()

def enroll_course(student_id, course_id):
    
    c.execute("SELECT id FROM enrollments WHERE student_id=? AND course_id=?", (student_id, course_id))
    if c.fetchone():
        return False
    c.execute("INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)", (student_id, course_id))
    conn.commit()
    return True

def get_enrolled_courses(student_id):
    c.execute('''SELECT c.id, c.name
                 FROM courses c
                 JOIN enrollments e ON c.id = e.course_id
                 WHERE e.student_id = ?''', (student_id,))
    return c.fetchall()

def count_enrolled_students(course_id):
    c.execute("SELECT COUNT(*) FROM enrollments WHERE course_id=?", (course_id,))
    return c.fetchone()[0]

# ---------------- ASSIGNMENT FUNCTIONS -----------------
def add_assignment(course_id, title, description):
    """Teacher creates an assignment (title + content/description)."""
    c.execute("INSERT INTO assignments (course_id, title, description) VALUES (?, ?, ?)",
              (course_id, title, description))
    conn.commit()

def get_assignments(course_id):
    """Return list of tuples (id, title, description) — used by student display."""
    c.execute("SELECT id, title, description FROM assignments WHERE course_id=?", (course_id,))
    return c.fetchall()

def submit_assignment(student_id, assignment_id, answer):
    """Student submits an answer (text)."""
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT id FROM submissions WHERE student_id=? AND assignment_id=?", (student_id, assignment_id))
    row = c.fetchone()
    if row:
        c.execute("""UPDATE submissions
                     SET answer=?, submission_date=?
                     WHERE id=?""", (answer, date, row[0]))
    else:
        c.execute("""INSERT INTO submissions (student_id, assignment_id, answer, submission_date)
                     VALUES (?, ?, ?, ?)""", (student_id, assignment_id, answer, date))
    conn.commit()

def get_submissions_for_assignment(assignment_id):
    """
    Return list of (submission_id, student_id, username, answer, submission_date, grade, feedback)
    for a given assignment — teacher view.
    """
    c.execute("""
        SELECT s.id, s.student_id, u.username, s.answer, s.submission_date, s.grade, s.feedback
        FROM submissions s
        JOIN users u ON s.student_id = u.id
        WHERE s.assignment_id = ?
        ORDER BY s.submission_date DESC
    """, (assignment_id,))
    return c.fetchall()

def grade_submission(submission_id, grade, feedback=None):
    """Teacher grades a submission and optionally writes feedback."""
    c.execute("UPDATE submissions SET grade=?, feedback=? WHERE id=?", (grade, feedback, submission_id))
    conn.commit()

def count_assignments(course_id):
    c.execute("SELECT COUNT(*) FROM assignments WHERE course_id=?", (course_id,))
    return c.fetchone()[0]

def count_user_assignments(student_id):
    """How many assignment submissions the student has made (used in student dashboard)."""
    c.execute("SELECT COUNT(*) FROM submissions WHERE student_id=?", (student_id,))
    return c.fetchone()[0]

# ---------------- NOTES FUNCTIONS -----------------
def upload_note(course_id, content):
    c.execute("INSERT INTO notes (course_id, content) VALUES (?, ?)", (course_id, content))
    conn.commit()

def get_notes(course_id):
    c.execute("SELECT id, content FROM notes WHERE course_id=?", (course_id,))
    return c.fetchall()

# ---------------- EXAM FUNCTIONS -----------------
def create_exam(course_id, title, content):
    c.execute("INSERT INTO exams (course_id, title, content) VALUES (?, ?, ?)",
              (course_id, title, content))
    conn.commit()

def get_exams(course_id):
    c.execute("SELECT id, title, content FROM exams WHERE course_id=?", (course_id,))
    return c.fetchall()

def submit_exam(student_id, exam_id, answer):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT id FROM exam_submissions WHERE student_id=? AND exam_id=?", (student_id, exam_id))
    row = c.fetchone()
    if row:
        c.execute("UPDATE exam_submissions SET answer=?, submission_date=? WHERE id=?", (answer, date, row[0]))
    else:
        c.execute("""INSERT INTO exam_submissions (student_id, exam_id, answer, submission_date)
                     VALUES (?, ?, ?, ?)""", (student_id, exam_id, answer, date))
    conn.commit()

def get_submissions_for_exam(exam_id):
    c.execute("""
        SELECT s.id, s.student_id, u.username, s.answer, s.submission_date, s.grade, s.feedback
        FROM exam_submissions s
        JOIN users u ON s.student_id = u.id
        WHERE s.exam_id = ?
        ORDER BY s.submission_date DESC
    """, (exam_id,))
    return c.fetchall()

def grade_exam_submission(submission_id, grade, feedback=None):
    c.execute("UPDATE exam_submissions SET grade=?, feedback=? WHERE id=?", (grade, feedback, submission_id))
    conn.commit()

def count_user_exams(student_id):
    c.execute("SELECT COUNT(*) FROM exam_submissions WHERE student_id=?", (student_id,))
    return c.fetchone()[0]

# ---------------- POINTS / LEADERBOARD -----------------
def add_points(student_id, points):
    """Add points (create row if missing)."""
    c.execute("SELECT points FROM points WHERE student_id=?", (student_id,))
    row = c.fetchone()
    if row:
        new_total = row[0] + points
        c.execute("UPDATE points SET points=? WHERE student_id=?", (new_total, student_id))
    else:
        c.execute("INSERT INTO points (student_id, points) VALUES (?, ?)", (student_id, points))
    conn.commit()

def get_user_points(student_id):
    c.execute("SELECT points FROM points WHERE student_id=?", (student_id,))
    row = c.fetchone()
    return row[0] if row else 0

def get_leaderboard():
    c.execute('''SELECT u.username, p.points
                 FROM users u
                 JOIN points p ON u.id = p.student_id
                 ORDER BY p.points DESC''')
    return c.fetchall()

# ---------------- ANALYTICS / PROGRESS -----------------
def get_course_progress(student_id):
    """
    Returns list of (course_name, completion_percent).
    If a course has zero assignments progress = 0.0.
    """
    c.execute('''
        SELECT
            c.name,
            CASE
                WHEN (SELECT COUNT(*) FROM assignments a WHERE a.course_id = c.id) = 0 THEN 0.0
                ELSE (CAST(COALESCE(sub.count_submissions,0) AS FLOAT) * 100.0) /
                     (SELECT COUNT(*) FROM assignments a WHERE a.course_id = c.id)
            END AS progress
        FROM courses c
        JOIN enrollments e ON c.id = e.course_id
        LEFT JOIN (
            SELECT a.course_id, COUNT(s.id) AS count_submissions
            FROM assignments a
            LEFT JOIN submissions s ON a.id = s.assignment_id AND s.student_id = ?
            GROUP BY a.course_id
        ) sub ON sub.course_id = c.id
        WHERE e.student_id = ?
    ''', (student_id, student_id))
    return c.fetchall()

# ---------------- TEACHER HELPERS -----------------
def fetch_assignments_by_teacher(teacher_id):
    """Return (id,title,description,course_id) for teacher-created assignments."""
    c.execute("""
        SELECT a.id, a.title, a.description, a.course_id
        FROM assignments a
        JOIN courses c ON a.course_id = c.id
        WHERE c.teacher_id = ?
    """, (teacher_id,))
    return c.fetchall()

def fetch_exams_by_teacher(teacher_id):
    c.execute("""
        SELECT e.id, e.title, e.content, e.course_id
        FROM exams e
        JOIN courses c ON e.course_id = c.id
        WHERE c.teacher_id = ?
    """, (teacher_id,))
    return c.fetchall()


