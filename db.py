import sqlite3

conn = sqlite3.connect(
    "app.db",
    check_same_thread=False,
    timeout=30
)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id TEXT,
        subject_name TEXT,
        specialization TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS syllabus (
        subject_id TEXT,
        content TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id TEXT,
        question TEXT,
        options TEXT,
        correct_answer TEXT,
        explanation TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        public_test_id TEXT,
        subject_id TEXT,
        start_time TEXT,
        end_time TEXT,
        questions_json TEXT,
        allowed_emails_json TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_access (
        token TEXT,
        test_id INTEGER,
        email TEXT,
        is_used INTEGER DEFAULT 0
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER,
        student_email TEXT,
        score INTEGER,
        total INTEGER,
        answers TEXT,
        timestamp TEXT
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_results_test
    ON results(test_id)
    """)

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_submission
    ON results(test_id, student_email)
    """)

    conn.commit()

# ============================================================
# MIGRATE TESTS TABLE (RUNS ONLY ONCE)
# ============================================================

try:
    cursor.execute("""
    ALTER TABLE tests
    ADD COLUMN public_test_id TEXT
    """)
except:
    pass

try:
    cursor.execute("""
    ALTER TABLE tests
    ADD COLUMN questions_json TEXT
    """)
except:
    pass

try:
    cursor.execute("""
    ALTER TABLE tests
    ADD COLUMN allowed_emails_json TEXT
    """)
except:
    pass

cursor.execute("PRAGMA journal_mode=WAL;")

conn.commit()