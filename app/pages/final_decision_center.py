"""
app/pages/final_decision_center.py

Final Decision Intelligence and Outcome Evaluation
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from app.components.empty_states import show_pipeline_uninitialized
import pandas as pd
from datetime import datetime
import uuid

from src.services.app_state import AppState
from src.services.decision_intelligence_service import DecisionIntelligenceService
from src.services.outcome_tracking_service import OutcomeTrackingService
from src.services.kpi_service import KPIService
from src.services.report_service import ReportService
from src.services.system_health_service import SystemHealthService
from src.security.security_service import SecurityService

st.set_page_config(page_title="Final Decision Center", page_icon="", layout="wide")

# Styling
st.markdown("""
<style>
    .priority-CRITICAL { border-left: 5px solid #FF4B4B; padding: 10px; background-color: rgba(255, 75, 75, 0.1); margin-bottom: 10px; border-radius: 4px; }
    .priority-HIGH { border-left: 5px solid #FF8C00; padding: 10px; background-color: rgba(255, 140, 0, 0.1); margin-bottom: 10px; border-radius: 4px; }
    .priority-MEDIUM { border-left: 5px solid #FFC107; padding: 10px; background-color: rgba(255, 193, 7, 0.1); margin-bottom: 10px; border-radius: 4px; }
    .priority-LOW { border-left: 5px solid #00CC96; padding: 10px; background-color: rgba(0, 204, 150, 0.1); margin-bottom: 10px; border-radius: 4px; }
    .priority-MANUAL_REVIEW_REQUIRED { border-left: 5px solid #888888; padding: 10px; background-color: rgba(136, 136, 136, 0.1); margin-bottom: 10px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

apply_global_styles()
render_sidebar()

page_header(" Final Decision Intelligence ()", "AI-powered outreach decisions with human oversight, outcome tracking, and KPI evaluation.", icon=":material/verified:")

AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

# Dependencies
tracker = OutcomeTrackingService()
role = SecurityService.render_role_selector(sidebar=True)

# ── Data retrieval via centralized API ──────────────────────────────────────
df = AppState.get_pipeline_results()  # Final DataFrame from pipeline
if df is None or df.empty:
    show_pipeline_uninitialized()
    st.stop()

system_health = AppState.get_system_health()
pipeline_run_id = AppState.get_pipeline_run_id() or str(uuid.uuid4())
config_version = "v12.0"
fairness_warnings = AppState.get_fairness_warnings()

# Build neighbourhood records from the final DataFrame for the Decision Intelligence Service
# The service expects a list of dicts representing each neighbourhood
neighbourhoods = df.to_dict(orient="records")

# Build a simplified fairness dict for KPI calculation
fairness_dict = {}
if fairness_warnings:
    gaps = [w.get("coverage_gap", 0) for w in fairness_warnings if isinstance(w, dict)]
    if gaps:
        fairness_dict["disparity"] = max(gaps)

alerts = []  # Active operational alerts

with st.spinner("Generating Final Decision Intelligence..."):
    try:
        decisions = DecisionIntelligenceService.generate_final_decisions(
            neighbourhoods=neighbourhoods,
            system_health_status=system_health.get("overall_status", "HEALTHY"),
            alerts=alerts,
            pipeline_run_id=pipeline_run_id,
            config_version=config_version
        )
    except Exception as e:
        st.error(f"Decision Intelligence generation failed: {e}")
        decisions = []

    # Initialize tracking if not present for this run
    if decisions:
        try:
            existing_outcomes = tracker.get_all_records()
            existing_rec_ids = {r["recommendation_id"] for r in existing_outcomes}
            for dec in decisions:
                if dec["recommendation_id"] not in existing_rec_ids:
                    tracker.log_recommendation_generated(dec)
        except Exception:
            pass

try:
    outcome_map = tracker.get_latest_status_map()
except Exception:
    outcome_map = {}

# Calculate KPIs
capacity_used = sum(1 for d in decisions if d.get("priority") in ["CRITICAL", "HIGH"]) if decisions else 0
capacity_total = 25

kpis = {}
try:
    kpis = KPIService.calculate_kpis(
        recommendations=decisions,
        outcome_status_map=outcome_map,
        fairness_results=fairness_dict,
        system_health=system_health.get("overall_status", "HEALTHY"),
        capacity_used=capacity_used,
        capacity_total=capacity_total
    )
except Exception:
    kpis = {
        "system_trust_rate": 0.0,
        "risk_coverage_rate": 0.0,
        "capacity_utilization": 0.0,
        "fairness_gap": 0.0
    }

baseline_kpis = {
    "risk_coverage_rate": 0.4,
    "capacity_utilization": 1.0,
    "fairness_gap": fairness_dict.get("disparity", 0) + 0.15
}

# ── SECTION 1: DISTRICT STATUS ───────────────────────────────────────────────
st.header("1. District Status")
c1, c2, c3, c4 = st.columns(4)
c1.metric("System Trust Rate", f"{kpis.get('system_trust_rate', 0):.0%}")
c2.metric("Risk Coverage Rate", f"{kpis.get('risk_coverage_rate', 0):.0%}",
          delta=f"{kpis.get('risk_coverage_rate', 0) - baseline_kpis['risk_coverage_rate']:.0%} vs Baseline")
c3.metric("Capacity Utilization", f"{kpis.get('capacity_utilization', 0):.0%}")
c4.metric("Fairness Gap", f"{kpis.get('fairness_gap', 0):.3f}")

st.markdown("---")

# ── SECTION 2: TOP PRIORITY ACTIONS ──────────────────────────────────────────
st.header("2. Top Priority Actions")
if not decisions:
    st.info("No decisions generated. Ensure the pipeline has run successfully.")
else:
    top_actions = [d for d in decisions if d.get("priority") in ["CRITICAL", "HIGH", "MANUAL_REVIEW_REQUIRED"]]

    if top_actions:
        for act in top_actions[:5]:
            priority = act.get("priority", "MEDIUM")
            st.markdown(f"""
            <div class="priority-{priority}">
                <h4>{act.get('neighbourhood_id', 'Unknown')} — {priority}</h4>
                <p><strong>Recommended Action:</strong> {act.get('recommended_action', 'N/A')}</p>
                <p><strong>Timing:</strong> {act.get('recommended_timing', 'N/A')}</p>
                <p><strong>Reasoning:</strong> {act.get('reasoning', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No critical or high-priority actions. System is operating within normal parameters.")

    st.markdown("---")

    # ── SECTION 3: ALL DECISIONS TABLE ───────────────────────────────────────
    st.header("3. All Decisions")
    dec_df = pd.DataFrame(decisions)
    if not dec_df.empty:
        display_cols = [c for c in ["neighbourhood_id", "priority", "recommended_action", "recommended_timing", "reasoning"] if c in dec_df.columns]
        st.dataframe(dec_df[display_cols], use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── SECTION 4: OUTCOME TRACKING ──────────────────────────────────────────
    st.header("4. Outcome Tracking")
    st.caption("Update delivery outcomes for tracked decisions.")
    try:
        outcome_records = tracker.get_all_records()
        if outcome_records:
            out_df = pd.DataFrame(outcome_records)
            display_out_cols = [c for c in ["recommendation_id", "neighbourhood_id", "status", "timestamp"] if c in out_df.columns]
            st.dataframe(out_df[display_out_cols].head(10), use_container_width=True, hide_index=True)
        else:
            st.info("No outcomes have been tracked yet.")
    except Exception as e:
        st.warning(f"Outcome tracking unavailable: {e}")

    st.markdown("---")

    # ── SECTION 5: AUTOMATED REPORT ──────────────────────────────────────────
    st.header("5. Automated Report")
    if st.button(" Generate & Download Report", type="primary"):
        try:
            report = ReportService.generate_report(
                decisions=decisions,
                kpis=kpis,
                pipeline_run_id=pipeline_run_id
            )
            st.download_button(
                label="Download Report (JSON)",
                data=str(report),
                file_name=f"heat_risk_report_{pipeline_run_id[:8]}.json",
                mime="application/json"
            )
        except Exception as e:
            st.error(f"Report generation failed: {e}")
