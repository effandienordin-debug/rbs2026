import streamlit as st
import extra_streamlit_components as stx
import json
import time
from datetime import datetime, timedelta
from sqlalchemy import text

# Import utiliti dari fail lain
from database_utils import get_engine, init_db, check_password, hash_password, get_malaysia_time, delete_item
from form_components import render_evaluation_fields, render_scoring_fields
from admin_logic import render_dashboard, render_management
from reviewer_logic import render_review_form
from reporting_logic import render_reporting 

# --- 1. PAGE CONFIG (Mesti paling atas) ---
st.set_page_config(page_title="RBS Grant System", layout="wide")

# --- 2. ENGINE & DB INIT (Cached) ---
# Kita panggil engine sekali je, tak payah buat banyak kali
engine = get_engine()

@st.cache_resource
def startup_db():
    init_db() # Run sekali je masa apps mula-mula start
    return True

startup_db()

# --- 3. PERSISTENT LOGIN (Cookie & Session) ---
if 'cookie_manager' not in st.session_state:
    st.session_state.cookie_manager = stx.CookieManager(key="rbs_mgr")

cookie_manager = st.session_state.cookie_manager

def handle_persistence():
    # Kalau session dah ada, tak payah buat apa-apa
    if st.session_state.get('authenticated'):
        return

    # Check kuki secara senyap
    session_data = cookie_manager.get('rbs_session_data')
    if session_data:
        try:
            if isinstance(session_data, str):
                session_data = json.loads(session_data)
            
            st.session_state.update({
                "authenticated": True,
                "username": session_data.get('username'),
                "role": session_data.get('role'),
                "full_name": session_data.get('full_name')
            })
        except:
            pass

handle_persistence()

# --- 4. LOGIN INTERFACE ---
if not st.session_state.get('authenticated'):
    st.title("🔐 RBS Login")
    with st.form("login_form"):
        login_role = st.radio("Log in as:", ["Reviewer", "Admin"], horizontal=True)
        u = st.text_input("Username").strip()
        p = st.text_input("Password", type="password")
        
        if st.form_submit_button("Login", use_container_width=True):
            with engine.connect() as conn:
                # Query laju: hanya ambil apa yang perlu
                tbl = "users" if login_role == "Admin" else "reviewers"
                query = text(f"SELECT password_hash, full_name FROM {tbl} WHERE username = :u")
                res = conn.execute(query, {"u": u}).fetchone()

                if res and check_password(p, res[0]):
                    role = "Admin" if login_role == "Admin" else "Reviewer"
                    # Simpan dalam session
                    st.session_state.update({
                        "authenticated": True, 
                        "username": u, 
                        "role": role, 
                        "full_name": res[1]
                    })
                    # Simpan dalam kuki (Tahan 1 hari)
                    cookie_data = {"username": u, "role": role, "full_name": res[1]}
                    cookie_manager.set(
                        'rbs_session_data', 
                        json.dumps(cookie_data), 
                        expires_at=datetime.now() + timedelta(days=1)
                    )
                    st.success(f"Welcome {res[1]}!"); time.sleep(0.5); st.rerun()
                else:
                    st.error("Invalid credentials.")
    st.stop()

# --- 5. SIDEBAR & NAVIGATION ---
with st.sidebar:
    st.title(f"👤 {st.session_state.full_name}")
    st.caption(f"Logged in as: {st.session_state.role}")

    if st.session_state.role == "Admin":
        menu = st.radio("Navigation", ["Dashboard", "Reporting", "Phase 1 Management", "Phase 2 Management", "Reviewer Management"])
    else:
        menu = st.radio("Navigation", ["Phase 1: Shortlisting", "Phase 2: Winner Selection"])

    st.divider()
    if st.button("Logout", use_container_width=True, type="primary"):
        cookie_manager.delete('rbs_session_data')
        st.session_state.clear()
        time.sleep(0.2)
        st.rerun()

# --- 6. ROUTING (Laju sebab data dah di-cache dalam sub-modul) ---
if menu == "Dashboard":
    render_dashboard(engine)
elif menu == "Reporting":
    render_reporting(engine)
elif menu in ["Reviewer Management", "Phase 1 Management", "Phase 2 Management"]:
    render_management(menu, engine, hash_password, delete_item)
elif "Phase" in menu:
    phase_num = 1 if "Phase 1" in menu else 2
    render_review_form(engine, get_malaysia_time, phase_num, render_evaluation_fields, render_scoring_fields)
