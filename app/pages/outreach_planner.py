"""
app/pages/outreach_planner.py  –  Outreach plan results and override UI.
(UI Redesign)
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from src.services.app_state import AppState
from src.governance.audit_logger import AuditLogger
from src.governance.overrides import OverrideManager

from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from app.components.cards import html_card
from app.components.empty_states import show_pipeline_uninitialized

st.set_page_config(page_title="Outreach Planner", page_icon="", layout="wide")

apply_global_styles()
render_sidebar()

page_header(" Outreach Planner", "Review and manage the optimised, capacity-constrained outreach plan.", icon=":material/assignment:")

AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

df = AppState.get_pipeline_results()
if df is None:
    show_pipeline_uninitialized()
    st.stop()

warnings = AppState.get_fairness_warnings()

# ── Key Metrics ───────────────────────────────────────────────────────────────
total        = len(df)
selected     = int(df["selected_for_outreach"].sum())
manual_rev   = int((df["fallback_status"] == "MANUAL_REVIEW").sum())
extreme      = int((df["multi_factor_risk_category"] == "EXTREME").sum())

c1, c2, c3, c4 = st.columns(4)
with c1:
    html_card("Total Neighbourhoods", str(total), icon="")
with c2:
    html_card("Selected for Outreach", str(selected), f"{selected / total:.0%} coverage", icon="")
with c3:
    html_card("Extreme Risk Zones", str(extreme), icon="local_fire_department")
with c4:
    html_card("Review Needed", str(manual_rev), icon="visibility")

st.markdown("<br>", unsafe_allow_html=True)

# ── Action Table ──────────────────────────────────────────────────────────────
st.markdown("### Priority Neighbourhoods")

st.markdown("<div style='background: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px;'>", unsafe_allow_html=True)
filter_option = st.selectbox(
    "Filter by Priority Status",
    ["All", "PRIMARY_OUTREACH", "WAITLIST_HIGH_RISK", "NEEDS_REVIEW", "NO_ACTION"]
)
st.markdown("</div>", unsafe_allow_html=True)

display_cols = [
    "neighbourhood_id", "neighbourhood_name", "district",
    "multi_factor_risk_category", "multi_factor_risk_score",
    "confidence_score", "fallback_status", "selected_for_outreach",
    "outreach_priority"
]
available_cols = [c for c in display_cols if c in df.columns]
sorted_df = df[available_cols].sort_values("multi_factor_risk_score", ascending=False).copy()

if filter_option != "All":
    sorted_df = sorted_df[sorted_df["outreach_priority"] == filter_option]

sorted_df.rename(columns={
    "neighbourhood_id": "ID",
    "neighbourhood_name": "Neighbourhood",
    "district": "District",
    "multi_factor_risk_category": "Risk Level",
    "multi_factor_risk_score": "Risk Score",
    "selected_for_outreach": "Selected",
    "outreach_priority": "Priority"
}, inplace=True)

if "Risk Score" in sorted_df.columns:
    sorted_df["Risk Score"] = sorted_df["Risk Score"].round(2)
if "confidence_score" in sorted_df.columns:
    sorted_df["confidence_score"] = sorted_df["confidence_score"].round(2)

def _highlight(val):
    if val == "EXTREME":
        return "background-color: #fee2e2; color: #ef4444; font-weight: bold"
    if val == "HIGH":
        return "background-color: #ffedd5; color: #f97316; font-weight: bold"
    return ""

st.dataframe(
    sorted_df.style.map(_highlight, subset=["Risk Level"]),
    use_container_width=True,
    height=400,
    hide_index=True
)

st.markdown("<br>", unsafe_allow_html=True)

# ── Manual Override ───────────────────────────────────────────────────────────
st.markdown("### 👤 Manual Override")
st.markdown("<p style='color: #64748b; font-size: 0.95rem; margin-bottom: 15px;'>Manually override the system's selection. All actions are strictly audit-logged.</p>", unsafe_allow_html=True)

st.markdown("<div style='background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
ov_col1, ov_col2 = st.columns([1, 1])

with ov_col1:
    ov_id = st.selectbox("Select Neighbourhood ID", df["neighbourhood_id"].tolist())
    ov_user = st.text_input("Authorised User ID", value="admin")
    
with ov_col2:
    ov_action = st.radio("Override Action", ["Force SELECT", "Force DESELECT"])
    ov_reason = st.text_input("Mandatory Reason for Override")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("Apply Override", type="primary"):
    if not ov_reason.strip():
        st.error("A mandatory reason must be provided before overriding.")
    else:
        try:
            audit_log = AuditLogger(log_path="logs/audit.jsonl")
            manager   = OverrideManager(audit_logger=audit_log)
            updated   = manager.force_selection(
                df=st.session_state.pipeline_results,
                neighbourhood_id=ov_id,
                user=ov_user,
                reason=ov_reason,
                force_select=(ov_action == "Force SELECT")
            )
            st.session_state.pipeline_results = updated
            st.success(f" Override applied for {ov_id}. The plan has been updated.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to apply override. Check system logs.")
st.markdown("</div>", unsafe_allow_html=True)
