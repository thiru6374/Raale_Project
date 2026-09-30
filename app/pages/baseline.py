"""
app/pages/baseline.py – Temperature-Only Baseline Model UI.
sys.path is set by .streamlit/config.toml – no hacks needed here.
"""
import os
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import pandas as pd
import plotly.express as px

from src.services.app_state import AppState
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("baseline_ui")

page_header("Baseline vs Proposed", 
  "This page displays the isolated Temperature-Only prioritisation baseline. "
  "It ranks neighbourhoods purely by temperature and does NOT include vulnerability, "
  "fairness, or service-access data.", icon=":material/stacked_bar_chart:")

apply_global_styles()
render_sidebar()

AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()

# Get baseline results from session state (run during the pipeline)
res = AppState.get_full_results()
baseline_result = res.get("baseline_results") if res else None
status_val = getattr(baseline_result.status, "value", baseline_result.status) if baseline_result else None
if baseline_result is None or status_val != "COMPLETED":
  st.error("Baseline model did not complete successfully.")
  st.stop()

# ── Metrics ───────────────────────────────────────────────────────────────────
st.subheader("Baseline Execution Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Total Ranked",    baseline_result.summary.ranked_neighbourhoods)
c2.metric("Data Insufficient",  baseline_result.summary.data_insufficient_neighbourhoods)
c3.metric("Selected (Top-N)",  baseline_result.summary.selected_neighbourhoods)

if baseline_result.summary.warnings:
  st.warning("Warnings occurred during Baseline execution:")
  for err in baseline_result.summary.warnings:
    st.write(f"- {err}")

# ── Data Table ────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Ranked Neighbourhoods")

records = [r.model_dump() for r in baseline_result.records]
if not records:
  st.info("No records to display.")
  st.stop()

df_base = pd.DataFrame(records)

# Highlight selected
def highlight_selected(val):
  return 'background-color: #00CC96' if val else ''

st.dataframe(
  df_base.style.map(highlight_selected, subset=['baseline_selected']),
  use_container_width=True,
  height=400,
)

# ── Chart ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Temperature Distribution (Selected vs Unselected)")

# Filter out unranked/insufficient records for plotting
plot_df = df_base[df_base["baseline_status"] == "RANKED"].copy()

if not plot_df.empty and "baseline_temperature_value" in plot_df.columns:
  fig = px.histogram(
    plot_df, x="baseline_temperature_value", nbins=20,
    color="baseline_selected", barmode="overlay",
    title="Baseline Temperature Selection",
    labels={
      "baseline_temperature_value": "Temperature (°C)",
      "baseline_selected": "Selected (Top-N)",
    },
    color_discrete_map={True: "#00CC96", False: "#636EFA"},
    template="plotly_dark",
  )
  fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
  st.plotly_chart(fig, use_container_width=True)
else:
  st.info("Insufficient data for plotting.")
