import streamlit as st
import pandas as pd
import os
import time
import base64
import json
from sqlalchemy import text

# --- 1. SETUP & UTILS ---
PHOTO_DIR = "evaluator_photos"
os.makedirs(PHOTO_DIR, exist_ok=True)

def get_local_image_base64(username):
    file_path = os.path.join(PHOTO_DIR, f"{username.replace(' ', '_')}.png")
    if os.path.exists(file_path):
        with open(file_path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{b64}"
    return "https://cdn-icons-png.flaticon.com/512/149/149071.png"

# --- 2. DIALOGS (EDIT & BULK) ---
@st.dialog("📝 Edit Applicant")
def edit_applicant_dialog(engine, app_data):
    with st.form("edit_app_form"):
        new_name = st.text_input("Full Name", value=app_data['name'])
        new_title = st.text_input("Proposal Title", value=app_data['proposal_title'])
        new_inst = st.text_input("Institution", value=app_data['institution'])
        new_link = st.text_input("Info Link", value=app_data['info_link'])
        new_rem = st.text_area("Admin Remarks", value=app_data['remarks'])
        
        if st.form_submit_button("Update Details", type="primary"):
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE applicants SET name=:n, proposal_title=:t, institution=:i, info_link=:l, remarks=:r 
                    WHERE id=:id
                """), {"n":new_name, "t":new_title, "i":new_inst, "l":new_link, "r":new_rem, "id":app_data['id']})
            st.success("✅ Applicant details updated!"); time.sleep(1); st.rerun()

@st.dialog("📚 Bulk Add Applicants")
def bulk_add_applicants_dialog(engine):
    st.markdown("**Format:** `Name, Proposal Title, Institution, Info Link, Remarks` (One per line)")
    raw_data = st.text_area("Paste Applicant List Here", height=200)
    if st.button("Import Applicants", type="primary"):
        if not raw_data.strip():
            st.error("🚨 Please enter data.")
            return
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        count = 0
        with engine.begin() as conn:
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    conn.execute(text("""
                        INSERT INTO applicants (name, proposal_title, institution, info_link, remarks) 
                        VALUES (:n, :t, :i, :l, :r) ON CONFLICT (name) DO NOTHING
                    """), {
                        "n": parts[0], 
                        "t": parts[1], 
                        "i": parts[2] if len(parts)>2 else "", 
                        "l": parts[3] if len(parts)>3 else "", 
                        "r": parts[4] if len(parts)>4 else ""
                    })
                    count += 1
        st.cache_resource.clear(); st.success(f"✅ Imported {count} applicants!"); time.sleep(1); st.rerun()

@st.dialog("📚 Bulk Add Reviewers")
def bulk_add_reviewers_dialog(engine, hash_password):
    st.markdown("**Format:** `Full Name, Username, Password` (One per line)")
    raw_data = st.text_area("Paste Reviewer List Here", height=200)
    if st.button("Import Reviewers", type="primary"):
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        count = 0
        with engine.begin() as conn:
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    conn.execute(text("INSERT INTO reviewers (username, full_name, password_hash) VALUES (:u, :n, :p) ON CONFLICT (username) DO NOTHING"), {"u":parts[1], "n":parts[0], "p":hash_password(parts[2])})
                    count += 1
        st.cache_resource.clear(); st.success(f"✅ Imported {count} reviewers!"); time.sleep(1); st.rerun()

# --- 3. RENDER DASHBOARD ---
def render_dashboard(engine):
    st.header("📊 Live Evaluation Tracker")
    if st.button("🔄 Sync Dashboard Data"): st.cache_resource.clear(); st.rerun()
    
    revs_df = pd.read_sql("SELECT username, full_name FROM reviewers", engine)
    
    # --- PHASE 1 STATUS ---
    st.subheader("📋 Phase 1: Shortlisting Status")
    reviews_p1 = pd.read_sql("SELECT reviewer_username FROM reviews", engine)
    assign_p1 = pd.read_sql("SELECT reviewer_username FROM applicant_assignments", engine)
    
    if revs_df.empty:
        st.info("No reviewers registered yet.")
    else:
        cols = st.columns(4)
        for i, row in revs_df.iterrows():
            u, f = row['username'], row['full_name']
            # Kira guna case-insensitive untuk elak ralat casing
            assigned = len(assign_p1[assign_p1['reviewer_username'].str.lower() == u.lower()])
            done = len(reviews_p1[reviews_p1['reviewer_username'].str.lower() == u.lower()])
            bg = "#E6FFFA" if (done >= assigned and assigned > 0) else "#FFFBEB"
            with cols[i % 4]:
                st.markdown(f"<div style='background-color:{bg}; padding:10px; border-radius:5px; border:1px solid #ddd; margin-bottom:10px;'><strong>{f}</strong><br>{done}/{assigned} Done</div>", unsafe_allow_html=True)

    st.divider()
    # --- PHASE 2 LEADERBOARD ---
    st.subheader("🏁 Phase 2: Leaderboard (Ranking)")
    p2_reviews = pd.read_sql("SELECT applicant_name, responses FROM phase2_reviews", engine)
    
    if not p2_reviews.empty:
        leaderboard_data = []
        for _, r_row in p2_reviews.iterrows():
            try:
                res = json.loads(r_row['responses'])
                leaderboard_data.append({"Applicant": r_row['applicant_name'], "Score": float(res.get('total_score', 0))})
            except: continue
        
        if leaderboard_data:
            ld_df = pd.DataFrame(leaderboard_data)
            final_ld = ld_df.groupby("Applicant")["Score"].mean().sort_values(ascending=False).reset_index()
            final_ld.index += 1
            st.table(final_ld)
        else: st.info("No Phase 2 scores submitted yet.")
    else: st.info("Waiting for Phase 2 data...")

# --- 4. RENDER MANAGEMENT ---
def render_management(menu, engine, hash_password, delete_item):
    if menu == "Phase 1 Management":
        apps_df = pd.read_sql("SELECT * FROM applicants ORDER BY id ASC", engine)
        st.header(f"📋 Phase 1 Management (Total Proposals: {len(apps_df)})")
        
        # Butang Bulk & Add Single
        c1, c2 = st.columns(2)
        if c1.button("📚 Bulk Add Applicants", use_container_width=True): bulk_add_applicants_dialog(engine)
        
        with st.expander("➕ Add Single Applicant"):
            with st.form("add_app_form", clear_on_submit=True):
                n = st.text_input("Full Name*")
                t = st.text_input("Proposal Title*")
                i = st.text_input("Institution")
                l = st.text_input("Info Link")
                r = st.text_area("Remarks")
                if st.form_submit_button("Save Applicant", type="primary"):
                    if n and t:
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO applicants (name, proposal_title, institution, info_link, remarks) VALUES (:n, :t, :i, :l, :r) ON CONFLICT (name) DO NOTHING"), {"n":n, "t":t, "i":i, "l":l, "r":r})
                        st.success("✅ Added!"); time.sleep(1); st.rerun()
                    else: st.warning("Please fill mandatory fields (*)")

        revs_df = pd.read_sql("SELECT username, full_name FROM reviewers", engine)
        assign_df = pd.read_sql("SELECT * FROM applicant_assignments", engine)
        rev_map = dict(zip(revs_df['username'], revs_df['full_name']))

        for idx, row in apps_df.iterrows():
            with st.container(border=True):
                ca, cb, cc = st.columns([0.2, 3, 1.2])
                ca.write(f"**{idx+1}**")
                cb.write(f"**{row['name']}**")
                cb.caption(f"🏫 {row['institution'] if row['institution'] else 'N/A'} | 📄 {row['proposal_title']}")
                
                # Butang Edit & Delete
                ced1, ced2 = cc.columns(2)
                if ced1.button("📝 Edit", key=f"edit_{row['id']}"): edit_applicant_dialog(engine, row)
                if ced2.button("🗑️", key=f"del_{row['id']}"): delete_item("applicants", row['id'])
                
                # Assignment Multiselect
                curr = assign_df[assign_df['applicant_name'] == row['name']]['reviewer_username'].tolist()
                sel = st.multiselect("Assign Phase 1 Reviewers:", options=list(rev_map.keys()), default=curr, format_func=lambda x: rev_map.get(x), key=f"p1_sel_{row['id']}")
                if st.button("💾 Save Assignment", key=f"p1_save_{row['id']}"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM applicant_assignments WHERE applicant_name = :a"), {"a": row['name']})
                        for r in sel:
                            conn.execute(text("INSERT INTO applicant_assignments (applicant_name, reviewer_username) VALUES (:a, :r)"), {"a": row['name'], "r": r})
                    st.success("✅ Assignment Saved!"); time.sleep(0.5); st.rerun()

    elif menu == "Phase 2 Management":
        finalists_df = pd.read_sql(text("SELECT DISTINCT a.* FROM applicants a JOIN reviews r ON a.name = r.applicant_name WHERE UPPER(r.final_recommendation) = 'YES'"), engine)
        st.header(f"🏆 Phase 2 Management (Total Finalists: {len(finalists_df)})")
        
        revs_df = pd.read_sql("SELECT username, full_name FROM reviewers", engine)
        assign_p2 = pd.read_sql("SELECT * FROM phase2_assignments", engine)
        rev_map = dict(zip(revs_df['username'], revs_df['full_name']))

        if finalists_df.empty:
            st.warning("Belum ada pemohon yang lulus Fasa 1.")
        else:
            for idx, row in finalists_df.iterrows():
                app_name = row['name']
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{idx+1}. {app_name}**")
                    
                    # Live scores display
                    scores_df = pd.read_sql(text("SELECT reviewer_username, responses, final_recommendation FROM phase2_reviews WHERE applicant_name = :n"), engine, params={"n": app_name})
                    if not scores_df.empty:
                        for _, s_row in scores_df.iterrows():
                            try:
                                m_data = json.loads(s_row['responses'])
                                st.markdown(f"⭐ **{s_row['reviewer_username']}**: :blue[{m_data.get('total_score', 0):.1f}%] ({s_row['final_recommendation']})")
                            except: continue
                    else: st.caption("No scores submitted yet.")

                    # Assign Phase 2
                    curr_p2 = assign_p2[assign_p2['applicant_name'] == app_name]['reviewer_username'].tolist()
                    sel_p2 = st.multiselect("Assign Phase 2 Reviewers:", options=list(rev_map.keys()), default=curr_p2, format_func=lambda x: rev_map.get(x), key=f"p2_sel_{row['id']}")
                    if c2.button("💾 Save", key=f"p2_save_{row['id']}"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM phase2_assignments WHERE applicant_name = :a"), {"a": app_name})
                            for r in sel_p2:
                                conn.execute(text("INSERT INTO phase2_assignments (applicant_name, reviewer_username) VALUES (:a, :r)"), {"a": app_name, "r": r})
                        st.success("✅ Saved!"); st.rerun()

    elif menu == "Reviewer Management":
        st.header("👤 Evaluator Management")
        c1, c2 = st.columns(2)
        if c1.button("📚 Bulk Add Reviewers", use_container_width=True): bulk_add_reviewers_dialog(engine, hash_password)
        
        with st.expander("➕ Add Single Evaluator"):
            with st.form("add_rev_form", clear_on_submit=True):
                n = st.text_input("Full Name")
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Save Evaluator"):
                    if n and u and p:
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO reviewers (username, full_name, password_hash) VALUES (:u, :n, :p) ON CONFLICT DO NOTHING"), {"u":u.strip(), "n":n.strip(), "p":hash_password(p)})
                        st.cache_resource.clear(); st.success("✅ Added!"); st.rerun()

        revs = pd.read_sql("SELECT * FROM reviewers ORDER BY id ASC", engine)
        for _, r in revs.iterrows():
            with st.container(border=True):
                ca, cb = st.columns([4, 1])
                ca.write(f"**{r['full_name']}** ({r['username']})")
                if cb.button("🗑️", key=f"del_rev_{r['id']}"): delete_item("reviewers", r['id'])
