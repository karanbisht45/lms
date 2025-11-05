import sqlite3
from datetime import datetime
import os

# ---------------- DATABASE CONNECTION -----------------
DB_PATH = "lms.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# ---------------- CREATE FOLDERS FOR FILES -----------------
UPLOAD_DIRS = ["uploads/assignments", "uploads/notes", "uploads/exams"]
for d in UPLOAD_DIRS:
    os.makedirs(d, exist_ok=True)

# ---------------- SAFE MIGRATION HELPERS -----------------
def try_alter(table, sql):
    try:
        c.execute(sql)
        conn.commit()
    except Exception:
        pass

# ---------------- CREATE / MIGRATE TABLES -----------------
def create_tables_and_migrate():
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    role TEXT CHECK(role IN ('Student','Teacher'))
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    teacher_id INTEGER,
                    FOREIGN KEY (teacher_id) REFERENCES users(id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS enrollments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    course_id INTEGER,
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )''')

    # Assignments (with PDF path)
    c.execute('''CREATE TABLE IF NOT EXISTS assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER,
                    title TEXT,
                    file_path TEXT,
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )''')
    try_alter("assignments", "ALTER TABLE assignments ADD COLUMN file_path TEXT")

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

    # Notes (PDF support)
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER,
                    file_path TEXT,
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )''')
    try_alter("notes", "ALTER TABLE notes ADD COLUMN file_path TEXT")

    # Exams (PDF support)
    c.execute('''CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER,
                    title TEXT,
                    file_path TEXT,
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )''')
    try_alter("exams", "ALTER TABLE exams ADD COLUMN file_path TEXT")

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

    # Points/leaderboard
    c.execute('''CREATE TABLE IF NOT EXISTS points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER UNIQUE,
                    points INTEGER DEFAULT 0,
                    FOREIGN KEY (student_id) REFERENCES users(id)
                )''')

    conn.commit()

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

# ---------------- COURSE FUNCTIONS -----------------
def add_course(name, teacher_id):
    c.execute("INSERT INTO courses (name, teacher_id) VALUES (?, ?)", (name, teacher_id))
    conn.commit()

def get_courses():
    c.execute("SELECT id, name, teacher_id FROM courses")
    return c.fetchall()

def get_enrolled_courses(student_id):
    c.execute('''SELECT c.id, c.name
                 FROM courses c
                 JOIN enrollments e ON c.id = e.course_id
                 WHERE e.student_id = ?''', (student_id,))
    return c.fetchall()

def enroll_course(student_id, course_id):
    c.execute("SELECT id FROM enrollments WHERE student_id=? AND course_id=?", (student_id, course_id))
    if c.fetchone():
        return False
    c.execute("INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)", (student_id, course_id))
    conn.commit()
    return True

def count_enrolled_students(course_id):
    c.execute("SELECT COUNT(*) FROM enrollments WHERE course_id=?", (course_id,))
    return c.fetchone()[0]

def get_enrolled_students(course_id):
    c.execute("""
        SELECT u.id, u.username
        FROM users u
        JOIN enrollments e ON e.student_id = u.id
        WHERE e.course_id = ?
    """, (course_id,))
    return c.fetchall()

# ---------------- ASSIGNMENT FUNCTIONS (PDF) -----------------
def add_assignment(course_id, title, uploaded_file):
    file_path = f"uploads/assignments/{title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    c.execute("INSERT INTO assignments (course_id, title, file_path) VALUES (?, ?, ?)",
              (course_id, title, file_path))
    conn.commit()

def get_assignments(course_id):
    c.execute("SELECT id, title, file_path FROM assignments WHERE course_id=?", (course_id,))
    return c.fetchall()

# ---------------- NOTES FUNCTIONS (PDF) -----------------
def upload_note(course_id, uploaded_file):
    file_path = f"uploads/notes/note_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    c.execute("INSERT INTO notes (course_id, file_path) VALUES (?, ?)", (course_id, file_path))
    conn.commit()

def get_notes(course_id):
    c.execute("SELECT id, file_path FROM notes WHERE course_id=?", (course_id,))
    return c.fetchall()

# ---------------- EXAM FUNCTIONS (PDF) -----------------
def create_exam(course_id, title, uploaded_file):
    file_path = f"uploads/exams/{title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    c.execute("INSERT INTO exams (course_id, title, file_path) VALUES (?, ?, ?)",
              (course_id, title, file_path))
    conn.commit()

def get_exams(course_id):
    c.execute("SELECT id, title, file_path FROM exams WHERE course_id=?", (course_id,))
    return c.fetchall()

# ---------------- SUBMISSIONS & PERFORMANCE -----------------
def submit_assignment(student_id, assignment_id, answer):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT id FROM submissions WHERE student_id=? AND assignment_id=?", (student_id, assignment_id))
    row = c.fetchone()
    if row:
        c.execute("UPDATE submissions SET answer=?, submission_date=? WHERE id=?",
                  (answer, date, row[0]))
    else:
        c.execute("""INSERT INTO submissions (student_id, assignment_id, answer, submission_date)
                     VALUES (?, ?, ?, ?)""", (student_id, assignment_id, answer, date))
    conn.commit()
    # TODO: Send email to teacher (Phase 2)

def submit_exam(student_id, exam_id, answer):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT id FROM exam_submissions WHERE student_id=? AND exam_id=?", (student_id, exam_id))
    row = c.fetchone()
    if row:
        c.execute("UPDATE exam_submissions SET answer=?, submission_date=? WHERE id=?",
                  (answer, date, row[0]))
    else:
        c.execute("""INSERT INTO exam_submissions (student_id, exam_id, answer, submission_date)
                     VALUES (?, ?, ?, ?)""", (student_id, exam_id, answer, date))
    conn.commit()
    # TODO: Send email notification (Phase 2)

# ---------------- TEACHER ANALYTICS -----------------
def get_teacher_student_performance(course_id):
    """
    Return detailed performance of all students in a course.
    Columns: Student Name, Assignments Submitted, Assignment Titles, Exams Attempted, Exam Titles
    """
    students = get_enrolled_students(course_id)
    data = []
    for sid, name in students:
        c.execute("""SELECT a.title FROM assignments a
                     JOIN submissions s ON a.id = s.assignment_id
                     WHERE s.student_id=? AND a.course_id=?""", (sid, course_id))
        assignments_done = c.fetchall()
        assignment_titles = ", ".join([a[0] for a in assignments_done]) if assignments_done else "None"

        c.execute("""SELECT e.title FROM exams e
                     JOIN exam_submissions s ON e.id = s.exam_id
                     WHERE s.student_id=? AND e.course_id=?""", (sid, course_id))
        exams_done = c.fetchall()
        exam_titles = ", ".join([e[0] for e in exams_done]) if exams_done else "None"

        data.append({
            "Student Name": name,
            "Assignments Submitted": len(assignments_done),
            "Assignment Titles": assignment_titles,
            "Exams Attempted": len(exams_done),
            "Exam Titles": exam_titles
        })
    return data
