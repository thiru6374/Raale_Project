"""
app/pages/data_governance.py  –  Data Governance & Lineage UI.

Shows dataset registry, data lineage, and improvement candidates.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import pandas as pd

from src.services.app_state import AppState
from src.governance.dataset_registry import get_all_datasets, get_latest_dataset
from src.governance.improvement_candidates import (
    get_all_candidates, get_open_candidates,
    create_improvement_candidate, update_candidate_status,
    generate_candidates_from_feedback,
)
from src.evaluation.stakeholder_validation import StakeholderFeedbackManager

st.set_page_config(page_title="Data Governance & Lineage", page_icon="", layout="wide")

page_header(" Data Governance & Lineage", subtitle=None, icon=":material/policy:")
st.markdown(
    "Dataset registry, data lineage tracking, and continuous improvement candidates."
)

apply_global_styles()
render_sidebar()

AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

res        = AppState.get_full_results()
dataset_id = res.get("dataset_id", "N/A")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Dataset Registry & Lineage", "Improvement Candidates", "Security Notes"])

# ═══════════════════════════════════════════════════════════
# TAB 1: DATASET REGISTRY & LINEAGE
# ═══════════════════════════════════════════════════════════
with tab1:
    st.subheader("Current Session Dataset")
    st.metric("Active Dataset ID", dataset_id)

    latest = get_latest_dataset()
    if latest:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Source Type",   latest.get("source_type", "N/A"))
        c2.metric("Total Records", latest.get("total_records", 0))
        c3.metric("Quality Score", f"{latest.get('quality_score_pct', 0):.1f}%")
        c4.metric("Validation",    latest.get("validation_status", "N/A"))
        st.caption(f"Registered at: {latest.get('created_at', 'N/A')}")

    # Lineage diagram
    st.markdown("---")
    st.subheader("Data Lineage Pipeline")
    if latest:
        lineage = latest.get("lineage", {})
        lineage_stages = [
            ("raw_ingestion",       "📥 Raw Ingestion"),
            ("schema_validation",   " Schema Validation"),
            ("preprocessing",       "🧹 Preprocessing"),
            ("feature_engineering", " Feature Engineering"),
            ("risk_assessment",     " Risk Assessment"),
            ("optimization",        " Optimization"),
            ("communication",       "📢 Communication"),
            ("experiment",          " Experiment"),
            ("evidence",            " Evidence"),
        ]
        cols = st.columns(len(lineage_stages))
        for (stage_key, label), col in zip(lineage_stages, cols):
            stage_status = lineage.get(stage_key, "PENDING")
            icon = "" if stage_status == "COMPLETE" else ("⏳" if stage_status == "PENDING" else "")
            col.markdown(f"**{icon}**")
            col.caption(label.split(" ", 1)[1])
            col.caption(stage_status)
    else:
        st.info("No dataset registered yet in this session. Run the pipeline first.")

    # All registered datasets
    st.markdown("---")
    st.subheader("All Registered Datasets")
    all_ds = get_all_datasets()
    if all_ds:
        rows = [{
            "Dataset ID": d.get("dataset_id"),
            "Fingerprint": d.get("fingerprint"),
            "Source": d.get("source_type"),
            "Records": d.get("total_records"),
            "Quality %": d.get("quality_score_pct"),
            "Validation": d.get("validation_status"),
            "Registered": d.get("created_at", "")[:19].replace("T", " "),
        } for d in all_ds]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("No datasets registered yet.")

# ═══════════════════════════════════════════════════════════
# TAB 2: IMPROVEMENT CANDIDATES
# ═══════════════════════════════════════════════════════════
with tab2:
    st.subheader("Improvement Candidates")
    st.markdown(
        "Improvement candidates are **never automatically applied**. "
        "Each candidate must be reviewed, tested, and manually approved."
    )

    # Auto-generate from feedback
    if st.button("🔄 Generate Candidates from Stakeholder Feedback"):
        fm = StakeholderFeedbackManager()
        feedback = fm.get_all_feedback()
        if feedback:
            created = generate_candidates_from_feedback(feedback)
            if created:
                st.success(f"Created {len(created)} new improvement candidate(s): {', '.join(created)}")
            else:
                st.info("No new candidates generated (all scores are above threshold).")
        else:
            st.info("No stakeholder feedback found. Collect feedback first.")

    # Manual submission
    with st.expander("➕ Submit New Improvement Candidate"):
        with st.form("new_candidate_form"):
            src    = st.selectbox("Source", ["stakeholder_feedback", "fairness_warning", "failure_analysis", "data_quality", "experiment_result"])
            prob   = st.text_area("Problem Description")
            comp   = st.text_input("Affected Component")
            prop   = st.text_area("Proposed Improvement")
            ben    = st.text_input("Expected Benefit")
            risk   = st.selectbox("Risk", ["LOW", "MEDIUM", "HIGH"])
            submit = st.form_submit_button("Submit Candidate")
            if submit:
                if prob and comp and prop:
                    imp_id = create_improvement_candidate(src, prob, comp, prop, ben, risk)
                    st.success(f"Improvement candidate created: {imp_id}")
                else:
                    st.error("Please fill in all required fields.")

    # Display all candidates
    all_cands = get_all_candidates()
    if all_cands:
        open_count = len([c for c in all_cands if c.get("status") == "PROPOSED"])
        st.markdown(f"**{len(all_cands)} total candidates** | **{open_count} open (PROPOSED)**")

        for cand in all_cands:
            status_icon = {"PROPOSED": "🟡", "TESTING": "🔵", "APPROVED": "🟢", "REJECTED": "🔴", "IMPLEMENTED": ""}.get(cand.get("status"), "⚪")
            with st.expander(f"{status_icon} [{cand['improvement_id']}] {cand['problem_description'][:80]}"):
                st.write(f"**Status:** {cand['status']}")
                st.write(f"**Source:** {cand['source']}")
                st.write(f"**Affected Component:** {cand['affected_component']}")
                st.write(f"**Problem:** {cand['problem_description']}")
                st.write(f"**Proposed Improvement:** {cand['proposed_improvement']}")
                st.write(f"**Expected Benefit:** {cand['expected_benefit']}")
                st.write(f"**Risk:** {cand['risk']}")
                st.write(f"**Created:** {cand['timestamp'][:19].replace('T', ' ')}")

                if cand.get("status") == "PROPOSED":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button(f" Approve {cand['improvement_id']}", key=f"app_{cand['improvement_id']}"):
                            update_candidate_status(cand['improvement_id'], "APPROVED")
                            st.success("Approved.")
                            st.rerun()
                    with col_b:
                        if st.button(f" Reject {cand['improvement_id']}", key=f"rej_{cand['improvement_id']}"):
                            update_candidate_status(cand['improvement_id'], "REJECTED")
                            st.warning("Rejected.")
                            st.rerun()
    else:
        st.info("No improvement candidates yet.")

# ═══════════════════════════════════════════════════════════
# TAB 3: SECURITY NOTES
# ═══════════════════════════════════════════════════════════
with tab3:
    st.subheader("Security & Safe Data Handling Review")
    st.markdown("""
**Implemented Controls:**

| Control | Status | Notes |
|---------|--------|-------|
| No hardcoded secrets |  | All sensitive values read from `.env` via pydantic-settings |
| No personal data stored |  | All data is synthetic — no real resident information |
| File path safety |  | All paths use `pathlib.Path` or `os.path.join`; no raw user-supplied paths used in file ops |
| Feedback input sanitization |  | Feedback stored as JSON with `json.dumps` — no raw string injection |
| Audit log stability |  | IOError raised and caught if audit write fails; override never silently proceeds |
| User-facing error safety |  | Internal tracebacks not exposed to UI; only friendly error messages shown |
| Sensitive log suppression |  | No personally identifiable information in log outputs |

**Authentication Scope:**

> Authentication and role-based access control are **outside the current prototype scope**.
> The system is designed for trusted district planning teams operating in a controlled environment.
> Override authorization is controlled by the mandatory `user_id` field and `reason` field
> in the OverrideManager — every override is audit-logged and cannot proceed without logging.

**Future Production Enhancements:**

- OAuth2 / Active Directory authentication for district planner login
- Role-based access: READ (viewer) / PLAN (optimizer) / OVERRIDE (senior planner) / ADMIN
- TLS encryption for all data in transit
- Encrypted storage for audit logs
- Rate limiting on feedback submission
""")
