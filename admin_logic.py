import streamlit as st
import pandas as pd
import os
import time
import base64
import json
from sqlalchemy import text

# --- LOCAL STORAGE SETUP ---
PHOTO_DIR = "evaluator_photos"
os.makedirs(PHOTO_DIR, exist_ok=True)

def get_local_image_base64(username):
    file_path = os.path.join(PHOTO_DIR, f"{username.replace(' ', '_')}.png")
    if os.path.exists(file_path):
        with open(file_path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode()
            # PEMBETULAN: Ditambah pengikat kata (") yang tertinggal tadi
            return f"data:image/png;base64,{b64}"
    return "https://cdn-icons-png.flaticon.com/512/149/149071.png"

# --- 1. DIALOGS FOR BULK ADDING & EDITING ---
@st.dialog("📚 Bulk Add Applicants")
def bulk_add_applicants_dialog(engine):
    st.markdown("**Format:** `Name, Proposal Title, Institution, Info Link, Remarks` (One per line)")
    raw_data = st.text_area("Paste Applicant List Here", height=200)
    
    if st.button("Import Applicants", type="primary"):
        if not raw_data.strip():
            st.error("🚨 Sila masukkan data.")
            return
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        count = 0
        with engine.begin() as conn:
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    app, title = parts[0], parts[1]
                    inst = parts[2] if len(parts) > 2 else None
                    link = parts[3] if len(parts) > 3 else None
                    rem = parts[4] if len(parts) > 4 else None
                    conn.execute(text("INSERT INTO applicants (name, proposal_title, institution, info_link, remarks) VALUES (:n, :t, :i, :l, :r) ON CONFLICT (name) DO NOTHING"), {"n": app, "t": title, "i": inst, "l": link, "r": rem})
                    count += 1
        st.cache_resource.clear()
        st.success(f"✅ Imported {count} applicants!"); time.sleep(1); st.rerun()

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
                    conn.execute(text("INSERT INTO reviewers (username, full_name, password_hash) VALUES (:u, :n, :p) ON CONFLICT (username) DO NOTHING"), {"u": parts[1], "n": parts[0], "p": hash_password(parts[2])})
                    count += 1
        st.cache_resource.clear(); st.success(f"✅ Imported {count} reviewers!"); time.sleep(1); st.rerun()

# --- 2. RENDER DASHBOARD ---
def render_dashboard(engine):
    st.header("📊 Live Evaluation Tracker")
    if st.button("🔄 Sync Dashboard Data"): st.cache_resource.clear(); st.rerun()
        
    revs_df = pd.read_sql("SELECT username, full_name FROM reviewers", engine)
    
    # Phase 1 Status
    st.subheader("📋 Phase 1: Shortlisting Status")
    reviews_p1 = pd.read_sql("SELECT reviewer_username, is_final FROM reviews", engine)
    assign_p1 = pd.read_sql("SELECT applicant_name, reviewer_username FROM applicant_assignments", engine)
    
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
    # Phase 2 Ranking Leaderboard
    st.subheader("🏁 Phase 2: Leaderboard (Ranking)")
    p2_reviews = pd.read_sql("SELECT applicant_name, responses FROM phase2_reviews", engine)
    
    if not p2_reviews.empty:
        leaderboard_data = []
        for _, r_row in p2_reviews.iterrows():
            try:
                res = json.loads(r_row['responses'])
                leaderboard_data.append({
                    "Applicant": r_row['applicant_name'],
                    "Score": float(res.get('total_score', 0))
                })
            except: continue
        
        if leaderboard_data:
            ld_df = pd.DataFrame(leaderboard_data)
            final_ld = ld_df.groupby("Applicant")["Score"].mean().reset_index()
            final_ld = final_ld.sort_values(by="Score", ascending=False).reset_index(drop=True)
            final_ld.index += 1
            st.table(final_ld)
        else:
            st.info("Waiting for Phase 2 scores...")
    else:
        st.info("No Phase 2 reviews submitted yet.")

# --- 3. RENDER MANAGEMENT ---
def render_management(menu, engine, hash_password, delete_item):
    if menu == "Phase 1 Management":
        st.header("📋 Phase 1: Shortlisting")
        if st.button("📚 Bulk Add Applicants"): bulk_add_applicants_dialog(engine)
        
        apps_df = pd.read_sql("SELECT * FROM applicants ORDER BY id ASC", engine)
        revs_df = pd.read_sql("SELECT username, full_name FROM reviewers", engine)
        assign_df = pd.read_sql("SELECT * FROM applicant_assignments", engine)
        rev_map = dict(zip(revs_df['username'], revs_df['full_name']))
        
        for idx, row in apps_df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['name']}**")
                c1.caption(f"{row['institution'] if row['institution'] else 'N/A'} | {row['proposal_title']}")
                curr = assign_df[assign_df['applicant_name'] == row['name']]['reviewer_username'].tolist()
                sel = c1.multiselect("Assign Phase 1 Reviewers:", options=list(rev_map.keys()), default=curr, format_func=lambda x: rev_map.get(x), key=f"p1_{row['name']}")
                if c2.button("💾 Save", key=f"s1_{row['name']}"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM applicant_assignments WHERE applicant_name = :a"), {"a": row['name']})
                        for r in sel:
                            conn.execute(text("INSERT INTO applicant_assignments (applicant_name, reviewer_username) VALUES (:a, :r)"), {"a": row['name'], "r": r})
                    st.success("Saved!"); time.sleep(0.5); st.rerun()

    elif menu == "Phase 2 Management":
        st.header("🏆 Phase 2: Finalist Selection")
        finalists_df = pd.read_sql(text("SELECT DISTINCT a.id, a.name, a.proposal_title, a.institution FROM applicants a JOIN reviews r ON a.name = r.applicant_name WHERE UPPER(r.final_recommendation) = 'YES'"), engine)
        
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
                    c1.caption(f"🏫 {row['institution'] if row['institution'] else 'N/A'}")
                    
                    scores_df = pd.read_sql(text("SELECT reviewer_username, responses, final_recommendation FROM phase2_reviews WHERE applicant_name = :n"), engine, params={"n": app_name})
                    if not scores_df.empty:
                        for _, s_row in scores_df.iterrows():
                            try:
                                m_data = json.loads(s_row['responses'])
                                t_score = m_data.get('total_score', 0)
                                rec = s_row['final_recommendation']
                                rec_color = "green" if rec == "YES" else "red"
                                st.markdown(f"⭐ **{s_row['reviewer_username']}**: :blue[{t_score:.1f}%] (:{rec_color}[{rec}])")
                            except: continue
                    else:
                        st.caption("No scores submitted yet.")

                    curr = assign_p2[assign_p2['applicant_name'] == app_name]['reviewer_username'].tolist()
                    sel = c1.multiselect("Assign Phase 2 Reviewers:", options=list(rev_
