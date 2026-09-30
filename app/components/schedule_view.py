"""
app/components/schedule_view.py

Geographic Clustering & Outreach Schedule visualisation component.

Renders:
 1. Daily Team Utilization table
 2. Cluster map (coloured by team assignment)
 3. Detailed route assignment table
 4. Isolated / unassigned neighbourhood warnings
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from src.services.app_state import AppState
from src.utils.logger import get_logger

logger = get_logger("schedule_view")


def _load_team_schedules(df: pd.DataFrame) -> pd.DataFrame:
  """Try to recover team-schedule metadata from the persisted run store."""
  try:
    if "optimization_run_id" not in df.columns or df["optimization_run_id"].isna().all():
      return pd.DataFrame()
    run_id = str(df["optimization_run_id"].dropna().iloc[0])
    from src.optimisation.run_store import OptimizationRunStore
    run_data = OptimizationRunStore().get(run_id)
    records = run_data.get("metrics", {}).get("team_schedules", [])
    return pd.DataFrame(records) if records else pd.DataFrame()
  except Exception as exc:
    logger.debug("Could not load team schedules: %s", exc)
    return pd.DataFrame()


def render_schedule_view(df: pd.DataFrame = None, show_map: bool = True):
  """
  Full schedule rendering: utilization table + cluster map + route detail.

  Parameters
  ----------
  df     Pipeline DataFrame (defaults to AppState result).
  show_map  Whether to render the cluster map (can be toggled by callers).
  """
  if df is None:
    df = AppState.get_pipeline_results()

  if df is None or df.empty or "assigned_team" not in df.columns:
    return # silently skip — the page should handle empty state messaging

  selected_df = df[df["selected_for_outreach"] == True].copy()

  if selected_df.empty:
    st.info("No neighbourhoods selected for outreach — no schedule to display.")
    return

  st.subheader(" Geographically Clustered Outreach Schedule")

  # ── 1. Daily Team Utilization ─────────────────────────────────────────────
  team_schedules = _load_team_schedules(df)

  if not team_schedules.empty:
    st.markdown("##### Team Utilization")

    def _color_status(val):
      if val == "OVERLOADED":
        return "color: #ef4444; font-weight: bold"
      if val == "HEALTHY":
        return "color: #10b981; font-weight: bold"
      return "color: #f59e0b; font-weight: bold"

    try:
      styled = team_schedules.style.map(_color_status, subset=["Status"])
      st.dataframe(styled, use_container_width=True, hide_index=True)
    except Exception:
      st.dataframe(team_schedules, use_container_width=True, hide_index=True)

    # Bar chart of utilization
    if "Utilization (%)" in team_schedules.columns and "Team" in team_schedules.columns:
      fig = px.bar(
        team_schedules,
        x="Team",
        y="Utilization (%)",
        color="Status",
        color_discrete_map={
          "HEALTHY": "#10b981",
          "OVERLOADED": "#ef4444",
          "IDLE": "#f59e0b",
        },
        title="Team Utilization (%)",
        template="plotly_dark",
        text="Utilization (%)",
      )
      fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
      fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(range=[0, 120]),
        showlegend=True,
      )
      st.plotly_chart(fig, use_container_width=True)

  # ── 2. Cluster Map ────────────────────────────────────────────────────────
  if show_map:
    geo_df = selected_df.dropna(subset=["latitude", "longitude"]).copy()
    invalid_count = len(selected_df) - len(geo_df)

    if not geo_df.empty and "assigned_team" in geo_df.columns:
      st.markdown("##### Cluster Map — Team Assignments")
      from src.utils.map_utils import scatter_map as geo_scatter_map

      hover_candidates = {
        "district": True,
        "multi_factor_risk_category": True,
        "outreach_date": True,
        "start_time": True,
        "end_time": True,
        "latitude": False,
        "longitude": False,
      }
      hover_data = {k: v for k, v in hover_candidates.items() if k in geo_df.columns}

      try:
        fig_map = geo_scatter_map(
          data_frame=geo_df,
          lat="latitude",
          lon="longitude",
          color="assigned_team",
          hover_name="neighbourhood_name" if "neighbourhood_name" in geo_df.columns else None,
          hover_data=hover_data,
          map_style="carto-positron",
          center={"lat": geo_df["latitude"].mean(), "lon": geo_df["longitude"].mean()},
          zoom=10,
          height=520,
          opacity=0.9,
          size_max=16,
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_map, use_container_width=True)
      except Exception as exc:
        st.warning(f"Map rendering failed: {exc}")

    if invalid_count > 0:
      st.warning(
        f" {invalid_count} selected neighbourhood(s) have invalid GPS and are "
        "excluded from the map but included in the route table below."
      )

  # ── 3. Detailed Route Assignments ─────────────────────────────────────────
  st.markdown("##### Route Assignments")
  disp_cols = [
    "neighbourhood_name", "district", "assigned_team",
    "outreach_date", "start_time", "end_time",
    "multi_factor_risk_category", "cluster_id", "is_isolated",
  ]
  avail_cols = [c for c in disp_cols if c in selected_df.columns]

  if "assigned_team" in selected_df.columns and "start_time" in selected_df.columns:
    selected_df = selected_df.sort_values(["assigned_team", "start_time"])

  st.dataframe(
    selected_df[avail_cols],
    use_container_width=True,
    hide_index=True,
  )

  # ── 4. Isolated / Overloaded Warnings ─────────────────────────────────────
  if "is_isolated" in df.columns:
    isolated = df[df["is_isolated"] == True]
    if not isolated.empty:
      st.error(
        f" {len(isolated)} neighbourhood(s) could not be scheduled due to team "
        "capacity overflow and have been marked as isolated. They remain in the "
        "WAITLIST_HIGH_RISK queue for the next planning cycle."
      )
