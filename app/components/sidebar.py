"""
app/components/sidebar.py

Standardized, categorized sidebar navigation for the planner.
"""
import streamlit as st

def render_sidebar():
    """Renders the grouped sidebar navigation."""
    with st.sidebar:
        st.markdown("### ☀ Heat-Risk Planner")
        st.markdown("<p style='font-size: 0.8rem; color: #94a3b8; margin-top: -10px; margin-bottom: 20px;'>Decision Support System</p>", unsafe_allow_html=True)
        
        st.markdown("**MAIN**")
        st.page_link("main.py", label="Executive Dashboard", icon=":material/dashboard:")
        st.page_link("pages/dashboard.py", label="System Overview", icon=":material/monitoring:")
        
        st.markdown("**ANALYTICS & DECISION SUPPORT**")
        st.page_link("pages/risk_map.py", label="Risk Map", icon=":material/map:")
        st.page_link("pages/outreach_planner.py", label="Outreach Planner", icon=":material/assignment:")
        st.page_link("pages/scenario_simulation.py", label="Scenario Simulation", icon=":material/science:")
        st.page_link("pages/baseline.py", label="Baseline vs Proposed", icon=":material/stacked_bar_chart:")
        st.page_link("pages/decision_center.py", label="Decision Center", icon=":material/psychology:")
        st.page_link("pages/decision_explainability.py", label="Decision Explainability", icon=":material/search_insights:")
        
        st.markdown("**EVALUATION & ASSURANCE**")
        st.page_link("pages/fairness_analysis.py", label="Fairness Analysis", icon=":material/balance:")
        st.page_link("pages/experiment_evaluation.py", label="Experiment Evaluation", icon=":material/biotech:")
        st.page_link("pages/failure_analysis.py", label="Failure Analysis", icon=":material/troubleshoot:")
        st.page_link("pages/evidence_report.py", label="Evidence Report", icon=":material/article:")
        st.page_link("pages/stakeholder_validation.py", label="Stakeholder Validation", icon=":material/groups:")
        st.page_link("pages/override_audit.py", label="Override Audit", icon=":material/history:")
        
        st.markdown("**OPERATIONS**")
        st.page_link("pages/operations_control_center.py", label="Operations Control Center", icon=":material/settings_applications:")
        st.page_link("pages/final_decision_center.py", label="Final Decision Intelligence", icon=":material/verified:")
        st.page_link("pages/system_monitoring.py", label="System Monitoring", icon=":material/speed:")
        st.page_link("pages/system_health.py", label="System Health", icon=":material/health_and_safety:")
        st.page_link("pages/release_readiness.py", label="Release Readiness", icon=":material/rocket_launch:")
        st.page_link("pages/security_dashboard.py", label="Security Dashboard", icon=":material/security:")
        st.page_link("pages/data_sources.py", label="Data Sources", icon=":material/database:")
        st.page_link("pages/data_governance.py", label="Data Governance", icon=":material/policy:")

