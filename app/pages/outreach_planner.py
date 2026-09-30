"""
app/pages/outreach_planner.py
Outreach plan results — review, schedule, constraints, and manual override.
All values sourced from the canonical pipeline/AppState.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from src.services.app_state import AppState
from src.governance.audit_logger import AuditLogger
from src.governance.overrides import OverrideManager
from src.config.settings import settings

from app.components.layout import apply_global_styles
from app.components.sidebar import render_sidebar
from app.components.empty_states import show_pipeline_uninitialized
from app.components.constraints import render_constraint_status
from app.components.schedule_view import render_schedule_view

# ── Design system ─────────────────────────────────────────────────────────────
apply_global_styles()

st.markdown("""
<style>
.op-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 20px 22px 16px 22px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  height: 100%;
  transition: box-shadow 0.2s, transform 0.2s;
}
.op-card:hover { box-shadow: 0 6px 16px rgba(0,0,0,0.09); transform: translateY(-2px); }
.op-kpi-label {
  font-size: 0.76rem; font-weight: 700; color: #64748b;
  text-transform: uppercase; letter-spacing: 0.06em;
  display: flex; align-items: center; gap: 6px; margin-bottom: 8px;
}
.op-kpi-icon { color: #6366f1; font-size: 1.15rem; }
.op-kpi-value { font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1.1; }
.op-kpi-denom { font-size: 1.1rem; color: #64748b; font-weight: 500; }
.op-kpi-sub   { font-size: 0.78rem; color: #64748b; margin-top: 3px; }
.op-kpi-bar   { height: 4px; border-radius: 2px; background: #e2e8f0; margin-top: 10px; overflow: hidden; }
.op-kpi-fill  { height: 100%; border-radius: 2px; }

.op-section-h {
  font-size: 0.95rem; font-weight: 700; color: #0f172a;
  display: flex; align-items: center; gap: 8px; margin: 0 0 14px 0;
}
.op-section-h .material-symbols-rounded { font-size: 1.15rem; color: #3b82f6; }
</style>
""", unsafe_allow_html=True)

render_sidebar()

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='margin-bottom:2px;'>"
    "<span class='material-symbols-rounded' style='font-size:2rem;vertical-align:middle;"
    "margin-right:10px;color:#3b82f6;'>assignment</span>"
    "Outreach Planner</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#64748b;font-size:1rem;margin:0 0 18px 0;'>"
    "Review and manage the optimised, capacity-constrained outreach plan.</p>",
    unsafe_allow_html=True,
)
st.markdown("<hr style='margin:0 0 20px 0;border:0;border-top:1px solid #e2e8f0;'>",
            unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

df = AppState.get_pipeline_results()
if df is None or df.empty:
    show_pipeline_uninitialized()
    st.stop()

warnings = AppState.get_fairness_warnings()

# ── Derived Metrics ───────────────────────────────────────────────────────────
total       = len(df)
is_sel      = df.get("selected_for_outreach", pd.Series(False, index=df.index)).astype(bool)
selected    = int(is_sel.sum())
total_cap   = settings.number_of_teams * settings.maximum_visits_per_team

risk_col    = "multi_factor_risk_category" if "multi_factor_risk_category" in df.columns else "risk_level"
extreme     = int((df[risk_col].isin(["EXTREME", "VERY HIGH"])).sum()) if risk_col in df.columns else 0
manual_rev  = int((df["fallback_status"] == "MANUAL_REVIEW").sum()) if "fallback_status" in df.columns else 0
cap_ok      = selected <= total_cap

def _pbar(pct: float, color: str) -> str:
    pct = min(max(pct, 0), 100)
    return (f"<div class='op-kpi-bar'>"
            f"<div class='op-kpi-fill' style='width:{pct:.0f}%;background:{color};'></div>"
            f"</div>")

# ── KPI Cards ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

coverage_pct = (selected / total * 100) if total > 0 else 0
cap_color    = "#10b981" if cap_ok else "#ef4444"
cap_label    = "Within Capacity" if cap_ok else "Over Capacity"

with k1:
    st.markdown(f"""
    <div class='op-card'>
      <div class='op-kpi-label'>
        <span class='material-symbols-rounded op-kpi-icon'>location_city</span>Total Neighbourhoods
      </div>
      <div class='op-kpi-value'>{total:,}</div>
      <div class='op-kpi-sub'>In active dataset</div>
      {_pbar(100, '#94a3b8')}
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class='op-card'>
      <div class='op-kpi-label'>
        <span class='material-symbols-rounded op-kpi-icon'>check_circle</span>Selected for Outreach
      </div>
      <div class='op-kpi-value' style='color:#3b82f6;'>{selected}
        <span class='op-kpi-denom'> / {total_cap}</span>
      </div>
      <div class='op-kpi-sub'>{coverage_pct:.1f}% neighbourhood coverage</div>
      {_pbar(coverage_pct, '#3b82f6')}
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class='op-card'>
      <div class='op-kpi-label'>
        <span class='material-symbols-rounded op-kpi-icon'>local_fire_department</span>Extreme Risk Zones
      </div>
      <div class='op-kpi-value' style='color:#ef4444;'>{extreme}</div>
      <div class='op-kpi-sub'>EXTREME / VERY HIGH risk</div>
      {_pbar((extreme / total * 100) if total > 0 else 0, '#ef4444')}
    </div>""", unsafe_allow_html=True)

with k4:
    mr_color = "#f59e0b" if manual_rev > 0 else "#10b981"
    st.markdown(f"""
    <div class='op-card'>
      <div class='op-kpi-label'>
        <span class='material-symbols-rounded op-kpi-icon'>visibility</span>Review Needed
      </div>
      <div class='op-kpi-value' style='color:{mr_color};'>{manual_rev}</div>
      <div class='op-kpi-sub'>Flagged for manual review</div>
      {_pbar((manual_rev / total * 100) if total > 0 else 0, mr_color)}
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Capacity Status Banner ────────────────────────────────────────────────────
cap_bg   = "#f0fdf4" if cap_ok else "#fef2f2"
cap_bc   = "#86efac" if cap_ok else "#fca5a5"
cap_icon = "check_circle" if cap_ok else "warning"
cap_tc   = "#166534" if cap_ok else "#991b1b"
st.markdown(
    f"<div style='background:{cap_bg};border:1px solid {cap_bc};border-radius:10px;"
    f"padding:12px 18px;display:flex;align-items:center;gap:10px;margin-bottom:20px;'>"
    f"<span class='material-symbols-rounded' style='color:{cap_color};'>{cap_icon}</span>"
    f"<span style='font-weight:700;color:{cap_tc};'>{cap_label}</span>"
    f"<span style='color:{cap_tc};font-size:0.85rem;'>&nbsp;— {selected} events planned out of {total_cap} capacity "
    f"({settings.number_of_teams} teams × {settings.maximum_visits_per_team} visits/team)</span>"
    f"</div>",
    unsafe_allow_html=True,
)

# ── Operational Constraint Status ─────────────────────────────────────────────
with st.container(border=True):
    st.markdown(
        "<div class='op-section-h'>"
        "<span class='material-symbols-rounded'>rule</span>"
        "Operational Constraint Status</div>",
        unsafe_allow_html=True,
    )
    render_constraint_status()

st.markdown("<br>", unsafe_allow_html=True)

# ── Geographically Clustered Schedule ────────────────────────────────────────
with st.container(border=True):
    st.markdown(
        "<div class='op-section-h'>"
        "<span class='material-symbols-rounded'>map</span>"
        "Geographically Clustered Outreach Schedule</div>",
        unsafe_allow_html=True,
    )
    render_schedule_view(df)

st.markdown("<br>", unsafe_allow_html=True)

# ── Priority Neighbourhoods Table ─────────────────────────────────────────────
with st.container(border=True):
    st.markdown(
        "<div class='op-section-h'>"
        "<span class='material-symbols-rounded'>priority_high</span>"
        "Priority Neighbourhoods</div>",
        unsafe_allow_html=True,
    )

    filter_col, _ = st.columns([2, 5])
    with filter_col:
        filter_option = st.selectbox(
            "Filter by Priority Status",
            ["All", "PRIMARY_OUTREACH", "WAITLIST_HIGH_RISK", "NEEDS_REVIEW", "NO_ACTION"],
            label_visibility="collapsed",
        )

    display_cols = [
        "neighbourhood_id", "neighbourhood_name", "district",
        "multi_factor_risk_category", "multi_factor_risk_score",
        "confidence_score", "fallback_status", "selected_for_outreach",
        "outreach_priority", "assigned_team", "outreach_date",
    ]
    available_cols = [c for c in display_cols if c in df.columns]

    sort_score_col = next((c for c in ["multi_factor_risk_score", "risk_score"] if c in df.columns), None)
    sorted_df = (df[available_cols].sort_values(sort_score_col, ascending=False).copy()
                 if sort_score_col else df[available_cols].copy())

    if filter_option != "All" and "outreach_priority" in sorted_df.columns:
        sorted_df = sorted_df[sorted_df["outreach_priority"] == filter_option]

    rename_map = {
        "neighbourhood_id":           "ID",
        "neighbourhood_name":         "Neighbourhood",
        "district":                   "District",
        "multi_factor_risk_category": "Risk Level",
        "multi_factor_risk_score":    "Risk Score",
        "confidence_score":           "Confidence",
        "fallback_status":            "Fallback",
        "selected_for_outreach":      "Selected",
        "outreach_priority":          "Priority",
        "assigned_team":              "Team",
        "outreach_date":              "Date",
    }
    sorted_df.rename(columns={k: v for k, v in rename_map.items() if k in sorted_df.columns},
                     inplace=True)

    if "Risk Score" in sorted_df.columns:
        sorted_df["Risk Score"] = sorted_df["Risk Score"].round(3)
    if "Confidence" in sorted_df.columns:
        sorted_df["Confidence"] = sorted_df["Confidence"].round(2)

    def _highlight(val):
        return {
            "EXTREME":   "background-color:#fef2f2;color:#dc2626;font-weight:600;",
            "VERY HIGH": "background-color:#fef2f2;color:#dc2626;font-weight:600;",
            "HIGH":      "background-color:#fff7ed;color:#ea580c;font-weight:600;",
            "MODERATE":  "background-color:#fefce8;color:#ca8a04;",
            "LOW":       "background-color:#f0fdf4;color:#16a34a;",
        }.get(str(val), "")

    col_cfg = {}
    if "ID" in sorted_df.columns:
        col_cfg["ID"] = st.column_config.TextColumn("ID", width="small")
    if "Risk Score" in sorted_df.columns:
        col_cfg["Risk Score"] = st.column_config.NumberColumn("Risk Score", width="small", format="%.3f")
    if "Risk Level" in sorted_df.columns:
        col_cfg["Risk Level"] = st.column_config.TextColumn("Risk Level", width="small")
    if "Confidence" in sorted_df.columns:
        col_cfg["Confidence"] = st.column_config.NumberColumn("Confidence", width="small", format="%.2f")
    if "Selected" in sorted_df.columns:
        col_cfg["Selected"] = st.column_config.CheckboxColumn("Selected", width="small")
    if "Team" in sorted_df.columns:
        col_cfg["Team"] = st.column_config.TextColumn("Team", width="small")
    if "Date" in sorted_df.columns:
        col_cfg["Date"] = st.column_config.TextColumn("Date", width="small")
    if "Priority" in sorted_df.columns:
        col_cfg["Priority"] = st.column_config.TextColumn("Priority", width="medium")
    if "Fallback" in sorted_df.columns:
        col_cfg["Fallback"] = st.column_config.TextColumn("Fallback", width="small")

    style_subset = [c for c in ["Risk Level"] if c in sorted_df.columns]
    styled_df = sorted_df.style
    if style_subset:
        styled_df = styled_df.map(_highlight, subset=style_subset)

    st.dataframe(
        styled_df,
        use_container_width=True,
        height=420,
        hide_index=True,
        column_config=col_cfg,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Manual Override ───────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown(
        "<div class='op-section-h'>"
        "<span class='material-symbols-rounded'>edit_note</span>"
        "Manual Override</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:0.88rem;color:#64748b;margin:-6px 0 16px 0;'>"
        "Manually override the system's selection. All actions are strictly audit-logged "
        "and cannot be reversed without a second override.</p>",
        unsafe_allow_html=True,
    )

    ov_col1, ov_col2 = st.columns(2, gap="medium")

    with ov_col1:
        ov_id   = st.selectbox("Neighbourhood ID", df["neighbourhood_id"].tolist(),
                               key="ov_id")
        ov_user = st.text_input("Authorised User ID", value="admin", key="ov_user")

    with ov_col2:
        ov_action = st.radio("Override Action",
                             ["Force SELECT", "Force DESELECT"],
                             key="ov_action",
                             horizontal=True)
        ov_reason = st.text_area("Mandatory Reason for Override", height=100,
                                 placeholder="State the clinical/operational justification…",
                                 key="ov_reason")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Apply Override", type="primary", use_container_width=False):
        if not ov_reason.strip():
            st.error("A mandatory reason must be provided before overriding.")
        else:
            try:
                audit_log = AuditLogger(log_path="logs/audit.jsonl")
                manager   = OverrideManager(audit_logger=audit_log)
                updated   = manager.force_selection(
                    df=st.session_state.pipeline_results,
                    neighbourhood_id=ov_id,
                    user=ov_user,
                    reason=ov_reason,
                    force_select=(ov_action == "Force SELECT"),
                )
                st.session_state.pipeline_results = updated
                st.success(f"Override applied for {ov_id}. The plan has been updated.")
                st.rerun()
            except Exception as _e:
                st.error("Failed to apply override. Check system logs for details.")
