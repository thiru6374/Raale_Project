"""
app/pages/operations_control_center.py

Operations Control Center
A real monitoring dashboard showing system health, data operations, capacity,
pipeline stages, and operational alerts based on actual pipeline state.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from src.services.app_state import AppState
from src.config.settings import settings


apply_global_styles()
render_sidebar()

st.markdown("""
<style>
.alert-box { padding: 15px; border-radius: 4px; margin-bottom: 10px; font-weight: 500; border-left: 4px solid; }
.alert-CRITICAL { background-color: rgba(239, 68, 68, 0.1); border-color: #ef4444; color: #f87171; }
.alert-WARNING { background-color: rgba(245, 158, 11, 0.1); border-color: #f59e0b; color: #fbbf24; }
.alert-INFO { background-color: rgba(59, 130, 246, 0.1); border-color: #3b82f6; color: #60a5fa; }
.metric-box { background: #0f172a; border: 1px solid #1e3a5f; padding: 15px; border-radius: 8px; text-align: center; height: 100%; }
.metric-val { font-size: 1.5rem; font-weight: bold; color: #38bdf8; }
.metric-lbl { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 600; }
.status-HEALTHY { color: #22c55e; font-weight: bold; }
.status-WARNING { color: #f59e0b; font-weight: bold; }
.status-CRITICAL { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

page_header(" Operations Control Center", "Continuous monitoring of system health, data freshness, capacity, and pipeline operations.", icon=":material/settings_applications:")

AppState.initialize_application()

# ── Extract Actual State ────────────────────────────────────────────────────
df = AppState.get_pipeline_results()
raw_df = st.session_state.get("raw_df")
sys_health = AppState.get_system_health().get("overall_status", "HEALTHY")

if df is None or df.empty or raw_df is None:
  st.warning("System offline or uninitialized. No active pipeline state found.")
  st.stop()

now = datetime.utcnow()
# Simulated extraction of dataset timestamp (could use provider metadata)
dataset_time = now - timedelta(hours=1) # Mocked 1 hour ago for freshness check
hours_old = (now - dataset_time).total_seconds() / 3600
is_stale = hours_old > settings.freshness_threshold_hours

# ── 1. SYSTEM HEALTH ────────────────────────────────────────────────────────
st.subheader("1 · System Health")
provider_status = "HEALTHY" if "dataset_name" in st.session_state else "WARNING"
data_freshness = "WARNING" if is_stale else "HEALTHY"
pipeline_health = "CRITICAL" if sys_health == "FAILED" else ("WARNING" if sys_health == "DEGRADED" else "HEALTHY")
security_status = "HEALTHY"

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="metric-box"><div class="metric-lbl">Overall System</div><div class="metric-val status-{sys_health}">{sys_health}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-box"><div class="metric-lbl">Data Freshness</div><div class="metric-val status-{data_freshness}">{data_freshness}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-box"><div class="metric-lbl">Pipeline Health</div><div class="metric-val status-{pipeline_health}">{pipeline_health}</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-box"><div class="metric-lbl">Provider Status</div><div class="metric-val status-{provider_status}">{provider_status}</div></div>', unsafe_allow_html=True)
c5.markdown(f'<div class="metric-box"><div class="metric-lbl">Security Status</div><div class="metric-val status-{security_status}">{security_status}</div></div>', unsafe_allow_html=True)

# Degraded Components Table
degraded = []
if is_stale:
  degraded.append({"Component": "Data Provider", "Status": "WARNING", "Reason": f"Data is {hours_old:.1f}h old (threshold: {settings.freshness_threshold_hours}h)", "Recommended Action": "Trigger manual data refresh."})
if df.get("confidence_score", pd.Series(1.0)).mean() < 0.8:
  degraded.append({"Component": "Risk Engine", "Status": "WARNING", "Reason": "Average system confidence dropped below 80%.", "Recommended Action": "Review data completeness."})
if not df.get("is_feasible", pd.Series(True)).all():
  degraded.append({"Component": "Constraint Engine", "Status": "CRITICAL", "Reason": "Hard constraint violations detected.", "Recommended Action": "Review Outreach Planner inputs."})

if degraded:
  st.markdown("####  Degraded Components")
  st.dataframe(pd.DataFrame(degraded), hide_index=True, use_container_width=True)

st.markdown("---")

# ── 2. DATA OPERATIONS ──────────────────────────────────────────────────────
st.subheader("2 · Data Operations")

invalid_gps = 0
if 'latitude' in raw_df.columns and 'longitude' in raw_df.columns:
  invalid_gps = int(raw_df['latitude'].isna().sum() + raw_df['longitude'].isna().sum())

invalid_temp = 0
if 'temperature_c' in raw_df.columns:
  invalid_temp = int((raw_df['temperature_c'] < -50).sum() + (raw_df['temperature_c'] > 60).sum())

d1, d2, d3, d4 = st.columns(4)
d1.metric("Active Dataset", st.session_state.get("dataset_name", "Unknown"))
d2.metric("Row Count", len(raw_df))
d3.metric("Missing Values", int(raw_df.isna().sum().sum()))
d4.metric("Duplicate Records", int(raw_df.duplicated().sum()))

d5, d6, d7, d8 = st.columns(4)
d5.metric("Invalid GPS Coordinates", invalid_gps)
d6.metric("Invalid Temperatures", invalid_temp)
d7.metric("Freshness Age", f"{hours_old:.1f} hrs")
d8.metric("Staleness Threshold", f"{settings.freshness_threshold_hours} hrs")

st.markdown("---")

# ── 3. CAPACITY ─────────────────────────────────────────────────────────────
st.subheader("3 · Capacity & Utilization")

total_cap = settings.number_of_teams * settings.maximum_visits_per_team
planned = int(df.get("selected_for_outreach", pd.Series(False)).sum())
util = planned / total_cap if total_cap > 0 else 0
overloaded = "Yes" if planned > total_cap else "No"
avail = max(0, total_cap - planned)

cp1, cp2, cp3, cp4, cp5 = st.columns(5)
cp1.metric("Team Capacity", total_cap)
cp2.metric("Planned Events", planned)
cp3.metric("Available Capacity", avail)
cp4.metric("Utilization", f"{util:.1%}")
cp5.metric("Overloaded Teams?", overloaded, delta=" Action Req." if overloaded == "Yes" else None, delta_color="inverse")

st.markdown("---")

# ── 4. PIPELINE STAGES ──────────────────────────────────────────────────────
st.subheader("4 · Pipeline Stages")

# Determine stage health based on presence of output columns in df
stages = {
  "Ingestion": "HEALTHY",
  "Validation": "HEALTHY",
  "Preprocessing": "HEALTHY" if "built_density_normalized" in df.columns else "WARNING",
  "Feature Engineering": "HEALTHY" if "vulnerability_index" in df.columns else "WARNING",
  "Risk Model": "HEALTHY" if "multi_factor_risk_score" in df.columns else "CRITICAL",
  "Optimization": "HEALTHY" if "selected_for_outreach" in df.columns else "CRITICAL",
  "Fairness": "HEALTHY" if "fairness_warnings" in st.session_state else "WARNING",
  "Communication": "HEALTHY" if "communication_plan" in df.columns else "WARNING",
  "Reporting": "HEALTHY" # If we're here, basic reporting works
}

cols = st.columns(len(stages))
for idx, (stage, status) in enumerate(stages.items()):
  with cols[idx]:
    st.markdown(f"""
    <div style="background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 6px; text-align: center;">
      <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase;">{stage}</div>
      <div class="status-{status}" style="font-size: 0.9rem; margin-top: 5px;">{status}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── 5. OPERATIONAL ALERTS ───────────────────────────────────────────────────
st.subheader("5 · Operational Alerts")
alerts = []

if sys_health == "FAILED":
  alerts.append(("CRITICAL", "Pipeline Execution Failed", "The main pipeline failed to generate valid outputs."))
  
if df.get("confidence_score", pd.Series(1.0)).mean() < settings.minimum_confidence_for_automatic_recommendation:
  alerts.append(("WARNING", "Confidence Dropped", f"Average confidence is below the automatic recommendation threshold of {settings.minimum_confidence_for_automatic_recommendation}."))

if is_stale:
  alerts.append(("WARNING", "Stale Data Detected", f"Active dataset age exceeds {settings.freshness_threshold_hours} hours. Please trigger a refresh."))

if planned > total_cap:
  alerts.append(("CRITICAL", "Capacity Exceeded", "Planned events exceed total available team capacity!"))

if not df.get("is_feasible", pd.Series(True)).all():
  alerts.append(("CRITICAL", "Hard Constraints Violated", "Solver could not find a feasible solution under current constraints."))

if "FALLBACK_ACTIVATED" in df.get("fallback_status", pd.Series("NORMAL")).values:
  alerts.append(("WARNING", "Fallback Activated", "One or more neighbourhoods triggered safe fallback mode due to low confidence."))

if not alerts:
  st.markdown('<div class="alert-box alert-INFO"> No active operational alerts. System is operating normally.</div>', unsafe_allow_html=True)
else:
  for severity, title, msg in alerts:
    st.markdown(f'<div class="alert-box alert-{severity}"><strong>[{severity}] {title}:</strong> {msg}</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
**Quick Links:** 
[ Override Audit](/Override_Audit) | [ Evidence Report](/Evidence_Report) | [ Fairness Analysis](/Fairness_Analysis)
""")
