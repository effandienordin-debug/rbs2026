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
