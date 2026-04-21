import os
from sqlalchemy import create_engine, text
import bcrypt
from datetime import datetime
import pytz

# --- 1. SETUP DATABASE ENGINE ---
db_path = "rbs_database.db"
engine = create_engine(f"sqlite:///{db_path}")

# --- 2. TIMEZONE CONFIGURATION ---
def get_malaysia_time():
    tz = pytz.timezone('Asia/Kuala_Lumpur')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# --- 3. PASSWORD HASHING ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# --- 4. INITIALIZE TABLES ---
def init_db():
    with engine.begin() as conn:
        # Table 1: Admins (Users)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL
            )
        """))
        
        # Table 2: Reviewers
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reviewers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL
            )
        """))

        # Table 3: Applicants
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS applicants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                proposal_title TEXT NOT NULL,
                institution TEXT,
                info_link TEXT,
                remarks TEXT,
                photo BLOB
            )
        """))

        # Table 4: Phase 1 Assignments (Shortlisting)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS applicant_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                applicant_name TEXT NOT NULL,
                reviewer_username TEXT NOT NULL,
                UNIQUE(applicant_name, reviewer_username)
            )
        """))

        # Table 5: Phase 1 Reviews
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_username TEXT NOT NULL,
                applicant_name TEXT NOT NULL,
                responses TEXT,
                final_recommendation TEXT,
                overall_justification TEXT,
                is_final BOOLEAN DEFAULT FALSE,
                submitted_at TEXT,
                updated_at TEXT,
                UNIQUE(reviewer_username, applicant_name)
            )
        """))

        # --- BAHARU: JADUAL UNTUK FASA 2 ---
        
        # Table 6: Phase 2 Assignments (Winner Selection)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS phase2_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                applicant_name TEXT NOT NULL,
                reviewer_username TEXT NOT NULL,
                UNIQUE(applicant_name, reviewer_username)
            )
        """))

        # Table 7: Phase 2 Reviews (Pemarkahan 1-10)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS phase2_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_username TEXT NOT NULL,
                applicant_name TEXT NOT NULL,
                responses TEXT,
                final_recommendation TEXT,
                overall_justification TEXT,
                is_final BOOLEAN DEFAULT FALSE,
                submitted_at TEXT,
                updated_at TEXT,
                UNIQUE(reviewer_username, applicant_name)
            )
        """))

        # Create default admin if not exists
        check_admin = conn.execute(text("SELECT * FROM users WHERE username = 'admin'")).fetchone()
        if not check_admin:
            default_hash = hash_password("admin123")
            conn.execute(text("""
                INSERT INTO users (username, full_name, role, password_hash) 
                VALUES ('admin', 'System Administrator', 'Admin', :h)
            """), {"h": default_hash})

# --- 5. DELETE HELPER ---
def delete_item(table, item_id):
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": item_id})
