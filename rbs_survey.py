import streamlit as st
import extra_streamlit_components as stx
import json
import time
from datetime import datetime, timedelta
from sqlalchemy import text

# Import utiliti
from database_utils import get_engine, init_db, check_password, hash_password, get_malaysia_time, delete_item
from form_components import render_evaluation_fields, render_scoring_fields
from admin_logic import render_dashboard, render_management
from reviewer_logic import render_review_form
from reporting_logic import render_reporting 

# --- 1. SET PAGE CONFIG (WAJIB PALING ATAS) ---
st.set_page_config(page_title="RBS Grant System", layout="wide")

# --- 2. ENGINE & DB INIT (TURBO CACHE) ---
engine = get_engine()

@st.cache_resource
def startup_sequence():
    init_db() # Run sekali je masa apps mula
    return True

startup_sequence()

# --- 3. SESSION & COOKIE MANAGER ---
if 'cookie_manager' not in st.session_state:
    st.session_state.cookie_manager = stx.CookieManager(key="rbs_mgr")
cookie_manager = st.session_state.cookie_manager

# --- 4. PERSISTENCE LOGIC (PUNCA LOGOUT FIX) ---
def sync_auth():
    # A. Jika sedang dalam proses logout, jangan buat apa-apa
    if st.session_state.get('logout_in_progress'):
        return False

    # B. Check Session State (Paling laju)
    if st.session_state.get('authenticated'):
        return True

    # C. Check URL Params (Sangat laju - Fix refresh issue)
    params = st.query_params
    if "u" in params and "r" in params:
        st.session_state.update({
            "authenticated": True,
            "username": params["u"],
            "role": params["r"],
            "full_name": params.get("n", params["u"])
        })
        return True

    # D. Check Cookies (Backup)
    val = cookie_manager.get('rbs_session')
    if val:
        try:
            if isinstance(val, str): val = json.loads(val)
            st.session_state.update({
                "authenticated": True,
                "username": val['u'], "role": val['r'], "full_name": val['n']
            })
            st.query_params.update({"u": val['u'], "r": val['r'], "n": val['n']})
            return True
        except: pass
    
    return False

# Jalankan sync_auth
is_auth = sync_auth()

# --- 5. LOGIN INTERFACE ---
if not is_auth:
    st.title("🔐 RBS Login")
    with st.form("login_form"):
        login_role = st.radio("Log in as:", ["Reviewer", "Admin"], horizontal=True)
        u_input = st.text_input("Username").strip()
        p_input = st.text_input("Password", type="password")
        
        if st.form_submit_button("Login", use_container_width=True):
            with engine.connect() as conn:
                tbl = "users" if login_role == "Admin" else "reviewers"
                res = conn.execute(text(f"SELECT password_hash, full_name FROM {tbl} WHERE username = :u"), {"u": u_input}).fetchone()

                if res and check_password(p_input, res[0]):
                    role = "Admin" if login_role == "Admin" else "Reviewer"
                    # 1. Update Session
                    st.session_state.update({"authenticated": True, "username": u_input, "role": role, "full_name": res[1]})
                    # 2. Update URL Params (Untuk Speed Refresh)
                    st.query_params.update({"u": u_input, "r": role, "n": res[1]})
                    # 3. Update Cookies (Untuk Long-term)
                    cookie_manager.set('rbs_session', json.dumps({"u": u_input, "r": role, "n": res[1]}), expires_at=datetime.now() + timedelta(days=1))
                    
                    st.success("Login success!"); time.sleep(0.5); st.rerun()
                else:
                    st.error("Invalid credentials.")
    st.stop()

# --- 6. SIDEBAR & NAVIGATION ---
with st.sidebar:
    st.title(f"👤 {st.session_state.get('full_name')}")
    st.caption(f"Role: {st.session_state.get('role')}")

    if st.session_state.role == "Admin":
        menu = st.radio("Navigation", ["Dashboard", "Reporting", "Phase 1 Management", "Phase 2 Management", "Reviewer Management"])
    else:
        menu = st.radio("Navigation", ["Phase 1: Shortlisting", "Phase 2: Winner Selection"])

    st.divider()
    if st.button("Logout", type="primary", use_container_width=True):
        cookie_manager.delete('rbs_session')
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

# --- 7. MODULE ROUTING ---
# Guna engine sedia ada (connection pool)
if menu == "Dashboard": render_dashboard(engine)
elif menu == "Reporting": render_reporting(engine)
elif menu in ["Reviewer Management", "Phase 1 Management", "Phase 2 Management"]: 
    render_management(menu, engine, hash_password, delete_item)
elif "Phase" in menu:
    p_num = 1 if "Phase 1" in menu else 2
    render_review_form(engine, get_malaysia_time, p_num, render_evaluation_fields, render_scoring_fields)
