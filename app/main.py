"""
app/main.py

Canonical navigation configuration and application entry point.
"""
import streamlit as st
from app.components.sidebar import render_confidence_card
from app.components.layout import apply_global_styles

st.set_page_config(page_title="Heat-Risk Planner", layout="wide")

apply_global_styles()

overview_pages = [
    st.Page("pages/overview.py", title="Overview", icon=":material/dashboard:", default=True)
]

planning_pages = [
    st.Page("pages/risk_map.py", title="Risk Map", icon=":material/map:"),
    st.Page("pages/baseline.py", title="Baseline vs Proposed", icon=":material/stacked_bar_chart:"),
    st.Page("pages/outreach_planner.py", title="Outreach Plan", icon=":material/assignment:"),
    st.Page("pages/communication_planner.py", title="Communications", icon=":material/campaign:"),
]

governance_pages = [
    st.Page("pages/fairness_analysis.py", title="Fairness & Bias", icon=":material/balance:"),
    st.Page("pages/data_governance.py", title="Data Quality", icon=":material/policy:"),
    st.Page("pages/override_audit.py", title="Audit & Overrides", icon=":material/history:"),
    st.Page("pages/evidence_report.py", title="Reports", icon=":material/article:"),
]

decision_pages = [
    st.Page("pages/final_decision_center.py", title="Final Decision Intelligence", icon=":material/verified:"),
    st.Page("pages/decision_explainability.py", title="Decision Explainability", icon=":material/search_insights:"),
    st.Page("pages/decision_center.py", title="Decision Center", icon=":material/psychology:"),
]

operations_pages = [
    st.Page("pages/operations_control_center.py", title="Operations Control Center", icon=":material/settings_applications:"),
    st.Page("pages/data_sources.py", title="Data Sources", icon=":material/database:"),
    st.Page("pages/scenario_simulation.py", title="Scenario Simulation", icon=":material/science:"),
    st.Page("pages/security_dashboard.py", title="Security Dashboard", icon=":material/security:"),
    st.Page("pages/stakeholder_validation.py", title="Stakeholder Validation", icon=":material/groups:"),
    st.Page("pages/system_health.py", title="System Health", icon=":material/health_and_safety:"),
    st.Page("pages/system_monitoring.py", title="System Monitoring", icon=":material/speed:"),
    st.Page("pages/release_readiness.py", title="Release Readiness", icon=":material/rocket_launch:"),
    st.Page("pages/methodology.py", title="Methodology", icon=":material/menu_book:"),
]

pg = st.navigation({
    "Overview": overview_pages,
    "Planning & Risk": planning_pages,
    "Governance & Quality": governance_pages,
    "Decision Intelligence": decision_pages,
    "Operations & Administration": operations_pages
})

# Custom components to always show in the sidebar
with st.sidebar:
    render_confidence_card()

# Run the selected page
pg.run()
