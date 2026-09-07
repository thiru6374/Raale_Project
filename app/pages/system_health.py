"""
app/pages/system_health.py  –  System Health & Readiness UI.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import pandas as pd

from src.services.app_state import AppState
from src.services.system_health_service import SystemHealthService

st.set_page_config(page_title="System Health", page_icon="", layout="wide")

page_header(" System Health & Readiness", subtitle=None, icon=":material/health_and_safety:")
st.markdown("Real-time end-to-end validation of the application and data pipeline.")

apply_global_styles()
render_sidebar()

AppState.initialize_application()

health = SystemHealthService.get_system_health()

status_color = {
    "HEALTHY": "green",
    "ATTENTION REQUIRED": "orange",
    "FAILED": "red"
}
current_color = status_color.get(health["overall_status"], "gray")

st.markdown(f"### Overall System Status: :{current_color}[**{health['overall_status']}**]")

if health["critical_errors"]:
    st.error("Critical Errors Detected:")
    for err in health["critical_errors"]:
        st.write(f"- {err}")

if health["warnings"]:
    st.warning("System Warnings:")
    for warn in health["warnings"]:
        st.write(f"- {warn}")

st.markdown("---")
st.subheader("Pipeline Status")

c1, c2, c3, c4, c5, c6 = st.columns(6)
def format_phase(val):
    if val == "PASS": return " PASS"
    if val == "WARNING": return " WARN"
    return " FAIL"

c1.metric("Foundation", format_phase(health["phase_1"]))
c2.metric("Data", format_phase(health["phase_2"]))
c3.metric("Validation", format_phase(health["phase_3"]))
c4.metric("Planning", format_phase(health["phase_4"]))
c5.metric("Evaluation", format_phase(health["phase_5"]))
c6.metric("Readiness", format_phase(health["phase_6"]))

st.markdown("---")
st.subheader("System Metrics")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Data Quality", f"{health['data_quality']:.1f}%")
col1.write(f"Valid Records: {health['valid_records']}")
col1.write(f"Invalid Records: {health['invalid_records']}")

col2.metric("Recommendation Trust", health["recommendation_trust"])
fallback_str = "ACTIVE" if health["fallback_active"] else "NOT ACTIVE"
col2.write(f"Safe Fallback: {fallback_str}")

col3.metric("Fairness Check", format_phase(health["fairness_status"]))
col3.metric("Capacity Status", format_phase(health["capacity_status"]))

col4.metric("Experiments Found", format_phase(health["experiment_status"]))
col4.metric("Feedback Collected", health["stakeholder_feedback_count"])

if st.button("Refresh System Health"):
    AppState.initialize_application(force_refresh=True)
    st.rerun()
