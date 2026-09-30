"""
app/pages/experiment_evaluation.py — Experimentation & Quantitative Validation

4-way comparison: BASELINE + COVERAGE_FOCUSED + BALANCED + FAIRNESS_AWARE.
Runs on the full 50,000-row Chennai dataset.
Persists results with experiment IDs, configuration snapshots, and model versions.
Includes proxy validation (no fabricated precision/recall when no ground truth).
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from src.services.app_state import AppState
from src.evaluation.experiment_runner import ExperimentRunner
from src.evaluation.experiment_store import ExperimentStore
from src.optimisation.run_store import OptimizationRunStore


apply_global_styles()
render_sidebar()

page_header(" Experiment & Evaluation", "Quantitative validation across 4 strategies on the 50 000-row dataset.", icon=":material/biotech:")
AppState.initialize_application()

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
 .exp-banner {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  border: 1px solid #334155; border-left: 4px solid #6366f1;
  border-radius: 8px; padding: 14px 20px; margin-bottom: 16px;
 }
 .val-box {
  background: #0f172a; border: 1px solid #1e3a5f;
  border-radius: 6px; padding: 14px; margin-top: 8px;
  font-family: monospace; font-size: 0.82rem;
 }
 .section-label { color:#94a3b8; font-size:0.78rem; font-weight:600;
  letter-spacing:.08em; text-transform:uppercase; margin-bottom:4px; }
 .repro-box {
  background:#1e293b; border:1px solid #334155; border-radius:6px;
  padding:12px 16px; font-family:monospace; font-size:0.8rem;
 }
</style>
""", unsafe_allow_html=True)

st.markdown(
  "Compares **BASELINE** (temperature-only) against three optimization strategies "
  "on the **same full dataset**. No strategy is ranked as 'best' — each reflects "
  "different operational priorities."
)

# ── Run controls ──────────────────────────────────────────────────────────────
with st.expander(" Experiment Settings", expanded=False):
  num_records = st.number_input(
    "Records (0 = full 50 000-row dataset)",
    min_value=0, max_value=50000, value=0, step=100,
    help="Set to 0 to use the full dataset. Use a small value for quick tests."
  )
  missing_rate = st.slider("Missing Data Rate", 0.0, 0.3, 0.05, 0.01)

col_btn, col_info = st.columns([2, 5])
with col_btn:
  run_clicked = st.button(" Run 4-Strategy Experiment", type="primary", use_container_width=True)
with col_info:
  st.caption("Runs BASELINE → COVERAGE_FOCUSED → BALANCED → FAIRNESS_AWARE. "
        "Results are automatically persisted with a unique Experiment ID.")

if run_clicked:
  with st.spinner("Running 4-strategy experiment on the 50 000-row dataset…"):
    runner = ExperimentRunner(num_records=num_records, missing_rate=missing_rate)
    results = runner.run_comparison()

  if results["status"] == "FAILED":
    st.error("Experiment failed.")
    for e in results.get("errors", []):
      st.caption(e)
    st.stop()

  st.session_state["experiment_results"] = results
  st.success(
    f" Experiment **{results['experiment_id'][:8]}…** completed — "
    f"{results.get('dataset_rows', '?'):,} rows, {results.get('total_runtime_s', 0):.1f}s"
  )

if "experiment_results" not in st.session_state:
  st.info("Click ** Run 4-Strategy Experiment** above to execute the experiment.")
  st.stop()

exp = st.session_state["experiment_results"]

# ── Strategy data extraction ──────────────────────────────────────────────────
STRATEGY_KEYS = {
  "Baseline":     "baseline",
  "Coverage-Focused": "coverage_focused",
  "Balanced":     "balanced",
  "Fairness-Aware":  "fairness_aware",
}
COLORS = {
  "Baseline":     "#64748b",
  "Coverage-Focused": "#6366f1",
  "Balanced":     "#22c55e",
  "Fairness-Aware":  "#f59e0b",
}

strategies = {
  label: exp.get(key, {}).get("metrics", {})
  for label, key in STRATEGY_KEYS.items()
}
validations = {
  label: exp.get(key, {}).get("validation", {})
  for label, key in STRATEGY_KEYS.items()
}

st.markdown("---")

# ── Section 1: Experiment Identity ────────────────────────────────────────────
st.subheader("1 · Experiment Identity & Reproducibility")
exp_id   = exp.get("experiment_id", "—")
ds_sig   = exp.get("dataset_signature", "—")
ds_rows  = exp.get("dataset_rows", 0)
ds_name  = exp.get("dataset_name", "—")
cfg    = exp.get("configuration", {})
runtime  = exp.get("total_runtime_s", 0.0)

st.markdown(f"""<div class="repro-box">
<b>Experiment ID:</b> {exp_id}<br>
<b>Dataset:</b> {ds_name} ({ds_rows:,} rows)<br>
<b>Dataset Signature:</b> {ds_sig}<br>
<b>Model Version:</b> {cfg.get('model_version', '2.0.0')} &nbsp; 
<b>Optimizer Version:</b> {cfg.get('optimizer_version', '3.1.0')}<br>
<b>Total Runtime:</b> {runtime:.2f}s &nbsp; <b>Random Seed:</b> {cfg.get('random_seed', 42)}<br>
<b>Teams:</b> {cfg.get('number_of_teams', '?')} × {cfg.get('maximum_visits_per_team', '?')} visits &nbsp;
<b>Max Coverage Gap:</b> {cfg.get('maximum_coverage_gap', 0.1):.0%}
</div>""", unsafe_allow_html=True)

with st.expander(" Full Configuration Snapshot"):
  st.json(cfg)

st.markdown("---")

# ── Section 2: KPI Summary Cards ──────────────────────────────────────────────
st.subheader("2 · KPI Summary")
cols = st.columns(len(strategies))
for col, (label, m) in zip(cols, strategies.items()):
  col.markdown(f"<div class='section-label'>{label}</div>", unsafe_allow_html=True)
  col.metric("Risk Coverage",  f"{m.get('high_risk_coverage_pct', 0):.1f}%")
  col.metric("Capacity Used",  f"{m.get('capacity_utilization_pct', 0):.1f}%")
  col.metric("Fairness Gap",  f"{m.get('fairness_gap_pct', 0):.1f}%")
  col.metric("Events",     f"{m.get('num_outreach_events', 0):,}")
  col.metric("Pop. Reached",  f"{m.get('total_population_reached', 0):,}")

st.markdown("---")

# ── Section 3: Full Metrics Comparison Table ───────────────────────────────────
st.subheader("3 · Full Metrics Comparison")

METRIC_LABELS = {
  "high_risk_coverage_pct":   "High-Risk Coverage (%)",
  "total_population_reached":  "Total Population Reached",
  "mobile_population_reached":  "Mobile Pop. Reached",
  "low_service_access_reached": "Low-Service-Access Pop. Reached",
  "travel_distance_total_km":  "Total Travel Distance (km)",
  "estimated_travel_time_h":   "Est. Travel Time (h)",
  "num_outreach_events":     "Outreach Events",
  "capacity_utilization_pct":  "Capacity Utilization (%)",
  "fairness_gap_pct":      "Fairness Gap (%)",
  "fallback_count":       "Fallback Count",
  "avg_selected_risk_score":   "Avg. Risk Score (Selected)",
  "runtime_s":          "Runtime (s)",
}

rows = []
for key, label in METRIC_LABELS.items():
  row = {"Metric": label}
  for strat_label, m in strategies.items():
    v = m.get(key, "—")
    if isinstance(v, float):
      row[strat_label] = f"{v:.2f}"
    elif isinstance(v, int):
      row[strat_label] = f"{v:,}"
    else:
      row[strat_label] = str(v)
  rows.append(row)

comp_df = pd.DataFrame(rows).set_index("Metric")
st.dataframe(comp_df, use_container_width=True)

st.markdown("---")

# ── Section 4: Validation Results ────────────────────────────────────────────
st.subheader("4 · Quantitative Validation")

gt_available = any(v.get("ground_truth_available") for v in validations.values())
if gt_available:
  st.success(" Ground-truth labels detected. Supervised metrics (precision / recall / F1) computed.")
else:
  st.info(
    " No ground-truth labels found in the dataset. "
    "Supervised metrics (precision/recall/F1) are **not calculated** to avoid fabrication. "
    "Proxy validation metrics are shown instead."
  )

val_tabs = st.tabs(list(strategies.keys()))
for tab, (label, _) in zip(val_tabs, strategies.items()):
  with tab:
    v = validations[label]
    if not v or v.get("error"):
      st.warning(v.get("error", "No validation data."))
      continue

    if v.get("ground_truth_available"):
      # Supervised
      col1, col2, col3 = st.columns(3)
      col1.metric("Precision", f"{v.get('precision', 0):.3f}")
      col2.metric("Recall",   f"{v.get('recall', 0):.3f}")
      col3.metric("F1 Score",  f"{v.get('f1_score', 0):.3f}")
      cm = v.get("confusion_matrix", {})
      st.markdown("**Confusion Matrix**")
      st.table(pd.DataFrame({
        "Predicted: Yes": [cm.get("TP", 0), cm.get("FP", 0)],
        "Predicted: No": [cm.get("FN", 0), cm.get("TN", 0)],
      }, index=["Actual: Yes", "Actual: No"]))
    else:
      # Proxy metrics
      trcr = v.get("top_risk_capture_rate")
      rba = v.get("rule_based_agreement")
      tau = v.get("rank_stability_kendall_tau")
      sens = v.get("sensitivity_change_rate")
      thrc = v.get("threshold_consistency")

      c1, c2, c3, c4, c5 = st.columns(5)
      c1.metric("Top-Risk Capture", f"{trcr:.1%}" if trcr is not None else "—",
           help="Fraction of top-N risk neighbourhoods captured")
      c2.metric("Rule Agreement",  f"{rba:.1%}" if rba is not None else "—",
           help="Agreement with high-risk category threshold rule")
      c3.metric("Rank Stability τ", f"{tau:.3f}" if tau is not None else "—",
           help="Kendall-τ correlation between risk score and selection")
      c4.metric("Sensitivity",   f"{sens:.1%}" if sens is not None else "—",
           help="Selection change rate under ±5% risk perturbation")
      c5.metric("Threshold Consist.", f"{thrc:.1%}" if thrc is not None else "—",
           help="Fraction of selected neighbourhoods above the 75th-percentile risk score")

      with st.expander(" Proxy Metric Definitions"):
        st.markdown("""
| Metric | Mathematical Definition |
|--------|------------------------|
| **Top-Risk Capture Rate** | \|Selected ∩ Top-N by Risk Score\| / N |
| **Rule-Based Agreement** | \|Selected ∩ Rule-Positive\| / \|Rule-Positive\| |
| **Rank Stability (Kendall-τ)** | Kendall rank correlation between risk score and selection (τ ∈ [-1, 1]) |
| **Sensitivity** | Fraction of selections that change under ±5% risk perturbation |
| **Threshold Consistency** | \|Selected ∩ Above Q3 Risk\| / \|Selected\| |
""")
      st.markdown(f"""<div class="val-box">
<b>Rule-Positive Count:</b> {v.get('rule_positive_count', '—')}&nbsp; 
<b>Rule-Agreed Count:</b> {v.get('rule_agreed_count', '—')}<br>
<b>Top-Risk N:</b> {v.get('top_risk_capture_n', '—')}&nbsp;
<b>Sensitivity Changed:</b> {v.get('sensitivity_changed_n', '—')}<br>
<b>Threshold Value:</b> {v.get('threshold_value', '—')}&nbsp;
<b>Threshold Consistent N:</b> {v.get('threshold_consistent_n', '—')}<br>
<b>Rank Stability p-value:</b> {v.get('rank_stability_p_value', '—')}
</div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Section 5: Fairness Analysis ──────────────────────────────────────────────
st.subheader("5 · Rigorous Fairness Analysis")
fair_tabs = st.tabs(list(strategies.keys()))
for tab, (label, m) in zip(fair_tabs, strategies.items()):
  with tab:
    report = m.get("fairness_report", [])
    if not report:
      st.info("No fairness data available for this strategy.")
      continue
    rows_f = []
    for r in report:
      gname = r.get("group_name", "").replace("group_", "").replace("_", " ").title()
      rows_f.append({
        "Group":      gname,
        "Target Pop":    f"{r.get('target_population', 0):,}",
        "Reached Pop":   f"{r.get('reached_population', 0):,}",
        "Coverage (%)":   f"{r.get('group_coverage', 0)*100:.1f}%",
        "Overall Cov (%)": f"{r.get('overall_coverage', 0)*100:.1f}%",
        "Coverage Gap":   f"{r.get('coverage_gap', 0)*100:.1f}%",
        "Coverage Ratio":  f"{r.get('coverage_ratio', 0):.2f}×",
        "Opp. Diff":    f"{r.get('opportunity_difference', 0)*100:.1f}%",
        "Pop-Wtd Cov":   f"{r.get('pop_weighted_coverage', 0)*100:.1f}%",
        "Sample Size":   r.get("sample_size", 0),
      })
    st.dataframe(pd.DataFrame(rows_f).set_index("Group"), use_container_width=True)

st.markdown("---")

# ── Section 6: Charts ─────────────────────────────────────────────────────────
st.subheader("6 · Comparative Charts")

tab_bar, tab_radar, tab_val = st.tabs(["Bar Charts", "Radar Profile", "Validation Chart"])

with tab_bar:
  bar_metrics = [
    ("high_risk_coverage_pct",  "High-Risk Coverage (%)"),
    ("capacity_utilization_pct", "Capacity Utilization (%)"),
    ("fairness_gap_pct",     "Fairness Gap (%)"),
    ("total_population_reached", "Population Reached"),
  ]
  for key, title in bar_metrics:
    chart_df = pd.DataFrame([
      {"Strategy": lbl, "Value": m.get(key, 0) or 0}
      for lbl, m in strategies.items()
    ])
    fig = px.bar(
      chart_df, x="Strategy", y="Value", title=title,
      color="Strategy",
      color_discrete_map=COLORS,
      template="plotly_dark",
    )
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
             showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with tab_radar:
  radar_keys = [
    ("high_risk_coverage_pct",  100.0, "Risk Coverage"),
    ("capacity_utilization_pct", 100.0, "Capacity Util."),
    ("mobile_population_reached", None, "Mobile Pop."),
    ("low_service_access_reached",None, "Low-Service Pop."),
  ]
  fig_r = go.Figure()
  for label, m in strategies.items():
    vals = []
    for k, mx, _ in radar_keys:
      raw = float(m.get(k, 0) or 0)
      if mx:
        vals.append(min(raw / mx, 1.0))
      else:
        all_v = [float(strategies[s].get(k, 0) or 0) for s in strategies]
        mv = max(all_v) or 1.0
        vals.append(raw / mv)
    labels_r = [r[2] for r in radar_keys]
    fig_r.add_trace(go.Scatterpolar(
      r=vals + [vals[0]], theta=labels_r + [labels_r[0]],
      fill="toself", name=label,
      line_color=COLORS[label],
    ))
  fig_r.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)", title="Multi-Objective Strategy Profile"
  )
  st.plotly_chart(fig_r, use_container_width=True)

with tab_val:
  if not gt_available:
    val_chart_data = []
    for label in strategies:
      v = validations[label]
      val_chart_data.append({
        "Strategy": label,
        "Top-Risk Capture": float(v.get("top_risk_capture_rate", 0) or 0),
        "Rule Agreement":  float(v.get("rule_based_agreement", 0) or 0),
        "Threshold Consistency": float(v.get("threshold_consistency", 0) or 0),
      })
    val_df = pd.DataFrame(val_chart_data).melt(
      id_vars="Strategy", var_name="Metric", value_name="Value"
    )
    fig_v = px.bar(
      val_df, x="Metric", y="Value", color="Strategy",
      barmode="group", title="Proxy Validation Metrics by Strategy",
      color_discrete_map=COLORS, template="plotly_dark",
    )
    fig_v.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_v, use_container_width=True)
  else:
    st.info("Supervised metrics are scalar — see the Validation tab above for details.")

st.markdown("---")

# ── Section 7: Experiment History ────────────────────────────────────────────
st.subheader("7 · Experiment History")
with st.expander(" All Persisted Experiments"):
  try:
    store = ExperimentStore()
    all_exps = store.load_all()
    if all_exps:
      hist_rows = []
      for e in all_exps[:30]:
        strats = e.get("strategies", {})
        hist_rows.append({
          "ID (short)":  e["experiment_id"][:8] + "…",
          "Timestamp":   e.get("timestamp", "—")[:19],
          "Dataset":    e.get("dataset_name", "—"),
          "Rows":     f"{e.get('dataset_rows', 0):,}",
          "Runtime (s)":  e.get("runtime_s", 0),
          "Strategies Run": len(strats),
          "Full ID":    e["experiment_id"],
        })
      hist_df = pd.DataFrame(hist_rows)
      st.dataframe(hist_df.drop(columns=["Full ID"]), use_container_width=True, hide_index=True)
    else:
      st.info("No experiments persisted yet.")
  except Exception as exc:
    st.caption(f"Could not load experiment history: {exc}")

with st.expander(" Optimization Run History (from OutreachPlanner)"):
  try:
    store2 = OptimizationRunStore()
    runs  = store2.load_all()
    if runs:
      run_rows = [
        {
          "Run ID":     r["run_id"][:8] + "…",
          "Timestamp":   r["timestamp"][:19],
          "Strategy":    r["strategy"],
          "Risk Coverage": r["metrics"].get("risk_coverage_pct", "—"),
          "Runtime (s)":  r["runtime_s"],
          "Dataset Sig":  (r.get("dataset_signature") or "—")[:10],
        }
        for r in runs[:20]
      ]
      st.dataframe(pd.DataFrame(run_rows), use_container_width=True, hide_index=True)
    else:
      st.info("No optimization runs found.")
  except Exception as exc:
    st.caption(f"Could not load run history: {exc}")
