"""
app/pages/risk_map.py  –  Interactive heat-risk map for Chennai.

Uses the centralized `src.utils.map_utils.scatter_map` helper which
transparently handles the breaking Plotly 6/7 API change
(px.scatter_mapbox → px.scatter_map) without crashing the page.
"""
import logging
import streamlit as st
import plotly.express as px
import pandas as pd

from src.services.app_state import AppState
from src.utils.map_utils import scatter_map as geo_scatter_map
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from app.components.empty_states import show_empty_state, show_pipeline_uninitialized

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Risk Map", page_icon="", layout="wide")

apply_global_styles()
render_sidebar()

page_header(" Risk Map", "Visualise neighbourhood heat-risk levels and priority outreach areas.", icon=":material/map:")

AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

df = AppState.get_pipeline_results()
if df is None or df.empty:
    show_pipeline_uninitialized()
    st.stop()

# ── Schema Normalisation ──────────────────────────────────────────────────────
# Ensure the canonical UI columns exist, mapping from raw pipeline columns.
df = df.copy()

# 1. risk_level (normalized UI label from internal multi_factor_risk_category)
if "risk_level" not in df.columns:
    if "multi_factor_risk_category" in df.columns:
        _risk_map = {"EXTREME": "EXTREME", "HIGH": "HIGH", "MODERATE": "MODERATE", "LOW": "LOW"}
        df["risk_level"] = df["multi_factor_risk_category"].map(_risk_map).fillna("LOW")
    else:
        df["risk_level"] = "UNKNOWN"

# 2. risk_score (display name for the numeric score)
if "risk_score" not in df.columns:
    if "multi_factor_risk_score" in df.columns:
        df["risk_score"] = df["multi_factor_risk_score"]
    else:
        df["risk_score"] = 0.5

# 3. Ensure risk_score is positive (required for size parameter in scatter map)
df["risk_score"] = df["risk_score"].fillna(0.1).clip(lower=0.01)

# 4. neighbourhood_name fallback
if "neighbourhood_name" not in df.columns and "neighbourhood_id" in df.columns:
    df["neighbourhood_name"] = df["neighbourhood_id"]

# ── Coordinate Validation ────────────────────────────────────────────────────
# Use the is_valid_geo flag set by the spatial validator, or derive it manually.
if "is_valid_geo" in df.columns:
    invalid_mask = ~df["is_valid_geo"].fillna(False)
else:
    has_lat = "latitude" in df.columns
    has_lon = "longitude" in df.columns
    if has_lat and has_lon:
        invalid_mask = (
            df["latitude"].isna()
            | df["longitude"].isna()
            | (df["latitude"].abs() > 90)
            | (df["longitude"].abs() > 180)
        )
    else:
        invalid_mask = pd.Series([True] * len(df), index=df.index)

invalid_count = int(invalid_mask.sum())
if invalid_count > 0:
    st.warning(
        f" **{invalid_count}** neighbourhood(s) cannot be displayed on the map because "
        "geographic coordinates are missing or invalid. They are still included in all "
        "other planning, analysis, and reporting pages."
    )

map_df = df[~invalid_mask].copy()

if map_df.empty:
    show_empty_state(
        icon="",
        title="No Valid Geographic Coordinates",
        description=(
            "No neighbourhoods with valid latitude/longitude data are currently "
            "available for map visualization. All records are still available in the "
            "Outreach Planner, Fairness Analysis, and Dashboard pages."
        ),
    )
    st.stop()

# ── Filters ───────────────────────────────────────────────────────────────────
# Dynamically determine available risk categories from the real dataset
all_risk_cats = sorted(map_df["risk_level"].dropna().unique().tolist())
# Canonical ordering for display
_cat_order = ["EXTREME", "HIGH", "MODERATE", "LOW", "VERY HIGH", "MEDIUM", "UNKNOWN"]
ordered_cats = [c for c in _cat_order if c in all_risk_cats] + [
    c for c in all_risk_cats if c not in _cat_order
]

filter_container = st.container()
with filter_container:
    st.markdown(
        "<div style='background:#ffffff;padding:16px 20px;border-radius:12px;"
        "border:1px solid #e2e8f0;margin-bottom:20px;'>",
        unsafe_allow_html=True,
    )
    f_col1, f_col2, f_col3 = st.columns([3, 3, 2])

    with f_col1:
        risk_filter = st.multiselect(
            "Risk Category",
            options=ordered_cats,
            default=ordered_cats,
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
        _tmp_filtered = map_df.copy()
        if risk_filter:
            _tmp_filtered = _tmp_filtered[_tmp_filtered["risk_level"].isin(risk_filter)]
        if district_filter and "district" in _tmp_filtered.columns:
            _tmp_filtered = _tmp_filtered[_tmp_filtered["district"].isin(district_filter)]
        st.markdown(
            f"<div style='padding-top:28px'><b>Total Plotted:</b> {len(_tmp_filtered)}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

# Apply filters
filtered = map_df.copy()
if risk_filter:
    filtered = filtered[filtered["risk_level"].isin(risk_filter)]
if district_filter and "district" in filtered.columns:
    filtered = filtered[filtered["district"].isin(district_filter)]

# ── Map Rendering ─────────────────────────────────────────────────────────────
if filtered.empty:
    st.info("ℹ No data matches the current filter selection. Adjust the filters above.")
else:
    # Color palette consistent with rest of application
    color_map = {
        "EXTREME":  "#ef4444",
        "VERY HIGH":"#dc2626",
        "HIGH":     "#f97316",
        "MODERATE": "#f59e0b",
        "MEDIUM":   "#eab308",
        "LOW":      "#10b981",
        "UNKNOWN":  "#94a3b8",
    }

    # Build hover data dict — only include columns that actually exist
    hover_candidates = {
        "district":        True,
        "risk_score":      ":.2f",
        "outreach_priority": True,
        "confidence_score": ":.2f",
        "latitude":        False,
        "longitude":       False,
    }
    hover_data = {k: v for k, v in hover_candidates.items() if k in filtered.columns}

    # Chennai city centre
    center = {"lat": 13.05, "lon": 80.20}

    try:
        fig = geo_scatter_map(
            data_frame=filtered,
            lat="latitude",
            lon="longitude",
            color="risk_level",
            size="risk_score",
            hover_name="neighbourhood_name" if "neighbourhood_name" in filtered.columns else None,
            hover_data=hover_data,
            color_discrete_map=color_map,
            map_style="carto-positron",
            center=center,
            zoom=10,
            height=620,
            opacity=0.88,
            size_max=22,
        )

        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(
                title_text="Risk Level",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#e2e8f0",
                borderwidth=1,
                font=dict(size=12),
            ),
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

    except Exception as exc:
        # Never show a raw traceback — log it for developers, show a clean fallback
        logger.error("Map rendering failed: %s", exc, exc_info=True)

        st.error(
            " **Geographic map could not be rendered.**\n\n"
            "A fallback data view is shown below. Check the application logs for technical details."
        )

        # ── Fallback: bar chart by district + risk ────────────────────────────
        st.markdown("### Fallback: Risk Distribution by District")
        if "district" in filtered.columns:
            dist_risk = (
                filtered.groupby(["district", "risk_level"])
                .size()
                .reset_index(name="count")
            )
            fallback_fig = px.bar(
                dist_risk,
                x="district", y="count", color="risk_level",
                color_discrete_map=color_map,
                labels={"count": "Neighbourhoods", "district": "District", "risk_level": "Risk Level"},
                title="Neighbourhood Count by District and Risk Level",
                template="plotly_dark",
            )
            fallback_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fallback_fig, use_container_width=True)

        # ── Fallback table ────────────────────────────────────────────────────
        st.markdown("### Data Table")
        table_cols = [
            c for c in [
                "neighbourhood_name", "district", "risk_level",
                "risk_score", "selected_for_outreach", "latitude", "longitude"
            ]
            if c in filtered.columns
        ]
        st.dataframe(
            filtered[table_cols].sort_values("risk_score", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

# ── Summary Statistics ────────────────────────────────────────────────────────
if not filtered.empty:
    st.markdown("---")
    st.markdown("### Summary")
    s_cols = st.columns(4)
    s_cols[0].metric("Neighbourhoods Shown", len(filtered))

    if "selected_for_outreach" in filtered.columns:
        s_cols[1].metric("Selected for Outreach", int(filtered["selected_for_outreach"].sum()))

    extreme_count = int((filtered["risk_level"].isin(["EXTREME", "VERY HIGH"])).sum())
    s_cols[2].metric("Extreme / Very High Risk", extreme_count)

    if "risk_score" in filtered.columns:
        s_cols[3].metric("Avg Risk Score", f"{filtered['risk_score'].mean():.2f}")
