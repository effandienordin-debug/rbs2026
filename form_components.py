import streamlit as st
from database_utils import get_radio_index

def render_evaluation_fields(prev_resp=None, prev_data=None, disabled=False):
    if prev_resp is None: prev_resp = {}
    if prev_data is None: prev_data = {}
    
    sections = [
        ("Section 1 — Research Quality and Feasibility", [
            ("12a", "Are the proposed methods and objectives appropriate and achievable within the grant period (2 years)?"), 
            ("12b", "Does the applicant have relevant expertise and a strong research track record?"), 
            ("12c", "Have potential risks been identified, and are there plans to address them?")
        ]),
        ("Section 2 — Potential Impact", [
            ("14a", "Does the research address an important issue in medical science?"), 
            ("14b", "Does it have the potential to contribute to significant advancements in the medical field?")
        ]),
        ("Section 3 — Innovation and Novelty", [
            ("16a", "Does the research propose a novel approach or methodology?")
        ]),
        ("Section 4 — Value for Money", [
            ("18a", "Are the requested funds essential and appropriately allocated based on the importance of the research?")
        ]),
    ]
    
    responses = {}
    for title, qs in sections:
        st.subheader(title)
        for code, label in qs:
            current_idx = get_radio_index(prev_resp, code)
            responses[code] = st.radio(
                f"{label} *", 
                ["Yes", "No"], 
                index=current_idx, 
                horizontal=True, 
                disabled=disabled, 
                key=f"q{code}"
            )
        
        j_key = str(int(code[:2]) + 1) 
        responses[j_key] = st.text_area(f"Justification ({title})", value=prev_resp.get(j_key, ""), disabled=disabled, key=f"j{j_key}")
        st.divider()

    st.subheader("Section 5 — Final Recommendation")
    fr_val = prev_data.get('final_recommendation')
    
    q20 = st.radio(
        "Considering the evaluations made above, do you recommend this application for further consideration? *", 
        ["Yes", "No"], 
        index=(0 if fr_val=="Yes" else (1 if fr_val=="No" else None)), 
        horizontal=True, 
        disabled=disabled
    )
    j21 = st.text_area("Final justification *", value=prev_data.get('overall_justification', ""), disabled=disabled)
    
    return {"responses": responses, "recommendation": q20, "justification": j21}

# --- GANTIKAN FUNGSI INI DI DALAM form_components.py ---

def render_scoring_fields(prev_responses, rev_metadata, disabled=False):
    st.subheader("🏆 Phase 2: Winner Selection Scoring")
    st.info("Sila berikan markah (1.0 - 10.0) untuk setiap kriteria di bawah. Anda boleh menggunakan satu titik perpuluhan (contoh: 8.5).")
    
    def get_val(key, default=1.0):
        val = prev_responses.get(key, default)
        try:
            return float(val)
        except:
            return 1.0
            
    q_score = get_val('q_score', default=5.0) 
    imp_score = get_val('imp_score', default=5.0)
    inn_score = get_val('inn_score', default=5.0)
    vfm_score = get_val('vfm_score', default=5.0)
    
    st.divider()
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("**1. Research Quality and Feasibility (50%)**")
        st.caption("- Strength of medical or scientific case.\n- Feasibility of experimental plans, statistics, methodology and design.\n- How risks have been identified and will be mitigated.")
    with c2: q_val = st.number_input("Score (1-10)", min_value=1.0, max_value=10.0, step=0.1, value=q_score, format="%.1f", key="q", disabled=disabled)
        
    st.divider()
    c3, c4 = st.columns([3, 1])
    with c3:
        st.markdown("**2. Impact (20%)**")
        st.caption("- Identification of potential impacts of research for Malaysia and plans to deliver these.")
    with c4: imp_val = st.number_input("Score (1-10)", min_value=1.0, max_value=10.0, step=0.1, value=imp_score, format="%.1f", key="imp", disabled=disabled)

    st.divider()
    c5, c6 = st.columns([3, 1])
    with c5:
        st.markdown("**3. Innovation (20%)**")
        st.caption("- Level of innovation and whether that is likely to lead to significant new understanding.")
    with c6: inn_val = st.number_input("Score (1-10)", min_value=1.0, max_value=10.0, step=0.1, value=inn_score, format="%.1f", key="inn", disabled=disabled)

    st.divider()
    c7, c8 = st.columns([3, 1])
    with c7:
        st.markdown("**4. Value for Money (10%)**")
        st.caption("- Whether funds requested are essential and justified by the importance and scientific potential of the research.")
    with c8: vfm_val = st.number_input("Score (1-10)", min_value=1.0, max_value=10.0, step=0.1, value=vfm_score, format="%.1f", key="vfm", disabled=disabled)

    # Pengiraan Total (Wajaran: 50, 20, 20, 10)
    total_score = (q_val * 5) + (imp_val * 2) + (inn_val * 2) + (vfm_val * 1)
    
    st.divider()
    st.markdown(f"### 📈 Total Score (100%): :blue[{total_score:.1f}%]")
    st.divider()
    
    # --- REKOMENDASI & ULASAN FASA 2 ---
    st.subheader("💡 Final Recommendation")
    prev_rec = rev_metadata.get('final_recommendation')
    rec_index = 0 if prev_rec == "YES" else 1 if prev_rec == "NO" else None
    
    rec_val = st.radio("Recommended as the recipient of the Grant?", options=["YES", "NO"], index=rec_index, disabled=disabled, horizontal=True)
    prev_remark = rev_metadata.get('overall_justification', "")
    remark_val = st.text_area("Remark / Comment", value=prev_remark if prev_remark else "", height=150, disabled=disabled, placeholder="Sila berikan ulasan anda di sini...")
    
    return {
        "responses": {
            "q_score": q_val,
            "imp_score": imp_val,
            "inn_score": inn_val,
            "vfm_score": vfm_val,
            "total_score": total_score
        },
        "recommendation": rec_val,
        "justification": remark_val
    }
