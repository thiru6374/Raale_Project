"""
app/pages/final_decision_center.py

Final Decision Intelligence — Executive Decision Support Dashboard.
All values come from the canonical AppState and pipeline.
"""
import json
import uuid
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.layout import apply_global_styles, page_header, status_badge
from app.components.sidebar import render_sidebar
from src.config.settings import settings
from src.services.app_state import AppState
from src.services.decision_intelligence_service import DecisionIntelligenceService


apply_global_styles()
render_sidebar()

# ── Page-specific CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
.exec-kpi {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px 20px 14px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  transition: box-shadow 0.2s;
}
.exec-kpi:hover { box-shadow: 0 4px 10px rgba(0,0,0,0.09); }
.exec-kpi-label {
  font-size: 0.78rem; font-weight: 600; color: #64748b;
  text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px;
}
.exec-kpi-value {
  font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1.1;
}
.exec-kpi-sub { font-size: 0.78rem; color: #64748b; margin-top: 4px; }
.exec-section {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 22px 26px;
  margin-bottom: 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.exec-section h4 {
  font-size: 1rem; font-weight: 600; color: #0f172a;
  margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px;
}
.priority-card {
  border-left: 5px solid;
  border-radius: 0 8px 8px 0;
  padding: 14px 18px;
  margin-bottom: 12px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  border-right: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}
.pri-CRITICAL { border-left-color: #ef4444; }
.pri-HIGH   { border-left-color: #f59e0b; }
.pri-MEDIUM  { border-left-color: #3b82f6; }
.pri-LOW   { border-left-color: #10b981; }
.pri-MANUAL  { border-left-color: #8b5cf6; }
.tag {
  font-size: 0.72rem; padding: 2px 8px; border-radius: 12px;
  background: #f1f5f9; border: 1px solid #e2e8f0;
  color: #475569; margin-right: 5px; display: inline-block; margin-bottom: 4px;
}
.comparison-table {
  width: 100%; border-collapse: collapse; font-size: 0.85rem;
}
.comparison-table th {
  background: #f1f5f9; color: #475569; font-weight: 600;
  padding: 10px 14px; text-align: left; border-bottom: 2px solid #e2e8f0;
}
.comparison-table td {
  padding: 10px 14px; border-bottom: 1px solid #f1f5f9; color: #334155;
}
.comparison-table tr:hover td { background: #f8fafc; }
.better { color: #10b981; font-weight: 600; }
.worse { color: #ef4444; font-weight: 600; }
.neutral { color: #64748b; }
.nav-pills {
  display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;
}
.nav-pill {
  padding: 6px 14px; border-radius: 20px; border: 1px solid #e2e8f0;
  background: #f8fafc; color: #475569; font-size: 0.8rem; font-weight: 500;
  text-decoration: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px;
}
.nav-pill:hover { background: #eff6ff; border-color: #3b82f6; color: #3b82f6; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
col_h, col_btn = st.columns([4, 1])
with col_h:
  st.markdown(
    "<h1 style='margin-bottom:2px;'>"
    "<span class='material-symbols-rounded' style='font-size:2rem;vertical-align:middle;margin-right:10px;color:#3b82f6;'>verified</span>"
    "Final Decision Intelligence</h1>",
    unsafe_allow_html=True
  )
  st.markdown(
    "<p style='color:#64748b;font-size:1rem;margin:0 0 18px 0;'>"
    "AI-Assisted Decision Support for Targeted, Timely, and Fair Neighbourhood Outreach</p>",
    unsafe_allow_html=True
  )
with col_btn:
  st.write("")
  st.write("")
  if st.button("Refresh Analysis", use_container_width=True, type="primary"):
    AppState.initialize_application(force_refresh=True)
    st.rerun()

st.markdown("<hr style='margin:0 0 20px 0;border:0;border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

# ── Navigation ────────────────────────────────────────────────────────────────
nav_links = [
  ("map", "Risk Map", "risk_map"),
  ("assignment", "Outreach Plan", "outreach_planner"),
  ("balance", "Fairness", "fairness_analysis"),
  ("search_insights", "Explainability", "decision_explainability"),
  ("history", "Audit Log", "override_audit"),
  ("article", "Evidence Report", "evidence_report"),
  ("settings_applications", "Operations", "operations_control_center"),
]
pills_html = "<div class='nav-pills'>"
for icon, label, page in nav_links:
  pills_html += (
    f"<a class='nav-pill' href='/{page.replace('_', ' ').title().replace(' ', '_')}'>"
    f"<span class='material-symbols-rounded' style='font-size:0.9rem;'>{icon}</span>{label}</a>"
  )
pills_html += "</div>"
st.markdown(pills_html, unsafe_allow_html=True)

# ── Initialize ────────────────────────────────────────────────────────────────
AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()

df = AppState.get_pipeline_results()
if df is None or df.empty:
  st.markdown("""
  <div style='background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;
     padding:40px;text-align:center;'>
   <span class='material-symbols-rounded' style='font-size:3rem;color:#3b82f6;'>info</span>
   <h3 style='color:#1e40af;margin:10px 0 5px 0;'>No Analysis Results Available</h3>
   <p style='color:#3b82f6;margin:0;'>Run the pipeline to generate decision recommendations.</p>
  </div>""", unsafe_allow_html=True)
  st.stop()

# ── Normalise schema ──────────────────────────────────────────────────────────
df = df.copy()
if "risk_level" not in df.columns:
  if "multi_factor_risk_category" in df.columns:
    _rmap = {"EXTREME": "VERY HIGH", "VERY HIGH": "VERY HIGH",
         "HIGH": "HIGH", "MODERATE": "MODERATE", "MEDIUM": "MODERATE", "LOW": "LOW"}
    df["risk_level"] = df["multi_factor_risk_category"].map(_rmap).fillna("LOW")
  else:
    df["risk_level"] = "LOW"

if "risk_score" not in df.columns:
  for _c in ("multi_factor_risk_score", "composite_risk_score"):
    if _c in df.columns:
      df["risk_score"] = df[_c]
      break

# ── Core Calculations ─────────────────────────────────────────────────────────
total_cap = settings.number_of_teams * settings.maximum_visits_per_team
is_sel = df.get("selected_for_outreach", pd.Series(False, index=df.index)).astype(bool)
is_hr = df["risk_level"].isin(["HIGH", "VERY HIGH"])

n_sel = int(is_sel.sum())
n_hr = int(is_hr.sum())
hr_reached = int((is_hr & is_sel).sum())
risk_cov = hr_reached / n_hr if n_hr > 0 else 0.0

conf_mean = float(df["confidence_score"].mean()) if "confidence_score" in df.columns else 1.0
cap_util = n_sel / total_cap if total_cap > 0 else 0.0

# Mobile population
if "mobile_population" in df.columns:
  mob_total = int(df["mobile_population"].sum())
  mob_reached = int(df.loc[is_sel, "mobile_population"].sum()) if is_sel.any() else 0
elif "group_mobile" in df.columns:
  gm = df["group_mobile"].astype(bool)
  pop_c = "total_population" if "total_population" in df.columns else "population"
  mob_total = int(df.loc[gm, pop_c].sum()) if pop_c in df.columns else int(gm.sum())
  mob_reached = int(df.loc[gm & is_sel, pop_c].sum()) if pop_c in df.columns else int((gm & is_sel).sum())
else:
  mob_total = mob_reached = 0

mob_pct = mob_reached / mob_total if mob_total > 0 else 0.0

# Low service access
if "group_low_service_access" in df.columns:
  glsa = df["group_low_service_access"].astype(bool)
  pop_c = "total_population" if "total_population" in df.columns else "population"
  lsa_total = int(df.loc[glsa, pop_c].sum()) if pop_c in df.columns else int(glsa.sum())
  lsa_reached = int(df.loc[glsa & is_sel, pop_c].sum()) if pop_c in df.columns else int((glsa & is_sel).sum())
else:
  lsa_total = lsa_reached = 0

lsa_pct = lsa_reached / lsa_total if lsa_total > 0 else 0.0

# Fairness gap
rates = []
for grp in ["group_mobile", "group_low_service_access"]:
  if grp in df.columns:
    gm = df[grp].astype(bool)
    if gm.sum() > 0:
      rates.append((gm & is_sel).sum() / gm.sum())
fgap = abs(rates[0] - rates[1]) if len(rates) == 2 else 0.0

# Travel time
if "healthcare_distance_km" in df.columns and is_sel.any():
  avg_travel_min = float(df.loc[is_sel, "healthcare_distance_km"].mean() / 30.0 * 60)
else:
  avg_travel_min = None

strategy = st.session_state.get("optimization_strategy", "COVERAGE_FOCUSED")
sys_health = AppState.get_system_health()

# ── 1. Executive KPI Section ─────────────────────────────────────────────────
st.markdown("#### District Status")

c1, c2, c3, c4 = st.columns(4)

def _kpi(col, icon, label, value, sub, accent="#3b82f6"):
  col.markdown(f"""
  <div class='exec-kpi'>
   <div class='exec-kpi-label'>
    <span class='material-symbols-rounded' style='font-size:1rem;color:{accent};vertical-align:middle;'>{icon}</span>
    &nbsp;{label}
   </div>
   <div class='exec-kpi-value' style='color:{accent};'>{value}</div>
   <div class='exec-kpi-sub'>{sub}</div>
  </div>""", unsafe_allow_html=True)

conf_level = "High Confidence" if conf_mean >= 0.85 else ("Moderate" if conf_mean >= 0.6 else "Low Confidence")
conf_color = "#10b981" if conf_mean >= 0.85 else ("#f59e0b" if conf_mean >= 0.6 else "#ef4444")

_kpi(c1, "verified", "System Confidence", f"{conf_mean:.1%}", conf_level, conf_color)
_kpi(c2, "radar",  "Risk Coverage Rate", f"{risk_cov:.1%}", f"{hr_reached} / {n_hr} high-risk reached", "#3b82f6")
_kpi(c3, "corporate_fare", "Capacity Utilization", f"{cap_util:.1%}",
   f"{n_sel} / {total_cap} events {'(Over Cap)' if cap_util > 1.0 else '(OK)'}", "#f59e0b" if cap_util > 1.0 else "#3b82f6")
_kpi(c4, "balance", "Fairness Gap", f"{fgap:.1%}",
   "Acceptable" if fgap < 0.1 else "Review Required", "#10b981" if fgap < 0.1 else "#f59e0b")

st.markdown("<br>", unsafe_allow_html=True)
c5, c6, c7, c8 = st.columns(4)
_kpi(c5, "smartphone", "Mobile Pop Reached", f"{mob_reached:,}", f"{mob_pct:.1%} of mobile population", "#8b5cf6")
_kpi(c6, "local_hospital", "Low-Service Reached", f"{lsa_reached:,}", f"{lsa_pct:.1%} of LSA population", "#8b5cf6")
_kpi(c7, "calendar_today", "Planned Events", f"{n_sel}", f"Capacity: {total_cap}", "#0f172a")
_kpi(c8, "directions_car", "Avg Travel Time",
   f"{avg_travel_min:.1f} min" if avg_travel_min is not None else "N/A",
   f"Target ≤ {settings.maximum_travel_time} min", "#0f172a")

st.markdown("<br>", unsafe_allow_html=True)

# Constraint status bar
feasible = df.get("is_feasible", pd.Series(True, index=df.index)).all() if "is_feasible" in df.columns else (n_sel <= total_cap)
if feasible:
  st.markdown(
    "<div style='background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:10px 16px;"
    "color:#15803d;font-size:0.85rem;font-weight:600;'>"
    "<span class='material-symbols-rounded' style='vertical-align:middle;margin-right:6px;font-size:1rem;'>check_circle</span>"
    "All constraints satisfied — plan is operationally feasible.</div>",
    unsafe_allow_html=True
  )
else:
  st.markdown(
    "<div style='background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:10px 16px;"
    "color:#991b1b;font-size:0.85rem;font-weight:600;'>"
    "<span class='material-symbols-rounded' style='vertical-align:middle;margin-right:6px;font-size:1rem;'>error</span>"
    "Constraint violations detected — review the plan before finalising.</div>",
    unsafe_allow_html=True
  )

st.markdown("<br>", unsafe_allow_html=True)

# ── 2. Top Priority Actions + Comparison ─────────────────────────────────────
left_col, right_col = st.columns([3, 2])

with left_col:
  st.markdown("<div class='exec-section'>", unsafe_allow_html=True)
  st.markdown(
    "<h4><span class='material-symbols-rounded'>priority_high</span>"
    "Top Priority Actions</h4>", unsafe_allow_html=True
  )
  st.markdown(
    "<p style='font-size:0.82rem;color:#64748b;margin:-8px 0 16px 0;'>"
    "Transparent explanation of recommendations generated from risk model, confidence, and constraints.</p>",
    unsafe_allow_html=True
  )

  try:
    decisions = DecisionIntelligenceService.generate_final_decisions(
      neighbourhoods=df.to_dict(orient="records"),
      system_health_status=sys_health.get("overall_status", "HEALTHY") if sys_health else "HEALTHY",
      alerts=[],
      pipeline_run_id=AppState.get_pipeline_run_id() or str(uuid.uuid4()),
      config_version="v2.1"
    )
    pri_map = {"CRITICAL": 0, "HIGH": 1, "MANUAL_REVIEW_REQUIRED": 2, "MEDIUM": 3, "LOW": 4}
    decisions_sorted = sorted(decisions, key=lambda x: pri_map.get(x.get("priority", "LOW"), 5))

    if not decisions_sorted:
      st.info("No priority decisions generated. Ensure the pipeline has run successfully.")
    else:
      for dec in decisions_sorted[:8]:
        pri = dec.get("priority", "LOW")
        pri_cls = "pri-MANUAL" if "MANUAL" in pri else f"pri-{pri}"
        nid = dec.get("neighbourhood_id", "N/A")
        risk_lv = dec.get("risk_level", "UNKNOWN")
        action = dec.get("recommended_action", "—")
        reason = dec.get("reasoning_summary", "—")
        impact = dec.get("expected_impact", "—")
        conf_d = dec.get("confidence", None)

        # Get live row data
        nrow = df[df["neighbourhood_id"] == nid] if "neighbourhood_id" in df.columns else pd.DataFrame()
        if not nrow.empty:
          r = nrow.iloc[0]
          risk_score_d = r.get("risk_score", r.get("multi_factor_risk_score", "N/A"))
          risk_score_str = f"{risk_score_d:.3f}" if isinstance(risk_score_d, (int, float)) else str(risk_score_d)
          conf_d = r.get("confidence_score", conf_d or 1.0)
          sched_date = r.get("outreach_date", "Not scheduled")
          team = r.get("assigned_team", "Unassigned")
        else:
          risk_score_str = "N/A"
          sched_date = "Not scheduled"
          team = "Unassigned"

        conf_str = f"{conf_d:.1%}" if isinstance(conf_d, (int, float)) else "N/A"
        risk_lv_clean = str(risk_lv).replace("VERY ", "Very ").replace("HIGH", "High").replace("MODERATE", "Moderate").replace("LOW", "Low")

        st.markdown(f"""
        <div class='priority-card {pri_cls}'>
         <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>
          <div>
           <span style='font-weight:700;color:#0f172a;font-size:0.95rem;'>{nid}</span>
           &nbsp;—&nbsp;
           <span style='font-weight:600;color:#64748b;'>{risk_lv_clean}</span>
          </div>
          <span style='font-size:0.75rem;font-weight:700;color:#475569;background:#f1f5f9;
             padding:3px 10px;border-radius:10px;border:1px solid #e2e8f0;'>{pri}</span>
         </div>
         <div style='margin-bottom:10px;'>
          <span class='tag'>Risk Score: {risk_score_str}</span>
          <span class='tag'>Confidence: {conf_str}</span>
          <span class='tag'>Team: {team}</span>
          <span class='tag'>Date: {sched_date}</span>
         </div>
         <p style='margin:5px 0;font-size:0.83rem;'>
          <strong style='color:#0f172a;'>Recommended Action:</strong>
          <span style='color:#334155;'> {action}</span>
         </p>
         <p style='margin:4px 0;font-size:0.8rem;color:#64748b;'>
          <strong>Reason:</strong> {reason}
         </p>
         <p style='margin:4px 0;font-size:0.8rem;color:#64748b;'>
          <strong>Expected Impact:</strong> {impact}
         </p>
        </div>""", unsafe_allow_html=True)
  except Exception as e:
    st.warning(f"Could not generate priority decisions: {e}")

  st.markdown(
    "<div style='text-align:right;margin-top:8px;'>"
    "<a href='pages/decision_explainability' style='font-size:0.82rem;color:#3b82f6;'>"
    "Full Explanation &amp; Methodology →</a></div>",
    unsafe_allow_html=True
  )
  st.markdown("</div>", unsafe_allow_html=True)

with right_col:
  # ── Baseline vs Proposed ──────────────────────────────────────────────────
  st.markdown("<div class='exec-section'>", unsafe_allow_html=True)
  st.markdown(
    "<h4><span class='material-symbols-rounded'>stacked_bar_chart</span>"
    "Baseline vs Proposed Coverage</h4>", unsafe_allow_html=True
  )

  bl = AppState.get_baseline_results()
  if bl and hasattr(bl, "records") and bl.records:
    bl_selected_ids = {r.neighbourhood_id for r in bl.records if getattr(r, "baseline_selected", False)}
    bl_n = len(bl_selected_ids)
    hr_ids = set(df.loc[is_hr, "neighbourhood_id"]) if "neighbourhood_id" in df.columns else set()
    bl_hr_match = len(bl_selected_ids & hr_ids)
    bl_cov = bl_hr_match / n_hr if n_hr > 0 else 0.0
    bl_util = bl_n / total_cap if total_cap > 0 else 0.0

    rows = [
      ("High-Risk Coverage", f"{bl_cov:.1%}", f"{risk_cov:.1%}", risk_cov > bl_cov),
      ("Mobile Pop Coverage", "N/A (temp-only)", f"{mob_pct:.1%}", True),
      ("Low-Service Coverage", "N/A (temp-only)", f"{lsa_pct:.1%}", True),
      ("Fairness Gap", "N/A", f"{fgap:.1%}", True),
      ("Cap Utilization", f"{bl_util:.1%}", f"{cap_util:.1%}", None),
      ("Planned Events", f"{bl_n}", f"{n_sel}", None),
    ]

    table_html = "<table class='comparison-table'><thead><tr>"
    table_html += "<th>Metric</th><th>Baseline</th><th>Proposed</th></tr></thead><tbody>"
    for label, bv, pv, better in rows:
      prop_cls = "better" if better is True else ("worse" if better is False else "neutral")
      table_html += f"<tr><td>{label}</td><td class='neutral'>{bv}</td><td class='{prop_cls}'>{pv}</td></tr>"
    table_html += "</tbody></table>"
    table_html += (
      "<p style='margin-top:12px;font-size:0.75rem;color:#94a3b8;'>"
      "No strategy is universally best. COVERAGE_FOCUSED maximises high-risk reach; "
      "FAIRNESS_AWARE prioritises protected groups; BALANCED trades off travel vs coverage.</p>"
    )
    st.markdown(table_html, unsafe_allow_html=True)
  else:
    st.markdown("""
    <div style='background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
       padding:20px;text-align:center;color:#1e40af;font-size:0.85rem;'>
     <span class='material-symbols-rounded' style='font-size:2rem;color:#3b82f6;'>info</span><br>
     <b>Baseline comparison not available yet.</b><br>
     Run the pipeline to generate baseline results.
    </div>""", unsafe_allow_html=True)
  st.markdown("</div>", unsafe_allow_html=True)

  # ── Decision Explanation Summary ──────────────────────────────────────────
  st.markdown("<div class='exec-section'>", unsafe_allow_html=True)
  st.markdown(
    "<h4><span class='material-symbols-rounded'>search_insights</span>"
    "Decision Explanation</h4>", unsafe_allow_html=True
  )
  st.markdown("""
  <div style='font-size:0.82rem;color:#475569;line-height:1.7;'>
   <div style='margin-bottom:8px;'>
    <span class='material-symbols-rounded' style='font-size:0.9rem;vertical-align:middle;color:#3b82f6;'>help</span>
    <strong>Why this neighbourhood?</strong><br>
    <span style='color:#64748b;'>Based on multi-factor risk score exceeding threshold, factoring temperature, vulnerability, environment, service access, and mobility.</span>
   </div>
   <div style='margin-bottom:8px;'>
    <span class='material-symbols-rounded' style='font-size:0.9rem;vertical-align:middle;color:#3b82f6;'>help</span>
    <strong>Why this action?</strong><br>
    <span style='color:#64748b;'>Optimizer selected this neighbourhood as feasible within team capacity and travel constraints.</span>
   </div>
   <div style='margin-bottom:8px;'>
    <span class='material-symbols-rounded' style='font-size:0.9rem;vertical-align:middle;color:#3b82f6;'>help</span>
    <strong>What is the confidence?</strong><br>
    <span style='color:#64748b;'>Confidence reflects data completeness, temperature validity, and model consistency.</span>
   </div>
  </div>""", unsafe_allow_html=True)
  st.markdown(
    "<div style='text-align:right;margin-top:8px;'>"
    "<a href='pages/decision_explainability' style='font-size:0.82rem;color:#3b82f6;'>"
    "Full Explainability Page →</a></div>",
    unsafe_allow_html=True
  )
  st.markdown("</div>", unsafe_allow_html=True)

  # ── Recent Override Summary ───────────────────────────────────────────────
  st.markdown("<div class='exec-section'>", unsafe_allow_html=True)
  st.markdown(
    "<h4><span class='material-symbols-rounded'>history</span>Recent Overrides</h4>",
    unsafe_allow_html=True
  )
  try:
    audit_path = Path("data/logs/audit.jsonl")
    override_records = []
    if audit_path.exists():
      with open(audit_path, "r", encoding="utf-8") as f:
        for line in f:
          try:
            rec = json.loads(line.strip())
            if rec.get("action_type") == "MANUAL_OVERRIDE":
              override_records.append(rec)
          except Exception:
            pass

    if override_records:
      for rec in override_records[-3:][::-1]:
        ts = rec.get("timestamp", "")[:10]
        actor = rec.get("actor", "Unknown")
        nbhd = rec.get("neighbourhood_id", "Unknown")
        reason = rec.get("reason", "—")[:40]
        orig = "Selected" if rec.get("original_decision") else "Not Selected"
        final = "Selected" if rec.get("new_decision") else "Not Selected"
        st.markdown(
          f"<div style='font-size:0.8rem;border-bottom:1px solid #f1f5f9;padding:6px 0;'>"
          f"<b>{nbhd}</b> — {orig}→{final} by {actor} ({ts})<br>"
          f"<span style='color:#64748b;'>{reason}</span></div>",
          unsafe_allow_html=True
        )
    else:
      st.markdown(
        "<div style='color:#64748b;font-size:0.82rem;'>No overrides recorded.</div>",
        unsafe_allow_html=True
      )
  except Exception:
    st.markdown(
      "<div style='color:#64748b;font-size:0.82rem;'>Override log not accessible.</div>",
      unsafe_allow_html=True
    )
  st.markdown(
    "<div style='text-align:right;margin-top:8px;'>"
    "<a href='pages/override_audit' style='font-size:0.82rem;color:#3b82f6;'>View Full Audit Log →</a></div>",
    unsafe_allow_html=True
  )
  st.markdown("</div>", unsafe_allow_html=True)

# ── Dataset Provenance ────────────────────────────────────────────────────────
ds_info = AppState.get_active_dataset_info()
res = AppState.get_full_results()
ts = res.get("pipeline_timestamp", "")
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
  f"<div style='border-top:1px solid #e2e8f0;padding:12px 0;display:flex;justify-content:space-between;"
  f"color:#94a3b8;font-size:0.75rem;'>"
  f"<span>Dataset: <b>{ds_info.get('dataset_name','N/A')}</b> &nbsp;|&nbsp; "
  f"Rows: <b>{ds_info.get('dataset_rows',0):,}</b> &nbsp;|&nbsp; "
  f"Strategy: <b>{strategy}</b></span>"
  f"<span>All values from canonical pipeline &nbsp;|&nbsp; Last run: "
  f"{ts[:19].replace('T',' ') if ts else 'N/A'}</span>"
  f"</div>",
  unsafe_allow_html=True
)
