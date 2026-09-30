"""
app/pages/scenario_simulation.py - Scenario Simulation UI.

Provides an operational test environment for running scenarios,
comparing before vs after metrics, and viewing historical run results.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import pandas as pd
import json

from src.services.app_state import AppState
from src.simulation.scenario_definitions import SCENARIOS
from src.simulation.scenario_runner import run_scenario, get_latest_scenario_result



page_header(" Scenario Simulation Engine", subtitle=None, icon=":material/science:")
st.markdown(
  "Run predefined operational stress tests and observe how the system adapts "
  "to extreme weather, data failures, and capacity constraints."
)

apply_global_styles()
render_sidebar()

AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()

# ── SCENARIO SELECTION ────────────────────────────────────────────────────────
st.subheader("1. Select a Scenario")
scenario_options = {s_id: s_cfg["name"] for s_id, s_cfg in SCENARIOS.items()}
selected_scenario_id = st.selectbox(
  "Available Scenarios",
  options=list(scenario_options.keys()),
  format_func=lambda x: scenario_options[x]
)

cfg = SCENARIOS[selected_scenario_id]

with st.expander(f" Details: {cfg['name']}", expanded=True):
  st.write(f"**Description:** {cfg['description']}")
  st.write(f"**Expected Behaviour:** {cfg['expected_behaviour']}")
  c1, c2 = st.columns(2)
  with c1:
    st.write("**Simulated Conditions:**")
    st.json(cfg["input_changes"])
    st.write(f"**Missing Data Rate:** {cfg['data_quality_conditions']['missing_rate']*100:.0f}%")
  with c2:
    st.write("**Operational Settings:**")
    st.write(f"Optimization Strategy: `{cfg['strategy']}`")
    st.write(f"Teams: {cfg['capacity_settings']['number_of_teams']}")
    st.write(f"Visits/Team: {cfg['capacity_settings']['maximum_visits_per_team']}")

# ── SCENARIO EXECUTION ────────────────────────────────────────────────────────
st.subheader("2. Execute Scenario")
st.markdown(
  "> **Warning:** Running a scenario temporarily overrides the active dashboard session data. "
  "You can restore the normal pipeline from the sidebar at any time."
)

col_run, col_restore = st.columns(2)
with col_run:
  if st.button(" Run Scenario", type="primary"):
    with st.spinner(f"Executing {cfg['name']} pipeline..."):
      result = run_scenario(selected_scenario_id)
      
      # Store results in app state so the rest of the dashboard reflects it
      st.session_state.app_errors = result["errors"]
      if result["status"] == "SUCCESS":
        st.session_state.raw_df       = result.get("raw_df")
        st.session_state.processed_df    = result.get("processed_df")
        st.session_state.pipeline_results  = result.get("pipeline_results")
        st.session_state.fairness_warnings = result.get("fairness_warnings", [])
        st.session_state.baseline_results  = result.get("baseline_results")
        st.session_state.dataset_id     = result.get("dataset_id", "N/A")
        st.session_state.pipeline_duration_s = result.get("pipeline_duration_s", 0.0)
        st.session_state.optimization_strategy = cfg["strategy"]
      
      st.session_state.last_scenario_run = result.get("scenario_record")
      st.success(f"Scenario completed in {result.get('pipeline_duration_s', 0):.2f}s!")
      
with col_restore:
  if st.button(" Restore Normal Pipeline"):
    st.session_state.last_scenario_run = None
    AppState.initialize_application(force_refresh=True)
    st.rerun()

st.markdown("---")

# ── RESULTS & METRICS ─────────────────────────────────────────────────────────
st.subheader("3. Scenario Results")

# Try to load the latest run for this scenario from disk
latest_disk_run = get_latest_scenario_result(selected_scenario_id)

# If we just ran it, use session state, else disk
current_run = st.session_state.get("last_scenario_run")
if current_run and current_run["scenario_id"] != selected_scenario_id:
  current_run = None

run_data = current_run or latest_disk_run

if run_data:
  res_status = run_data.get("overall_scenario_result", "UNKNOWN")
  res_color = "green" if "PASS" in res_status else "red"
  
  st.markdown(f"**Run ID:** `{run_data['run_id']}` | **Time:** `{run_data['timestamp'][:19].replace('T', ' ')}`")
  st.markdown(f"### Acceptance Result: :{res_color}[**{res_status}**]")
  
  if run_data["errors"]:
    st.error("Pipeline Errors Encountered:")
    for e in run_data["errors"]:
      st.code(e)
      
  m = run_data.get("metrics", {})
  if m:
    c3, c4, c5, c6 = st.columns(4)
    c3.metric("High-Risk Areas", m.get("high_risk_count", 0))
    c4.metric("High-Risk Reached", m.get("selected_for_outreach", 0))
    c5.metric("Coverage %", f"{m.get('coverage_pct', 0):.1f}%")
    c6.metric("Fallback Count", m.get("fallback_active_count", 0))
    
    st.markdown("**Fairness Metrics**")
    st.write(f"Max Coverage Gap: `{m.get('max_coverage_gap_pct', 0):.1f}%`")
    st.json(m.get("fairness_coverage_rates", {}))

  with st.expander("Raw Scenario Record"):
    st.json(run_data)
else:
  st.info("No historical results found for this scenario. Click 'Run Scenario' to generate one.")
