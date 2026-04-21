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

# --- 2. DIALOGS (BULK & EDIT) ---
@st.dialog("📝 Edit Applicant")
def edit_applicant_dialog(engine, app_data):
    with st.form("edit_app_form"):
        new_name = st.text_input("Name", value=app_data['name'])
        new_title = st.text_input("Proposal Title", value=app_data['proposal_title'])
        new_inst = st.text_input("Institution", value=app_data['institution'])
        new_link = st.text_input("Info Link", value=app_data['info_link'])
        new_rem = st.text_area("Remarks", value=app_data['remarks'])
        
        if st.form_submit_button("Update Details", type="primary"):
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE applicants SET name=:n, proposal_title=:t, institution=:i, info_link=:l, remarks=:r 
                    WHERE id=:id
                """), {"n":new_name, "t":new_title, "i":new_inst, "l":new_link, "r":new_rem, "id":app_data['id']})
            st.success("Updated!"); time.sleep(1); st.rerun()

@st.dialog("📚 Bulk Add Applicants")
def bulk_add_applicants_dialog(engine):
    st.markdown("**Format:** `Name, Proposal Title, Institution, Info Link, Remarks` (One per line)")
    raw_data = st.text_area("Paste Applicant List Here", height=200)
    if st.button("Import Applicants", type="primary"):
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        count = 0
        with engine.begin() as conn:
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    conn.execute(text("""
                        INSERT INTO applicants (name, proposal_title, institution, info_link, remarks) 
                        VALUES (:n, :t, :i, :l, :r) ON CONFLICT (name) DO NOTHING
                    """), {"n":parts[0], "t":parts[1], "i":parts[2] if len(parts)>2 else "", "l":parts[3] if len(parts)>3 else "", "r":parts[4] if len(parts)>4 else ""})
                    count += 1
        st.cache_resource.clear(); st.success(f"Imported {count}!"); time.sleep(1); st.rerun()

@st.dialog("📚 Bulk Add Reviewers")
def bulk_add_reviewers_dialog(engine, hash_password):
    raw_data = st.text_area("Format: Name, Username, Password", height=200)
    if st.button("Import"):
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        with engine.begin() as conn:
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    conn.execute(text("INSERT INTO reviewers (username, full_name, password_hash) VALUES (:u, :n, :p) ON CONFLICT DO NOTHING"), {"u":parts[1], "n":parts[0], "p":hash_password(parts[2])})
        st.cache_resource.clear(); st.success("Done!"); time.sleep(1); st.rerun()

# --- 3. DASHBOARD ---
def render_dashboard(engine):
    st.header("📊 Live Evaluation Tracker")
    if st.button("🔄 Sync Data"): st.cache_resource.clear(); st.rerun()
    
    revs_df = pd.read_sql("SELECT username, full_name FROM reviewers", engine)
    
    # Phase 1 Status
    st.subheader("📋 Phase 1: Shortlisting Status")
    reviews_p1 = pd.read_sql("SELECT reviewer_username FROM reviews", engine)
    assign_p1 = pd.read_sql("SELECT reviewer_username FROM applicant_assignments", engine)
    if not revs_df.empty:
        cols = st.columns(4)
        for i, row in revs_df.iterrows():
            u, f = row['username'], row['full_name']
            assigned = len(assign_p1[assign_p1['reviewer_username'] == u])
            done = len(reviews_p1[reviews_p1['reviewer_username'] == u])
            bg = "#E6FFFA" if (done >= assigned and assigned > 0) else "#FFFBEB"
            with cols[i % 4]:
                st.markdown(f"<div style='background-color:{bg}; padding:10px; border-radius:5px;'><strong>{f}</strong><br>{done}/{assigned} Done</div>", unsafe_allow_html=True)

    st.divider()
    # Phase 2 Leaderboard
    st.subheader("🏁 Phase 2: Leaderboard")
    p2_reviews = pd.read_sql("SELECT applicant_name, responses FROM phase2_reviews", engine)
    if not p2_reviews.empty:
        ld = []
        for _, r in p2_reviews.iterrows():
            try:
                score = json.loads(r['responses']).get('total_score', 0)
                ld.append({"Applicant": r['applicant_name'], "Score": float(score)})
            except: continue
        if ld:
            df_ld = pd.DataFrame(ld).groupby("Applicant")["Score"].mean().sort_values(ascending=False).reset_index()
            df_ld.index += 1
            st.table(df_ld)

# --- 4. MANAGEMENT ---
def render_management(menu, engine, hash_password, delete_item):
    if menu == "Phase 1 Management":
        apps_df = pd.read_sql("SELECT * FROM applicants ORDER BY id ASC", engine)
        st.header(f"📋 Phase 1 Management (Total: {len(apps_df)})")
        
        c1, c2 = st.columns(2)
        if c1.button("📚 Bulk Add Applicants", use_container_width=True): bulk_add_applicants_dialog(engine)
        
        with st.expander("➕ Add Single Applicant"):
            with st.form("add_app_single", clear_on_submit=True):
                n = st.text_input("Name*")
                t = st.text_input("Title*")
                i = st.text_input("Institution")
                l = st.text_input("Link")
                r = st.text_area("Remarks")
                if st.form_submit_button("Save Applicant"):
                    if n and t:
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO applicants (name, proposal_title, institution, info_link, remarks) VALUES (:n, :t, :i, :l, :r)"), {"n":n, "t":t, "i":i, "l":l, "r":r})
                        st.success("Added!"); time.sleep(1); st.rerun()

        revs_df = pd.read_sql("SELECT username, full_name FROM reviewers", engine)
        assign_df = pd.read_sql("SELECT * FROM applicant_assignments", engine)
        rev_map = dict(zip(revs_df['username'], revs_df['full_name']))

        for idx, row in apps_df.iterrows():
            with st.container(border=True):
                ca, cb, cc = st.columns([0.1, 3, 1])
                ca.write(f"{idx+1}")
                cb.write(f"**{row['name']}**")
                cb.caption(f"{row['institution']} | {row['proposal_title']}")
                
                if cc.button("📝 Edit", key=f"ed_{row['id']}"): edit_applicant_dialog(engine, row)
                if cc.button("🗑️ Delete", key=f"del_{row['id']}"): delete_item("applicants", row['id'])
                
                curr = assign_df[assign_df['applicant_name'] == row['name']]['reviewer_username'].tolist()
                sel = st.multiselect("Assign Phase 1 Reviewers:", options=list(rev_map.keys()), default=curr, format_func=lambda x: rev_map.get(x), key=f"p1_sel_{row['id']}")
                if st.button("💾 Save Assignment", key=f"p1_sv_{row['id']}"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM applicant_assignments WHERE applicant_name = :a"), {"a":row['name']})
                        for r in sel:
                            conn.execute(text("INSERT INTO applicant_assignments (applicant_name, reviewer_username) VALUES (:a, :r)"), {"a":row['name'], "r":r})
                    st.success("Saved!"); time.sleep(0.5); st.rerun()

    elif menu == "Phase 2 Management":
        finalists_df = pd.read_sql(text("SELECT DISTINCT a.* FROM applicants a JOIN reviews r ON a.name = r.applicant_name WHERE UPPER(r.final_recommendation) = 'YES'"), engine)
        st.header(f"🏆 Phase 2 Management (Total: {len(finalists_df)})")
        
        revs_df = pd.read_sql("SELECT username, full_name FROM reviewers", engine)
        assign_p2 = pd.read_sql("SELECT * FROM phase2_assignments", engine)
        rev_map = dict(zip(revs_df['username'], revs_df['full_name']))

        for idx, row in finalists_df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{idx+1}. {row['name']}**")
                
                # Live scores
                sc_df = pd.read_sql(text("SELECT reviewer_username, responses, final_recommendation FROM phase2_reviews WHERE applicant_name = :n"), engine, params={"n":row['name']})
                for _, s in sc_df.iterrows():
                    try:
                        m = json.loads(s['responses']).get('total_score', 0)
                        st.markdown(f"⭐ **{s['reviewer_username']}**: :blue[{m:.1f}%] ({s['final_recommendation']})")
                    except: continue

                curr = st.multiselect("Assign Phase 2 Reviewers:", options=list(rev_map.keys()), default=assign_p2[assign_p2['applicant_name']==row['name']]['reviewer_username'].tolist(), format_func=lambda x: rev_map.get(x), key=f"p2_sel_{row['id']}")
                if c2.button("💾 Save", key=f"p2_sv_{row['id']}"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM phase2_assignments WHERE applicant_name = :a"), {"a":row['name']})
                        for r in curr:
                            conn.execute(text("INSERT INTO phase2_assignments (applicant_name, reviewer_username) VALUES (:a, :r)"), {"a":row['name'], "r":r})
                    st.success("Saved!"); st.rerun()

    elif menu == "Reviewer Management":
        st.header("👤 Evaluator Management")
        c1, c2 = st.columns(2)
        if c1.button("📚 Bulk Add Reviewers"): bulk_add_reviewers_dialog(engine, hash_password)
        
        with st.expander("➕ Add Single Evaluator"):
            with st.form("add_rev_single"):
                n, u, p = st.text_input("Name"), st.text_input("Username"), st.text_input("Password", type="password")
                if st.form_submit_button("Save"):
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO reviewers (username, full_name, password_hash) VALUES (:u, :n, :p)"), {"u":u, "n":n, "p":hash_password(p)})
                    st.success("Added!"); st.rerun()

        revs = pd.read_sql("SELECT * FROM reviewers ORDER BY id ASC", engine)
        for _, r in revs.iterrows():
            with st.container(border=True):
                ca, cb = st.columns([4, 1])
                ca.write(f"**{r['full_name']}** ({r['username']})")
                if cb.button("🗑️", key=f"del_rev_{r['id']}"): delete_item("reviewers", r['id'])
