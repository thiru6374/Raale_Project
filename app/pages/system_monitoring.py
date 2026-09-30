"""
app/pages/system_monitoring.py – System Monitoring Dashboard.

Shows real pipeline status, data quality, fairness monitoring, and
infrastructure health. No fake historical trends.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import plotly.express as px
import pandas as pd

from src.services.app_state import AppState
from src.monitoring.monitoring_service import MonitoringService



page_header(" System Monitoring", subtitle=None, icon=":material/speed:")
st.markdown("Real-time monitoring of pipeline health, data quality, fairness, and infrastructure.")

apply_global_styles()
render_sidebar()

AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()

res   = AppState.get_full_results()
raw_df = res.get("raw_df")
proc_df = res.get("processed_df")
pipe_df = res.get("pipeline_results")
fw   = res.get("fairness_warnings", [])
dur   = res.get("pipeline_duration_s", 0.0)
status = AppState.get_pipeline_status()

svc = MonitoringService(
  raw_df=raw_df,
  processed_df=proc_df,
  pipeline_df=pipe_df,
  fairness_warnings=fw,
  pipeline_status=status,
  pipeline_duration_s=dur,
)
report = svc.get_full_monitoring_report()

# ── STATUS HEADER ─────────────────────────────────────────────────────────────
health = report["pipeline_health"]
health_color = {"HEALTHY": "green", "ATTENTION REQUIRED": "orange", "DEGRADED": "red"}.get(health, "gray")
st.markdown(f"## Pipeline Health: :{health_color}[**{health}**]")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Pipeline Status", report["pipeline_status"])
k2.metric("Execution Time",  f"{report['pipeline_duration_s']:.1f}s")
k3.metric("Fallback Records", report["fallback_count"])
k4.metric("Untrusted Records", report["untrusted_count"])

st.markdown("---")

# ── DATA QUALITY ──────────────────────────────────────────────────────────────
st.subheader("Data Quality")
dq = report["data_quality"]
dq_color = {"PASS": "green", "WARNING": "orange", "CRITICAL": "red"}.get(dq["status"], "gray")
st.markdown(f"**Status:** :{dq_color}[**{dq['status']}**]")

q1, q2, q3, q4 = st.columns(4)
q1.metric("Total Records",  dq.get("total_records", 0))
q2.metric("Valid Records",  dq.get("valid_records", 0))
q3.metric("Invalid Records", dq.get("invalid_records",0))
q4.metric("Data Quality %", f"{dq.get('quality_pct', 0):.1f}%")

missing_data = dq.get("field_missing_rates", {})
if missing_data:
  st.markdown("**Missing Value Rates by Critical Field**")
  miss_df = pd.DataFrame([
    {"Field": k, "Missing %": v["missing_rate_pct"]}
    for k, v in missing_data.items()
  ])
  fig_miss = px.bar(
    miss_df, x="Field", y="Missing %", color="Missing %",
    color_continuous_scale=["#00CC96", "#FFC107", "#FF4B4B"],
    range_color=[0, 20], template="plotly_dark",
    title="Missing Value Rate per Critical Field (%)"
  )
  fig_miss.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300)
  st.plotly_chart(fig_miss, use_container_width=True)

st.caption(
  "Note: Historical data quality trends are not yet available. "
  "Only the current run is shown."
)

st.markdown("---")

# ── FAIRNESS MONITORING ───────────────────────────────────────────────────────
st.subheader("Fairness Monitoring")
fair = report["fairness"]
fair_color = {"PASS": "green", "WARNING": "orange", "CRITICAL": "red", "NO_DATA": "gray"}.get(
  fair["overall_status"], "gray"
)
st.markdown(f"**Fairness Status:** :{fair_color}[**{fair['overall_status']}**]")
st.write(f"Max Coverage Gap Across Groups: **{fair['max_coverage_gap_pct']:.1f}%** "
     f"(Threshold: {fair['threshold_pct']:.0f}%)")

if fair["warnings"]:
  for w in fair["warnings"]:
    st.warning(f" {w}")

groups = fair.get("groups", {})
if groups:
  rows = []
  for grp, metrics in groups.items():
    if "coverage_rate_pct" in metrics:
      rows.append({
        "Group": grp.replace("group_", "").replace("_", " ").title(),
        "Total Members": metrics.get("total_group", 0),
        "High-Risk Count": metrics.get("high_risk_count", 0),
        "High-Risk Covered": metrics.get("high_risk_covered", 0),
        "Coverage Rate %": metrics.get("coverage_rate_pct", 0),
        "Selection Rate %": metrics.get("selection_rate_pct", 0),
      })
  if rows:
    grp_df = pd.DataFrame(rows)
    fig_grp = px.bar(
      grp_df, x="Group", y="Coverage Rate %", color="Group",
      template="plotly_dark", title="High-Risk Coverage Rate by Population Group",
      color_discrete_sequence=["#636EFA", "#EF553B"],
    )
    fig_grp.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300)
    st.plotly_chart(fig_grp, use_container_width=True)
    st.dataframe(grp_df, hide_index=True, use_container_width=True)

st.markdown("---")

# ── DATA DISTRIBUTION ─────────────────────────────────────────────────────────
with st.expander("Data Distribution Statistics (Current Run)"):
  dist = report.get("data_distribution", {})
  if dist.get("status") == "AVAILABLE" and dist.get("distributions"):
    dist_rows = []
    for col, stats in dist["distributions"].items():
      dist_rows.append({"Field": col, **stats})
    st.dataframe(pd.DataFrame(dist_rows), hide_index=True, use_container_width=True)
  else:
    st.info("Distribution data is not available.")

st.markdown("---")

# ── INFRASTRUCTURE STATUS ─────────────────────────────────────────────────────
st.subheader("Infrastructure Status")
ic1, ic2, ic3 = st.columns(3)
ic1.metric("Audit Logging",   report["audit_logging_status"])
ic2.metric("Feedback Storage",  report["feedback_storage_status"])
ic3.metric("Experiment Storage", report["experiment_status"])

st.write(f"Total Stakeholder Feedback Responses: **{report['feedback_response_count']}**")

if st.button(" Refresh Monitoring"):
  AppState.initialize_application(force_refresh=True)
  st.rerun()
