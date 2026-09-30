"""
app/pages/risk_map.py – Interactive heat-risk map for Chennai.

Uses the centralized `src.utils.map_utils.prepare_map_dataframe` and
`src.utils.map_utils.scatter_map` helper which transparently handles
the breaking Plotly 6/7 API change and ensures identical data handling
between the Dashboard and the Map page.
"""
import logging
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.services.app_state import AppState
from src.utils.map_utils import (
  prepare_map_dataframe, scatter_map as geo_scatter_map,
  RISK_COLOR_MAP, RISK_ORDER
)
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from app.components.empty_states import show_empty_state, show_pipeline_uninitialized

logger = logging.getLogger(__name__)



apply_global_styles()
render_sidebar()

page_header("Risk Map", "Visualise neighbourhood heat-risk levels and priority outreach areas.", icon=":material/map:")

AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()

df = AppState.get_pipeline_results()
if df is None or df.empty:
  show_pipeline_uninitialized()
  st.stop()

# ── 1. Map Data Preparation ───────────────────────────────────────────────────
# Canonical function ensures exactly the same logic as the main dashboard
map_df, map_info = prepare_map_dataframe(
    df, 
    dataset_signature=AppState.get_active_dataset_info().get("signature", str(len(df)))
)

if map_df.empty:
  show_empty_state(
    icon="location_off",
    title="No Valid Geographic Coordinates",
    description=(
      f"None of the {map_info['total_records']} neighbourhoods have valid "
      "latitude/longitude data for map visualization. Check your dataset."
    ),
  )
  st.stop()

# ── 2. Filters ────────────────────────────────────────────────────────────────
filter_container = st.container()
with filter_container:
  st.markdown(
    "<div style='background:#ffffff;padding:16px 20px;border-radius:12px;"
    "border:1px solid #e2e8f0;margin-bottom:20px;box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>",
    unsafe_allow_html=True,
  )
  f_col1, f_col2, f_col3 = st.columns([3, 3, 2])

  with f_col1:
    # Only show risks that actually exist
    avail_risks = sorted(map_df["_map_risk_level"].unique().tolist())
    display_risks = [r for r in RISK_ORDER if r in avail_risks] + [r for r in avail_risks if r not in RISK_ORDER]
    risk_filter = st.multiselect(
      "Risk Category",
      options=display_risks,
      default=display_risks,
      key="risk_map_risk_filter",
    )

  with f_col2:
    district_options = sorted(map_df["district"].dropna().unique().tolist()) if "district" in map_df.columns else []
    district_filter = st.multiselect(
      "District",
      options=district_options,
      default=district_options,
      key="risk_map_district_filter",
    )

  with f_col3:
    # Pre-compute count respecting current filter selection
    _tmp = map_df.copy()
    if risk_filter:
      _tmp = _tmp[_tmp["_map_risk_level"].isin(risk_filter)]
    if district_filter and "district" in _tmp.columns:
      _tmp = _tmp[_tmp["district"].isin(district_filter)]

    st.markdown(
      f"<div style='padding-top:28px;font-size:0.85rem;color:#475569;'>"
      f"<b>Total Plotted:</b> {len(_tmp)}<br>"
      f"<b>Observation:</b> {map_info['observation_date']}"
      f"</div>",
      unsafe_allow_html=True,
    )

  st.markdown("</div>", unsafe_allow_html=True)

# Apply filters
filtered = map_df.copy()
if risk_filter:
  filtered = filtered[filtered["_map_risk_level"].isin(risk_filter)]
if district_filter and "district" in filtered.columns:
  filtered = filtered[filtered["district"].isin(district_filter)]

# ── 3. Map Rendering ──────────────────────────────────────────────────────────
if filtered.empty:
  st.info("No data matches the current filter selection. Adjust the filters above.")
else:
  # Build hover data dictionary based on what columns actually exist
  hover_cols = {}
  for _hc in ("district", "_map_risk_score", "selected_for_outreach",
        "mobile_population", "confidence_score", "outreach_priority"):
    if _hc in filtered.columns:
      hover_cols[_hc] = True

  try:
    fig_map = geo_scatter_map(
      data_frame=filtered,
      lat="_map_lat",
      lon="_map_lon",
      color="_map_risk_level",
      size="_map_risk_score",
      hover_name="neighbourhood_name" if "neighbourhood_name" in filtered.columns else None,
      hover_data=hover_cols if hover_cols else None,
      color_discrete_map=RISK_COLOR_MAP,
      map_style="carto-positron",
      center=map_info["centre"],
      zoom=10,
      height=620,
      opacity=0.85,
      size_max=22,
    )

    fig_map.update_layout(
      margin=dict(l=0, r=0, t=0, b=0),
      legend=dict(
        title_text="Risk Level",
        orientation="v", yanchor="top", y=0.99,
        xanchor="left", x=0.01,
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#e2e8f0", borderwidth=1,
        font=dict(size=12),
      ),
    )

    # Overlay planned outreach events as blue dots
    sel_map = filtered[filtered.get("selected_for_outreach", pd.Series(False, index=filtered.index)).astype(bool)]
    if len(sel_map) > 0 and hasattr(go, "Scattermap"):
      ht_parts = ["<b>Planned Outreach</b>"]
      if "neighbourhood_name" in sel_map.columns:
        ht_parts.append("%{customdata[0]}")
      fig_map.add_trace(go.Scattermap(
        lat=sel_map["_map_lat"],
        lon=sel_map["_map_lon"],
        mode="markers",
        marker=dict(size=14, color="#3b82f6", symbol="circle"),
        name="Planned Event",
        customdata=sel_map[["neighbourhood_name"]].values if "neighbourhood_name" in sel_map.columns else None,
        hovertemplate="<b>Planned Event</b><br>"
               + ("%{customdata[0]}" if "neighbourhood_name" in sel_map.columns else "")
               + "<extra></extra>",
      ))

    st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": True})

  except Exception as exc:
    logger.error("Map rendering failed: %s", exc, exc_info=True)
    st.error(
      " **Geographic map could not be rendered.**\n\n"
      "A fallback data view is shown below. Check the application logs for technical details."
    )

    # Fallback: bar chart by district + risk
    st.markdown("### Fallback: Risk Distribution by District")
    if "district" in filtered.columns:
      dist_risk = filtered.groupby(["district", "_map_risk_level"]).size().reset_index(name="count")
      fallback_fig = px.bar(
        dist_risk,
        x="district", y="count", color="_map_risk_level",
        color_discrete_map=RISK_COLOR_MAP,
        labels={"count": "Neighbourhoods", "district": "District", "_map_risk_level": "Risk Level"},
        title="Neighbourhood Count by District and Risk Level",
      )
      st.plotly_chart(fallback_fig, use_container_width=True)

# ── 4. Summary Statistics & Data Table ────────────────────────────────────────
if not filtered.empty:
  st.markdown("---")
  st.markdown("### Summary Statistics")
  s_cols = st.columns(4)
  s_cols[0].metric("Neighbourhoods Shown", len(filtered))

  if "selected_for_outreach" in filtered.columns:
    s_cols[1].metric("Selected for Outreach", int(filtered["selected_for_outreach"].sum()))

  extreme_count = int((filtered["_map_risk_level"].isin(["EXTREME", "VERY HIGH"])).sum())
  s_cols[2].metric("Extreme / Very High Risk", extreme_count)

  s_cols[3].metric("Avg Risk Score", f"{filtered['_map_risk_score'].mean():.2f}")

  st.markdown("### Data Table")
  table_cols = [c for c in [
    "neighbourhood_name", "district", "_map_risk_level",
    "_map_risk_score", "selected_for_outreach", "_map_lat", "_map_lon"
  ] if c in filtered.columns]
  
  # Rename for display
  display_df = filtered[table_cols].rename(columns={
    "neighbourhood_name": "Neighbourhood",
    "district": "District",
    "_map_risk_level": "Risk Level",
    "_map_risk_score": "Risk Score",
    "selected_for_outreach": "Planned Action",
    "_map_lat": "Lat",
    "_map_lon": "Lon"
  })
  
  st.dataframe(
    display_df.sort_values(by="Risk Score" if "Risk Score" in display_df.columns else "Neighbourhood", ascending=False),
    use_container_width=True,
    hide_index=True,
  )
