import os
import bcrypt
import pytz
import streamlit as st
from sqlalchemy import create_engine, text
from datetime import datetime

# --- 1. SETUP DATABASE ENGINE (CACHED) ---
# Saya kekalkan cara cache supaya apps lebih laju
@st.cache_resource
def get_engine():
    # Guna SUPABASE_URL (pastikan di Streamlit Secrets pun sama namanya)
    db_url = st.secrets["SUPABASE_URL"]
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    return create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )

engine = get_engine()

# --- 2. TIMEZONE & SECURITY ---
def get_malaysia_time():
    tz = pytz.timezone('Asia/Kuala_Lumpur')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

# --- 3. HELPER FUNCTIONS ---
def get_radio_index(options, value):
    """Digunakan oleh form_components untuk set default radio button"""
    if value in options:
        return options.index(value)
    return 0

def delete_item(table, item_id):
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": item_id})
    st.cache_resource.clear() 
    st.toast(f"Item deleted from {table}")
    st.rerun()

# --- 4. INITIALIZE TABLES (POSTGRESQL) ---
@st.cache_resource
def init_db():
    with engine.begin() as conn:
        # Tables menggunakan TEXT supaya tak ada had limit karakter
        conn.execute(text("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, full_name TEXT, role TEXT, password_hash TEXT)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS reviewers (id SERIAL PRIMARY KEY, username TEXT UNIQUE, full_name TEXT, password_hash TEXT)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS applicants (id SERIAL PRIMARY KEY, name TEXT UNIQUE, proposal_title TEXT, institution TEXT, info_link TEXT, remarks TEXT, photo BYTEA)"))
        
        # Phase 1
        conn.execute(text("CREATE TABLE IF NOT EXISTS applicant_assignments (id SERIAL PRIMARY KEY, applicant_name TEXT, reviewer_username TEXT, UNIQUE(applicant_name, reviewer_username))"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS reviews (id SERIAL PRIMARY KEY, reviewer_username TEXT, applicant_name TEXT, responses TEXT, final_recommendation TEXT, overall_justification TEXT, is_final BOOLEAN DEFAULT FALSE, submitted_at TEXT, updated_at TEXT, UNIQUE(reviewer_username, applicant_name))"))

        # Phase 2 (Pemarkahan 1-10)
        conn.execute(text("CREATE TABLE IF NOT EXISTS phase2_assignments (id SERIAL PRIMARY KEY, applicant_name TEXT, reviewer_username TEXT, UNIQUE(applicant_name, reviewer_username))"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS phase2_reviews (id SERIAL PRIMARY KEY, reviewer_username TEXT, applicant_name TEXT, responses TEXT, final_recommendation TEXT, overall_justification TEXT, is_final BOOLEAN DEFAULT FALSE, submitted_at TEXT, updated_at TEXT, UNIQUE(reviewer_username, applicant_name))"))

        # Create Admin asal
        res = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
        if res == 0:
            pw = hash_password("admin123")
            conn.execute(text("INSERT INTO users (username, full_name, role, password_hash) VALUES ('admin', 'System Admin', 'Admin', :p)"), {"p": pw})
    return True
