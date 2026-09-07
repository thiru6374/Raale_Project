"""
app/main.py  –  Executive Dashboard for the Neighbourhood Heat-Risk Planner.
Primary landing page of the application.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from src.services.app_state import AppState
from src.services.system_health_service import SystemHealthService

from app.components.layout import apply_global_styles, status_badge
from app.components.sidebar import render_sidebar
from app.components.cards import html_card
from app.components.empty_states import show_pipeline_uninitialized

st.set_page_config(
    page_title="Executive Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply unified design system
apply_global_styles()
render_sidebar()

# Initialize System — ensures pipeline data is available from ANY page entry point
AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

# Retrieve Data from centralized state
res = AppState.get_full_results()
pipeline_df = res.get("pipeline_results")
fairness = res.get("fairness_warnings", [])
health = SystemHealthService.get_system_health()

# ── Top Header ───────────────────────────────────────────────────────────────
col_title, col_actions = st.columns([3, 1])
with col_title:
    st.markdown("<h1 style='margin-bottom: 0px;'><span class='material-symbols-rounded' style='font-size: 2.2rem; vertical-align: bottom;'>dashboard</span> Heat-Risk Communication & Outreach Planner</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 1.1rem;'>AI-Assisted Decision Support for Targeted, Timely, and Fair Neighbourhood Outreach</p>", unsafe_allow_html=True)

with col_actions:
    st.write("")
    if st.button("🔄 Run / Refresh Analysis", use_container_width=True, type="primary"):
        with st.spinner("Running deep analysis..."):
            # Force re-run of the full pipeline
            AppState.initialize_application(force_refresh=True)
            st.rerun()

st.markdown("<hr style='margin-top: 5px; margin-bottom: 25px; border: 0; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

if pipeline_df is None or pipeline_df.empty:
    show_pipeline_uninitialized()
    st.stop()

# ── Validate schema: ensure risk_level column exists ────────────────────────
# risk_level is normalized by pipeline_service: EXTREME->VERY HIGH, HIGH->HIGH, etc.
if "risk_level" not in pipeline_df.columns:
    if "multi_factor_risk_category" in pipeline_df.columns:
        risk_map = {"EXTREME": "VERY HIGH", "HIGH": "HIGH", "MODERATE": "MEDIUM", "LOW": "LOW"}
        pipeline_df["risk_level"] = pipeline_df["multi_factor_risk_category"].map(risk_map).fillna("LOW")
    else:
        pipeline_df["risk_level"] = "LOW"

# ── Prepare Metrics ──────────────────────────────────────────────────────────
total_areas = len(pipeline_df)
high_risk_df = pipeline_df[pipeline_df["risk_level"].isin(["HIGH", "VERY HIGH"])]
selected_df = pipeline_df[pipeline_df["selected_for_outreach"] == True] if "selected_for_outreach" in pipeline_df.columns else pd.DataFrame()

high_risk_count = len(high_risk_df)
selected_count = len(selected_df)

# Population metrics — gracefully handle missing columns
def _safe_sum(df, col):
    return int(df[col].sum()) if col in df.columns else 0

def _group_population(df, group_col, pop_col="total_population"):
    """Sum population for rows where group_col is True."""
    if group_col not in df.columns:
        return 0
    mask = df[group_col].astype(bool)
    if pop_col in df.columns:
        return int(df.loc[mask, pop_col].sum())
    return int(mask.sum())  # fall back to count of neighborhoods

# Mobile population: sum total_population for neighborhoods flagged as group_mobile
mobile_total   = _group_population(pipeline_df, "group_mobile")
mobile_reached = _group_population(selected_df, "group_mobile")

# Also accumulate mobile_population field if present (individual mobile persons)
if "mobile_population" in pipeline_df.columns:
    mobile_total   = int(pipeline_df["mobile_population"].sum())
    mobile_reached = _safe_sum(selected_df, "mobile_population")

mobile_pct = (mobile_reached / mobile_total * 100) if mobile_total > 0 else 0

# Low service access: sum total_population for neighborhoods flagged as group_low_service_access
lsa_total   = _group_population(pipeline_df, "group_low_service_access")
lsa_reached = _group_population(selected_df, "group_low_service_access")
lsa_pct     = (lsa_reached / lsa_total * 100) if lsa_total > 0 else 0

# Derive confidence from available data if possible
confidence_col = "confidence_score"
avg_confidence = pipeline_df[confidence_col].mean() if confidence_col in pipeline_df.columns else None

capacity = 25

# ── Metric Row ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    html_card("High-Risk Neighbourhoods",
              f"<span style='color: #ef4444'>{selected_count}</span> / {high_risk_count}",
              "Reached in plan", "warning")
with c2:
    html_card("Mobile Population Reached",
              f"{int(mobile_reached):,} <span style='font-size: 1.2rem; color: #64748b'>/ {int(mobile_total):,}</span>",
              f"{mobile_pct:.1f}% covered" if mobile_total > 0 else "Data not available", "smartphone")
with c3:
    html_card("Low Service Access Reached",
              f"{int(lsa_reached):,} <span style='font-size: 1.2rem; color: #64748b'>/ {int(lsa_total):,}</span>",
              f"{lsa_pct:.1f}% covered" if lsa_total > 0 else "Data not available", "local_hospital")
with c4:
    stat = "Within Capacity" if selected_count <= capacity else "Over Capacity"
    html_card("Planned Outreach Events", f"{selected_count}", f"{stat} (Cap: {capacity})", "calendar_today")
with c5:
    conf_text = f"{avg_confidence:.2f}" if avg_confidence is not None else "N/A"
    html_card("Avg. Confidence Score", conf_text, "Based on data completeness", "check_circle")

st.markdown("<br>", unsafe_allow_html=True)

# ── Main Content Layout ───────────────────────────────────────────────────────
row1_c1, row1_c2 = st.columns([4, 3])

with row1_c1:
    st.markdown("### Top Priority Neighbourhoods")
    if not selected_df.empty:
        sort_col = "risk_score" if "risk_score" in selected_df.columns else (
            "multi_factor_risk_score" if "multi_factor_risk_score" in selected_df.columns else None
        )
        top_n = selected_df.sort_values(by=sort_col, ascending=False).head(5) if sort_col else selected_df.head(5)

        display_cols_candidates = [
            "neighbourhood_id", "neighbourhood_name", "district",
            sort_col, "risk_level", "mobile_population_count"
        ]
        display_cols = [c for c in display_cols_candidates if c and c in top_n.columns]
        display_df = top_n[display_cols].copy()

        rename_map = {
            "neighbourhood_id": "ID",
            "neighbourhood_name": "Neighbourhood",
            sort_col: "Risk Score",
            "risk_level": "Risk Level",
            "mobile_population_count": "Mobile Pop."
        }
        display_df.rename(columns={k: v for k, v in rename_map.items() if k in display_df.columns}, inplace=True)
        if "Risk Score" in display_df.columns:
            display_df["Risk Score"] = display_df["Risk Score"].round(2)
        if "Mobile Pop." in display_df.columns:
            display_df["Mobile Pop."] = display_df["Mobile Pop."].astype(int)

        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No neighbourhoods selected for outreach yet. Run the analysis.")

with row1_c2:
    st.markdown("### Baseline vs Proposed Coverage")
    baseline_res = res.get("baseline_results")
    if baseline_res and hasattr(baseline_res, 'selected_neighbourhoods'):
        base_count = len(baseline_res.selected_neighbourhoods)
        base_pct   = (base_count / total_areas * 100) if total_areas > 0 else 0
        prop_pct   = (selected_count / total_areas * 100) if total_areas > 0 else 0

        comp_data = pd.DataFrame({
            "Model": ["Baseline (Temp Only)", "Proposed (Multi-factor)"],
            "Coverage %": [base_pct, prop_pct]
        })
        fig = px.bar(comp_data, x="Model", y="Coverage %", color="Model",
                     color_discrete_sequence=["#ef4444", "#10b981"], height=250)
        fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), showlegend=False,
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Baseline comparison not available yet.")

st.markdown("<br>", unsafe_allow_html=True)
row2_c1, row2_c2 = st.columns([1, 1])

with row2_c1:
    st.markdown("### Fairness & Bias Summary")
    if fairness:
        for w in fairness[:3]:
            if isinstance(w, dict):
                grp = w.get("group", "Unknown")
                gap = w.get("coverage_gap", 0)
                st.markdown(status_badge(f" Bias in '{grp}' — gap: {gap:.1%}", "warning"), unsafe_allow_html=True)
                st.markdown("<div style='margin-top: 5px'></div>", unsafe_allow_html=True)
    else:
        st.markdown(status_badge(" No fairness violations detected", "success"), unsafe_allow_html=True)

with row2_c2:
    st.markdown("### System Alerts")
    overall = health.get("overall_status", "UNKNOWN") if health else "UNKNOWN"
    if overall == "HEALTHY":
        st.markdown(status_badge("System running optimally", "success"), unsafe_allow_html=True)
    else:
        st.markdown(status_badge(f"System status: {overall}", "warning"), unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 5px'></div>", unsafe_allow_html=True)
    if fairness:
        st.markdown(status_badge(f"{len(fairness)} fairness warning(s) detected", "warning"), unsafe_allow_html=True)
    else:
        st.markdown(status_badge("Fairness check passed", "success"), unsafe_allow_html=True)
