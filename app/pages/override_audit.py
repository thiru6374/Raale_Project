"""
app/pages/override_audit.py  –  Audit trail for manual overrides.
(UI Redesign)
"""
import os
import json
import streamlit as st
import pandas as pd

from src.services.app_state import AppState
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from app.components.cards import html_card
from app.components.empty_states import show_empty_state

st.set_page_config(page_title="Overrides & Audit", page_icon="", layout="wide")

apply_global_styles()
render_sidebar()

page_header(" Overrides & Audit Log", "Review all manual interventions applied to the outreach planner.", icon=":material/history:")

AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

AUDIT_PATH = "logs/audit.jsonl"

def _render_empty():
    show_empty_state(
        icon="",
        title="No Overrides Found",
        description="No manual overrides have been applied yet. The system is operating fully on automated recommendations."
    )

# ── Safe empty-log fallback ───────────────────────────────────────────────────
if not os.path.exists(AUDIT_PATH) or os.path.getsize(AUDIT_PATH) == 0:
    _render_empty()
    st.stop()

# ── Read and display audit log ────────────────────────────────────────────────
try:
    with open(AUDIT_PATH, "r") as f:
        lines = [l.strip() for l in f if l.strip()]

    if not lines:
        _render_empty()
        st.stop()

    records  = [json.loads(line) for line in lines]
    audit_df = pd.DataFrame(records)

    if "timestamp" in audit_df.columns:
        audit_df["timestamp"] = pd.to_datetime(audit_df["timestamp"])
        audit_df = audit_df.sort_values("timestamp", ascending=False)
        
    audit_df.rename(columns={
        "timestamp": "Date",
        "user_id": "User",
        "neighbourhood_id": "Neighbourhood ID",
        "previous_recommendation": "Original",
        "new_recommendation": "Override Action",
        "reason": "Reason"
    }, inplace=True)

    # ── Key Metrics ───────────────────────────────────────────────────────────────
    total_overrides = len(audit_df)
    forced_sel = (audit_df["Override Action"] == "SELECTED").sum() if "Override Action" in audit_df.columns else 0
    forced_desel = total_overrides - forced_sel

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        html_card("Total Manual Overrides", str(total_overrides), icon="")
    with c2:
        html_card("Forced Selections", str(forced_sel), icon="")
    with c3:
        html_card("Forced Deselections", str(forced_desel), icon="")

    st.markdown("<br>### Audit Log", unsafe_allow_html=True)
    
    # Format dates
    if "Date" in audit_df.columns:
        audit_df["Date"] = audit_df["Date"].dt.strftime('%Y-%m-%d %H:%M:%S')
        
    st.dataframe(audit_df, use_container_width=True, hide_index=True)

except json.JSONDecodeError:
    show_empty_state("", "Audit Log Corrupted", "The audit log contains invalid data and cannot be displayed.")
except Exception as exc:
    show_empty_state("", "Failed to Read Audit Log", "An unexpected error occurred while reading the logs.")
