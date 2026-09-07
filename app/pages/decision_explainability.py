"""
app/pages/decision_explainability.py  –  Decision Explainability UI.

Lets district planners select any neighbourhood and see a plain-language
explanation of WHY it has its risk level and WHY it was (or was not) selected.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import pandas as pd

from src.services.app_state import AppState
from src.explainability.risk_explainer import explain_risk
from src.explainability.recommendation_explainer import explain_recommendation
from src.explainability.decision_trace import create_decision_trace
from src.governance.audit_logger import AuditLogger

st.set_page_config(page_title="Decision Explainability", page_icon="", layout="wide")

page_header(" Decision Explainability", subtitle=None, icon=":material/search_insights:")
st.markdown(
    "Understand exactly **why** a neighbourhood has its risk classification "
    "and **why** it was or was not selected for outreach."
)

apply_global_styles()
render_sidebar()

AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

df = AppState.get_pipeline_results()
if df is None or df.empty:
    st.warning("No pipeline results available. Refresh the pipeline first.")
    st.stop()

res = AppState.get_full_results()
fairness_warnings = res.get("fairness_warnings", [])
dataset_id        = res.get("dataset_id", "N/A")
strategy          = st.session_state.get("optimization_strategy", "COVERAGE_FOCUSED")

# ── Neighbourhood Selector ────────────────────────────────────────────────────
names = df["neighbourhood_name"].tolist() if "neighbourhood_name" in df.columns else df["neighbourhood_id"].tolist()
choice = st.selectbox("Select a Neighbourhood to Explain", names)

col_lookup = "neighbourhood_name" if "neighbourhood_name" in df.columns else "neighbourhood_id"
row = df[df[col_lookup] == choice].iloc[0]

st.markdown("---")

# ── SECTION A: DATA PROVENANCE () ────────────────────────────────────
st.subheader("Data Provenance & Trust")
provider_meta = res.get("provider_metadata", {})
source_type = provider_meta.get("source_type", "UNKNOWN")
is_valid_geo = row.get("is_valid_geo", True)

c_prov1, c_prov2, c_prov3 = st.columns(3)
with c_prov1:
    st.markdown(f"**Primary Source:** {source_type}")
    if source_type == "HYBRID" and "domain_provenance" in provider_meta:
        st.caption(f"Temp: {provider_meta['domain_provenance'].get('temperature')}")
with c_prov2:
    st.markdown(f"**Freshness:** {provider_meta.get('freshness', 'UNKNOWN')}")
with c_prov3:
    if is_valid_geo:
        st.markdown("**Geographic Quality:**  VALID")
    else:
        status = row.get("geo_validation_status", "UNKNOWN")
        st.markdown(f"**Geographic Quality:**  {status}")

st.markdown("---")

# ── SECTION B: WHY IS THIS AREA HIGH RISK? ───────────────────────────────────
st.subheader("Why Is This Area High Risk?")

risk_exp = explain_risk(row)
risk_cat  = risk_exp["risk_category"]
risk_scr  = risk_exp["risk_score"]

cat_color = {"EXTREME": "🔴", "HIGH": "🟠", "MODERATE": "🟡", "LOW": "🟢"}.get(risk_cat, "⚪")
st.markdown(f"### {cat_color} Risk Level: **{risk_cat}**   |   Score: `{risk_scr:.3f}`")
st.info(risk_exp["narrative"])

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Top Contributing Factors**")
    for f in risk_exp["top_factors"]:
        st.write(f"- {f}")
with c2:
    st.markdown("**Factor Weights Used**")
    for factor, contrib in risk_exp["factor_contributions"].items():
        st.write(f"- {factor.replace('_', ' ').title()}: `{contrib:.3f}`")

if risk_exp["data_gaps"]:
    with st.expander(" Data Gaps Affecting This Explanation"):
        for gap in risk_exp["data_gaps"]:
            st.write(f"- {gap}")

st.markdown("---")

# ── SECTION B: WHY SELECTED / NOT SELECTED? ──────────────────────────────────
st.subheader("Why Was This Area Selected (or Not) for Outreach?")

rec_exp = explain_recommendation(row, fairness_warnings)

if rec_exp["is_selected"]:
    st.success(f" **SELECTED** for outreach — Priority: {rec_exp['priority']}")
elif rec_exp["priority"] == "WAITLIST_HIGH_RISK":
    st.warning(" **WAITLISTED** — High risk, but not reached due to capacity constraints.")
else:
    st.error(f" **NOT SELECTED** — Priority: {rec_exp['priority']}")

st.info(rec_exp["narrative"])

c3, c4 = st.columns(2)
with c3:
    if rec_exp["is_selected"]:
        st.markdown("**Reasons for Selection**")
        for r in rec_exp["selection_reasons"]:
            st.write(f"- {r}")
    else:
        st.markdown("**Reasons Not Selected**")
        for r in rec_exp["not_selected_reasons"]:
            st.write(f"- {r}")
with c4:
    st.markdown("**Constraints Applied**")
    for c in rec_exp["constraints"]:
        st.write(f"- {c}")

st.write(f"**Fairness Context:** {rec_exp['fairness_context']}")
st.write(f"**Trust:** {rec_exp['trust_explanation']}")
st.write(f"**Timing:** {rec_exp['timing']}")

st.markdown("---")

# ── SECTION C: FULL DECISION TRACE ───────────────────────────────────────────
with st.expander(" Full Decision Trace (Advanced)"):
    try:
        audit_log = AuditLogger().read_logs()
    except Exception:
        audit_log = []

    trace = create_decision_trace(
        row,
        dataset_id=dataset_id,
        strategy=strategy,
        fairness_warnings=fairness_warnings,
        audit_logs=audit_log,
    )
    st.json(trace)
