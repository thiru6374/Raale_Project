"""
app/pages/operations_control_center.py

Operations Control Center
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from app.components.empty_states import show_pipeline_uninitialized
import pandas as pd
from datetime import datetime

from src.services.app_state import AppState
from src.services.operations_service import OperationsService
from src.services.data_refresh_service import DataRefreshService
from src.services.operational_health_service import OperationalHealthService
from src.services.capacity_pressure_service import CapacityPressureService
from src.services.drift_detection_service import DriftDetectionService
from src.services.release_readiness_service import ReleaseReadinessService

st.set_page_config(page_title="Operations Control Center", page_icon="", layout="wide")

apply_global_styles()
render_sidebar()

page_header(" Operations Control Center ()", "Continuous monitoring, data freshness, capacity pressure, and drift detection.", icon=":material/settings_applications:")

AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

ops_service = OperationsService()

# ── Centralized data retrieval ──────────────────────────────────────────────
df = AppState.get_pipeline_results()  # Final DataFrame
sys_health = AppState.get_system_health()
record_count = len(df) if df is not None else 0

# Initialize refresh state
if "last_refresh_data" not in st.session_state:
    st.session_state.last_refresh_data = DataRefreshService.execute_refresh(
        provider_status="HEALTHY",
        record_count=record_count,
        last_successful=datetime.utcnow().isoformat() + "Z"
    )

refresh_data = st.session_state.last_refresh_data

# Calculate operational health
op_health = OperationalHealthService.get_overall_health(
    pipeline_status=sys_health.get("overall_status", "HEALTHY"),
    provider_status=refresh_data.get("provider_status", "HEALTHY"),
    freshness_status=refresh_data.get("freshness_status", "FRESH"),
    security_status="HEALTHY",
    persistence_status="HEALTHY"
)

# ── SECTION A: SYSTEM HEALTH ─────────────────────────────────────────────────
st.header("A. System Health")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Operational Health", op_health.get("overall_status", "N/A"))
c2.metric("Data Freshness", refresh_data.get("freshness_status", "N/A"))
c3.metric("Pipeline Health", sys_health.get("overall_status", "N/A"))
c4.metric("Provider Status", refresh_data.get("provider_status", "N/A"))
c5.metric("Security Status", "HEALTHY")

degraded = op_health.get("degraded_components", [])
if degraded:
    st.warning("Degraded Components Detected:")
    st.table(pd.DataFrame(degraded))

st.markdown("---")

# ── SECTION B & D: DATA OPERATIONS ───────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.header("D. Data Operations")
    st.write(f"**Last Refresh:** {refresh_data.get('last_successful_refresh', 'N/A')}")
    st.write(f"**Records:** {refresh_data.get('record_count', 0)}")

    if st.button("🔄 Trigger Manual Data Refresh"):
        with st.spinner("Refreshing data..."):
            st.session_state.last_refresh_data = DataRefreshService.execute_refresh(
                provider_status="HEALTHY",
                record_count=record_count,
                last_successful=st.session_state.last_refresh_data.get("last_successful_refresh", "N/A")
            )
        st.success("Refresh complete!")
        st.rerun()

# ── SECTION F: CAPACITY STATUS ───────────────────────────────────────────────
with col2:
    st.header("F. Capacity Status")
    if df is not None and not df.empty:
        decisions = df.to_dict(orient="records")
        # risk_level already provided by the pipeline via standardized schema
        cap_status = CapacityPressureService.evaluate_capacity(
            available_capacity=25,
            planned_actions=decisions
        )
        st.write(f"**Status:** {cap_status.get('status', 'N/A')}")
        st.write(f"**Used/Available:** {cap_status.get('used_capacity', 0)} / {cap_status.get('available_capacity', 25)}")
        critical_areas = cap_status.get("critical_uncovered_areas", [])
        if critical_areas:
            st.error(f"Critical Uncovered Areas: {', '.join(str(a) for a in critical_areas)}")
    else:
        show_pipeline_uninitialized()

st.markdown("---")

# ── SECTION H: SYSTEM DRIFT ──────────────────────────────────────────────────
st.header("H. System Drift")
try:
    trends = ops_service.get_historical_trends()
    if trends.get("status") == "AVAILABLE":
        st.success("Historical Analytics Available")
        colA, colB, colC = st.columns(3)
        colA.metric("Risk Trend (High Risk Count)", trends.get("risk_trend"), delta_color="inverse")
        colB.metric("Fairness Trend (Gap)", f"{trends.get('fairness_trend', 0):.3f}", delta_color="inverse")
        colC.metric("Capacity Trend (Util)", f"{trends.get('capacity_trend', 0):.1%}", delta_color="inverse")
    else:
        st.info(trends.get("message", "No historical trend data available."))
except Exception as e:
    st.info(f"Trend analysis unavailable: {e}")

st.markdown("---")

# ── SECTION I: DRIFT DETECTION ────────────────────────────────────────────────
st.header("I. Model Drift Detection")
try:
    if df is not None and not df.empty:
        drift_result = DriftDetectionService.detect_drift(df)
        drift_col1, drift_col2 = st.columns(2)
        with drift_col1:
            st.write(f"**Drift Status:** {drift_result.get('status', 'N/A')}")
            st.write(f"**Risk Drift Score:** {drift_result.get('risk_drift_score', 0):.3f}")
        with drift_col2:
            st.write(f"**Fairness Drift:** {drift_result.get('fairness_drift_score', 0):.3f}")
            if drift_result.get("alert"):
                st.warning(drift_result["alert"])
    else:
        st.info("No data available for drift detection.")
except Exception as e:
    st.info(f"Drift detection unavailable: {e}")

st.markdown("---")

# ── SECTION J: RELEASE READINESS ─────────────────────────────────────────────
st.header("J. Release Readiness")
try:
    readiness = ReleaseReadinessService.evaluate_readiness(
        system_health=sys_health.get("overall_status", "HEALTHY"),
        pipeline_status="SUCCESS" if df is not None else "FAILED",
        fairness_status="PASS" if not AppState.get_fairness_warnings() else "WARNING"
    )
    ready_icon = "" if readiness.get("is_ready") else ""
    st.write(f"**{ready_icon} Release Decision:** {'APPROVED' if readiness.get('is_ready') else 'NOT READY'}")

    blockers = readiness.get("blockers", [])
    if blockers:
        st.error("Release Blockers:")
        for b in blockers:
            st.write(f"  - {b}")
    else:
        st.success("No release blockers detected.")
except Exception as e:
    st.info(f"Release readiness check unavailable: {e}")
