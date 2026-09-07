"""
app/pages/dashboard.py  –  District-level overview dashboard.
sys.path is set by .streamlit/config.toml – no hacks needed here.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import plotly.express as px

from src.services.app_state import AppState

page_header("System Overview", "System overview and pipeline performance metrics.", icon=":material/monitoring:")

apply_global_styles()
render_sidebar()

AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

df       = AppState.get_pipeline_results()
warnings = AppState.get_fairness_warnings()

if df is None:
    st.stop()

# ── District bar chart ───────────────────────────────────────────────────────
st.subheader("Chennai District Overview")
district_risk = (
    df.groupby("district")
    .agg(
        avg_risk  =("multi_factor_risk_score",    "mean"),
        extreme   =("multi_factor_risk_category", lambda x: (x == "EXTREME").sum()),
        selected  =("selected_for_outreach",      "sum"),
        total     =("neighbourhood_id",           "count"),
    )
    .reset_index()
    .sort_values("avg_risk", ascending=False)
)

fig1 = px.bar(
    district_risk, x="district", y="avg_risk", color="avg_risk",
    color_continuous_scale="Reds",
    title="Average Multi-Factor Risk Score by District",
    template="plotly_dark",
    labels={"avg_risk": "Avg Risk Score", "district": "District"},
)
fig1.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    coloraxis_showscale=False,
)
st.plotly_chart(fig1, use_container_width=True)

# ── Category pie + confidence scatter ────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    fig2 = px.pie(
        df, names="multi_factor_risk_category", title="Risk Category Breakdown",
        color="multi_factor_risk_category",
        color_discrete_map={
            "EXTREME": "#FF4B4B", "HIGH": "#FF8C00",
            "MODERATE": "#FFC107", "LOW": "#00CC96",
        },
        template="plotly_dark",
    )
    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

with c2:
    fig3 = px.scatter(
        df, x="confidence_score", y="multi_factor_risk_score",
        color="outreach_priority",
        title="Confidence vs Risk Score",
        labels={
            "confidence_score":         "Confidence Score",
            "multi_factor_risk_score":  "Risk Score",
        },
        template="plotly_dark",
    )
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Fairness warnings ────────────────────────────────────────────────────────
if warnings:
    st.markdown("---")
    st.subheader("Active Fairness Warnings")
    for w in warnings:
        st.warning(w["message"])
