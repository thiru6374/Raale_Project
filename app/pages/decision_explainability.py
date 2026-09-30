"""
app/pages/decision_explainability.py — Model Explainability & Sensitivity

For every selected neighbourhood displays:
 risk score · risk level · contributing factors · normalized values · weights ·
 contribution · recommended action · population impact · travel impact ·
 fairness impact · constraint status · confidence · fallback status

Includes:
 - Full factor breakdown table (from formal model JSON)
 - 7-parameter sensitivity analysis with metric-level impact
 - Full decision trace
 - Link to methodology page
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from src.services.app_state import AppState
from src.explainability.risk_explainer import explain_risk
from src.explainability.recommendation_explainer import explain_recommendation
from src.explainability.decision_trace import create_decision_trace
from src.governance.audit_logger import AuditLogger
from src.config.settings import settings


apply_global_styles()
render_sidebar()

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
 .factor-card {
  background:#0f172a; border:1px solid #1e3a5f; border-radius:8px;
  padding:14px 18px; margin-bottom:10px;
 }
 .impact-row {
  display:flex; gap:10px; margin-bottom:8px; flex-wrap:wrap;
 }
 .impact-chip {
  background:#1e293b; border:1px solid #334155; border-radius:20px;
  padding:4px 12px; font-size:0.78rem; color:#94a3b8;
 }
 .impact-chip b { color:#e2e8f0; }
 .sens-header { color:#6366f1; font-weight:700; font-size:1.0rem; }
 .method-box {
  background:#0f172a; border:1px solid #334155; border-radius:6px;
  padding:16px 20px; margin-bottom:12px; font-size:0.88rem;
 }
</style>
""", unsafe_allow_html=True)

page_header(" Decision Explainability", "Full transparency into risk scores, selection decisions, and model sensitivity.", icon=":material/search_insights:")

AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()

df = AppState.get_pipeline_results()
if df is None or df.empty:
  st.warning("No pipeline results available. Run the pipeline first.")
  st.stop()

res       = AppState.get_full_results()
fairness_warnings= res.get("fairness_warnings", [])
dataset_id    = res.get("dataset_id", "N/A")
strategy     = st.session_state.get("optimization_strategy", "COVERAGE_FOCUSED")

# ── Neighbourhood Selector ─────────────────────────────────────────────────────
col_lookup = "neighbourhood_name" if "neighbourhood_name" in df.columns else "neighbourhood_id"
names = df[col_lookup].tolist()

view_mode = st.radio("View Mode", ["All Neighbourhoods", "Selected Only"], horizontal=True)
if view_mode == "Selected Only" and "selected_for_outreach" in df.columns:
  filtered_df = df[df["selected_for_outreach"] == True]
  names = filtered_df[col_lookup].tolist()
else:
  filtered_df = df

choice = st.selectbox("Select a Neighbourhood to Explain", names)
row = filtered_df[filtered_df[col_lookup] == choice].iloc[0]

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION A: COMPLETE EXPLAINABILITY CARD
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("A · Full Decision Card")

risk_exp = explain_risk(row)
rec_exp = explain_recommendation(row, fairness_warnings)

is_selected = bool(row.get("selected_for_outreach", False))
risk_cat   = risk_exp["risk_category"]
risk_score  = risk_exp["risk_score"]
conf_score  = float(row.get("confidence_score", 1.0))
conf_level  = row.get("confidence_level", "UNKNOWN")
fallback   = row.get("fallback_status", "STANDARD")
override_st = row.get("override_status", "AUTOMATED")
model_ver  = risk_exp.get("model_version", "2.0.0")

# Status badges
sel_color = "#22c55e" if is_selected else "#ef4444"
sel_label = " SELECTED" if is_selected else " NOT SELECTED"
if override_st == "MANUAL_OVERRIDE":
  sel_label += " (HUMAN OVERRIDE)"

cat_icons = {"VERY HIGH": "", "EXTREME": "", "HIGH": "", "MODERATE": "", "LOW": ""}
cat_icon = cat_icons.get(risk_cat, "")

# Header strip
st.markdown(f"""
<div class="factor-card">
 <div style="display:flex; gap:24px; align-items:center; flex-wrap:wrap;">
  <span style="font-size:1.4rem; font-weight:700;">{row.get('neighbourhood_name', row.get('neighbourhood_id',''))}</span>
  <span style="color:{sel_color}; font-weight:700; font-size:1.0rem;">{sel_label}</span>
  <span>{cat_icon} Risk: <b>{risk_cat}</b> (score: <b>{risk_score:.4f}</b>)</span>
  <span>Model: <b>v{model_ver}</b></span>
  <span>Strategy: <b>{strategy}</b></span>
 </div>
 <div class="impact-row" style="margin-top:12px;">
  <span class="impact-chip">Confidence: <b>{conf_level}</b> ({conf_score:.2f})</span>
  <span class="impact-chip">Fallback: <b>{fallback}</b></span>
  <span class="impact-chip">Override: <b>{override_st}</b></span>
  <span class="impact-chip">Priority: <b>{rec_exp.get('priority','—')}</b></span>
 </div>
</div>
""", unsafe_allow_html=True)

# Population, travel, fairness impact row
pop_total = int(row.get("population", row.get("mobile_population", 0)) or 0)
pop_mobile = int(row.get("mobile_population", 0) or 0)
pop_lsa  = int(row.get("group_low_service_access", False))
travel_km = float(row.get("healthcare_distance_km", 0) or 0)
travel_h  = round(travel_km / 30.0, 2)
mobile_grp = bool(row.get("group_mobile", False))
lsa_grp  = bool(row.get("group_low_service_access", False))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Population Impact",  f"{pop_total:,}", help="Total population in this neighbourhood")
c2.metric("Mobile Pop. Impact",  f"{pop_mobile:,}", help="Mobile worker population")
c3.metric("Travel Distance",   f"{travel_km:.1f} km")
c4.metric("Est. Travel Time",   f"{travel_h:.2f} h")

fair_flags = []
if mobile_grp: fair_flags.append("Mobile Population Group")
if lsa_grp:  fair_flags.append("Low-Service-Access Group")
if fair_flags:
  st.info(f"**Fairness Impact:** This neighbourhood belongs to protected groups: {', '.join(fair_flags)}")
else:
  st.caption("Fairness Impact: No protected group flags for this neighbourhood.")

# Constraint status
st.markdown("**Constraint Status**")
is_valid_geo = row.get("is_valid_geo", True)
geo_status  = " Valid" if is_valid_geo else f" {row.get('geo_validation_status','INVALID')}"
is_feasible = row.get("is_feasible", True)
feas_status = " Feasible" if is_feasible else " Constraint Violated"
c_cs1, c_cs2, c_cs3 = st.columns(3)
c_cs1.markdown(f"Geographic: **{geo_status}**")
c_cs2.markdown(f"Operational: **{feas_status}**")
c_cs3.markdown(f"Capacity OK: **{' Yes' if is_selected else '—'}**")

# Recommended action
st.markdown("**Recommended Action**")
if is_selected:
  action = rec_exp.get("narrative", "Deploy outreach team to this neighbourhood.")
  st.success(action)
else:
  action = rec_exp.get("narrative", "No outreach required at this time.")
  st.info(action)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION B: FACTOR BREAKDOWN TABLE
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("B · Factor Breakdown (Formal Mathematical Model)")
st.caption(
  "Risk Score = α×Temperature + β×Environment + γ×Vulnerability + δ×Service Access + ε×Mobility "
  f"(model v{model_ver})"
)

if risk_exp.get("factor_table"):
  factor_df = pd.DataFrame(risk_exp["factor_table"])
  # Ensure all required columns exist
  for col in ["Factor", "Raw Value", "Normalized (0–1)", "Weight", "Contribution"]:
    if col not in factor_df.columns:
      factor_df[col] = 0.0

  total_contrib = factor_df["Contribution"].sum()
  factor_df["Contribution %"] = (factor_df["Contribution"] / total_contrib * 100).round(1) if total_contrib > 0 else 0.0

  st.dataframe(
    factor_df.style
      .format({
        "Raw Value":    "{:.4f}",
        "Normalized (0–1)":"{:.4f}",
        "Weight":     "{:.3f}",
        "Contribution":  "{:.4f}",
        "Contribution %": "{:.1f}%",
      })
      .background_gradient(subset=["Contribution"], cmap="YlOrRd"),
    use_container_width=True,
    hide_index=True,
  )

  # Contribution bar chart
  fig_bar = px.bar(
    factor_df, x="Factor", y="Contribution",
    color="Contribution", color_continuous_scale="YlOrRd",
    title="Factor Contributions to Risk Score",
    template="plotly_dark", text="Contribution %",
  )
  fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
  fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
             coloraxis_showscale=False)
  st.plotly_chart(fig_bar, use_container_width=True)
else:
  # Legacy fallback
  st.info("Detailed factor breakdown requires a pipeline run with the formal risk model.")
  for factor, contrib in risk_exp.get("factor_contributions", {}).items():
    st.write(f"- **{factor.replace('_',' ').title()}:** contribution = `{contrib:.4f}`")

if risk_exp.get("data_gaps"):
  with st.expander(" Data Gaps Affecting This Explanation"):
    for gap in risk_exp["data_gaps"]:
      st.write(f"- {gap}")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION C: SELECTION REASONING
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("C · Selection Reasoning")
c_sel1, c_sel2 = st.columns(2)
with c_sel1:
  if is_selected:
    st.markdown("**Reasons for Selection**")
    for r in rec_exp.get("selection_reasons", ["—"]):
      st.write(f"• {r}")
  else:
    st.markdown("**Reasons Not Selected**")
    for r in rec_exp.get("not_selected_reasons", ["—"]):
      st.write(f"• {r}")
with c_sel2:
  st.markdown("**Constraints Applied**")
  for c in rec_exp.get("constraints", ["—"]):
    st.write(f"• {c}")

st.write(f"**Fairness Context:** {rec_exp.get('fairness_context', '—')}")
st.write(f"**Trust:** {rec_exp.get('trust_explanation', '—')}")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION D: SENSITIVITY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("D · Sensitivity Analysis")
st.caption(
  "Measures how the plan changes when each weight is shifted by ±10%. "
  "Shows metric-level impact — not just category counts."
)
st.markdown("""
**Parameters varied:**
- Temperature / Vulnerability / Service-Access / Environmental / Mobility weights (±10%, re-normalised)
- Travel Penalty (synthetic preference for nearby areas)
- Fairness Weight (synthetic boost for protected groups)
""")

if st.button(" Run Sensitivity Analysis", key="run_sens", type="primary"):
  with st.spinner("Running sensitivity analysis across 7 parameters…"):
    from src.explainability.sensitivity_engine import run_sensitivity_analysis
    sens_rows = run_sensitivity_analysis(df)

  if not sens_rows:
    st.warning("Sensitivity analysis returned no results. Ensure the pipeline has been run.")
  else:
    st.session_state["sensitivity_results"] = sens_rows
    st.success(f" Sensitivity analysis complete — {len(sens_rows)} parameter variations evaluated.")

if "sensitivity_results" in st.session_state:
  sens_df = pd.DataFrame(st.session_state["sensitivity_results"])

  # Summary table
  display_cols = [
    "Parameter", "Original", "Changed", "Δ Weight",
    "Coverage Orig (%)", "Coverage New (%)", "Coverage Δ (pp)",
    "Fairness Gap Orig (%)", "Fairness Gap New (%)", "Fairness Gap Δ (pp)",
    "Category Changes", "Metric Impact"
  ]
  display_cols = [c for c in display_cols if c in sens_df.columns]

  def _color_delta(val):
    try:
      v = float(str(val).replace("+",""))
      if v > 0: return "color: #22c55e"
      if v < 0: return "color: #ef4444"
    except:
      pass
    return ""

  styled = sens_df[display_cols].style.applymap(
    _color_delta, subset=[c for c in ["Coverage Δ (pp)", "Fairness Gap Δ (pp)"] if c in sens_df.columns]
  )
  st.dataframe(styled, use_container_width=True, hide_index=True)

  # Coverage impact chart
  if "Coverage Δ (pp)" in sens_df.columns:
    fig_s = px.bar(
      sens_df, x="Parameter", y="Coverage Δ (pp)",
      color="Coverage Δ (pp)",
      color_continuous_scale="RdYlGn",
      title="Coverage Change (pp) per Parameter Variation",
      template="plotly_dark",
    )
    fig_s.update_layout(
      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
      xaxis_tickangle=-30,
    )
    st.plotly_chart(fig_s, use_container_width=True)

  # Fairness gap impact chart
  if "Fairness Gap Δ (pp)" in sens_df.columns:
    fig_f = px.bar(
      sens_df, x="Parameter", y="Fairness Gap Δ (pp)",
      color="Fairness Gap Δ (pp)",
      color_continuous_scale="RdYlGn_r",
      title="Fairness Gap Change (pp) per Parameter Variation",
      template="plotly_dark",
    )
    fig_f.update_layout(
      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
      xaxis_tickangle=-30,
    )
    st.plotly_chart(fig_f, use_container_width=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION E: FULL DECISION TRACE
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("E · Full Decision Trace (Advanced)"):
  try:
    audit_log = AuditLogger().read_logs()
  except Exception:
    audit_log = []

  trace = create_decision_trace(
    row, dataset_id=dataset_id, strategy=strategy,
    fairness_warnings=fairness_warnings, audit_logs=audit_log,
  )
  st.json(trace)

# ── Link to methodology page ─────────────────────────────────────────────────
st.markdown("---")
st.page_link(
  "pages/methodology.py",
  label=" View Methodology — Risk Model, Optimization, Constraints, Fairness, Confidence, Limitations",
  icon=":material/article:"
)
