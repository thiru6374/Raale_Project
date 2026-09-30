"""
app/pages/overview.py — Heat-Risk Communication & Outreach Planner
Primary Executive Dashboard — all values sourced from the canonical pipeline/AppState.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.services.app_state import AppState
from src.services.system_health_service import SystemHealthService
from src.config.settings import settings

from app.components.layout import apply_global_styles, status_badge
from app.components.sidebar import render_sidebar
from app.components.empty_states import show_pipeline_uninitialized

# ── Design system ─────────────────────────────────────────────────────────────
apply_global_styles()

st.markdown("""
<style>
/* ── Dashboard-specific tokens ── */
.ov-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 20px 22px 18px 22px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  height: 100%;
  transition: box-shadow 0.2s, transform 0.2s;
}
.ov-card:hover {
  box-shadow: 0 6px 16px rgba(0,0,0,0.10);
  transform: translateY(-2px);
}
.ov-kpi-label {
  font-size: 0.76rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.ov-kpi-icon { color: #6366f1; font-size: 1.1rem; }
.ov-kpi-value {
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.1;
}
.ov-kpi-denom { font-size: 1.1rem; color: #64748b; font-weight: 500; }
.ov-kpi-sub   { font-size: 0.78rem; color: #64748b; margin-top: 3px; }
.ov-kpi-bar   { height: 4px; border-radius: 2px; background: #e2e8f0; margin-top: 10px; overflow: hidden; }
.ov-kpi-fill  { height: 100%; border-radius: 2px; }

/* Section heading */
.ov-section-h {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px 0;
}
.ov-section-h .material-symbols-rounded { font-size: 1.15rem; color: #3b82f6; }

/* Risk badges */
.rb-vh { background:#fef2f2; color:#dc2626; padding:2px 8px; border-radius:6px;
         font-size:0.7rem; font-weight:700; border:1px solid #fca5a5; }
.rb-h  { background:#fff7ed; color:#ea580c; padding:2px 8px; border-radius:6px;
         font-size:0.7rem; font-weight:700; border:1px solid #fed7aa; }
.rb-m  { background:#fefce8; color:#ca8a04; padding:2px 8px; border-radius:6px;
         font-size:0.7rem; font-weight:700; border:1px solid #fde68a; }
.rb-l  { background:#f0fdf4; color:#16a34a; padding:2px 8px; border-radius:6px;
         font-size:0.7rem; font-weight:700; border:1px solid #86efac; }

/* Compact alert pills */
.ov-alert-warn { background:#fffbeb; border-left:3px solid #f59e0b; padding:8px 12px;
                 border-radius:4px; font-size:0.82rem; color:#92400e; margin-bottom:6px; }
.ov-alert-ok   { background:#f0fdf4; border-left:3px solid #22c55e; padding:8px 12px;
                 border-radius:4px; font-size:0.82rem; color:#166534; margin-bottom:6px; }
.ov-alert-info { background:#eff6ff; border-left:3px solid #3b82f6; padding:8px 12px;
                 border-radius:4px; font-size:0.82rem; color:#1e40af; margin-bottom:6px; }

/* Dataset pill */
.ds-pill {
  background:#f1f5f9; border:1px solid #e2e8f0; border-radius:20px;
  padding:4px 14px; font-size:0.75rem; color:#475569; display:inline-block;
  margin-bottom:18px;
}

/* Nav links inside cards */
.ov-nav-link {
  font-size:0.8rem; color:#3b82f6; font-weight:600; text-decoration:none;
  display:block; text-align:right; margin-top:10px;
}

/* Table tweaks */
[data-testid="stDataFrame"] { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

render_sidebar()

# ── Initialize pipeline ───────────────────────────────────────────────────────
AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

# ── Page Header ───────────────────────────────────────────────────────────────
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.markdown(
        "<h1 style='margin-bottom:2px;'>"
        "<span class='material-symbols-rounded' style='font-size:2rem;vertical-align:middle;"
        "margin-right:10px;color:#3b82f6;'>dashboard</span>"
        "Heat-Risk Communication &amp; Outreach Planner</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#64748b;font-size:1rem;margin:0;'>"
        "Mobile Population Vaccination Outreach — Decision Support System</p>",
        unsafe_allow_html=True,
    )
with col_btn:
    st.write("")
    if st.button("Run / Refresh Analysis", use_container_width=True, type="primary"):
        AppState.initialize_application(force_refresh=True)
        st.rerun()

# Dataset pill
ds_info = AppState.get_active_dataset_info()
ds_name = ds_info.get("dataset_name", "Unknown")
ds_rows = ds_info.get("dataset_rows", 0)
st.markdown(
    f"<div><span class='ds-pill'>"
    f"<span class='material-symbols-rounded' style='font-size:0.85rem;vertical-align:middle;'>database</span>"
    f" {ds_name} &nbsp;|&nbsp; {ds_rows:,} records</span></div>",
    unsafe_allow_html=True,
)
st.markdown("<hr style='margin:0 0 20px 0;border:0;border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

# ── Load pipeline data ────────────────────────────────────────────────────────
res = AppState.get_full_results()
pipeline_df = res.get("pipeline_results")
fairness_warnings = res.get("fairness_warnings", [])
baseline_res = res.get("baseline_results")
health = SystemHealthService.get_system_health()

if pipeline_df is None or pipeline_df.empty:
    show_pipeline_uninitialized()
    st.stop()

df = pipeline_df.copy()

# ── Schema normalisation ──────────────────────────────────────────────────────
if "risk_level" not in df.columns:
    if "multi_factor_risk_category" in df.columns:
        _rmap = {"EXTREME": "VERY HIGH", "VERY HIGH": "VERY HIGH",
                 "HIGH": "HIGH", "MODERATE": "MODERATE", "MEDIUM": "MODERATE", "LOW": "LOW"}
        df["risk_level"] = df["multi_factor_risk_category"].map(_rmap).fillna("LOW")
    else:
        df["risk_level"] = "LOW"

if "risk_score" not in df.columns:
    for _c in ("multi_factor_risk_score", "composite_risk_score", "temperature_c"):
        if _c in df.columns:
            df["risk_score"] = df[_c]
            break
    else:
        df["risk_score"] = 0.0

# ── Derived metrics ───────────────────────────────────────────────────────────
total_cap = settings.number_of_teams * settings.maximum_visits_per_team
is_sel = df.get("selected_for_outreach", pd.Series(False, index=df.index)).astype(bool)
selected_df = df[is_sel]
selected_count = int(is_sel.sum())

is_hr = df["risk_level"].isin(["HIGH", "VERY HIGH"])
high_risk_count = int(is_hr.sum())
high_risk_reached = int((is_hr & is_sel).sum())

# Mobile population
if "mobile_population" in df.columns:
    mobile_total  = int(df["mobile_population"].sum())
    mobile_reached = int(df.loc[is_sel, "mobile_population"].sum()) if is_sel.any() else 0
elif "group_mobile" in df.columns:
    gm = df["group_mobile"].astype(bool)
    pop_col = "total_population" if "total_population" in df.columns else None
    mobile_total  = int(df.loc[gm, pop_col].sum()) if pop_col else int(gm.sum())
    mobile_reached = int(df.loc[gm & is_sel, pop_col].sum()) if pop_col else int((gm & is_sel).sum())
else:
    mobile_total = mobile_reached = 0
mobile_pct = (mobile_reached / mobile_total * 100) if mobile_total > 0 else 0

# Low service access
if "group_low_service_access" in df.columns:
    glsa = df["group_low_service_access"].astype(bool)
    pop_col2 = "total_population" if "total_population" in df.columns else None
    lsa_total  = int(df.loc[glsa, pop_col2].sum()) if pop_col2 else int(glsa.sum())
    lsa_reached = int(df.loc[glsa & is_sel, pop_col2].sum()) if pop_col2 else int((glsa & is_sel).sum())
else:
    lsa_total = lsa_reached = 0
lsa_pct = (lsa_reached / lsa_total * 100) if lsa_total > 0 else 0

avg_conf = float(df["confidence_score"].mean()) if "confidence_score" in df.columns else None

if "healthcare_distance_km" in df.columns and is_sel.any():
    avg_travel_min = float(df.loc[is_sel, "healthcare_distance_km"].mean() / 30.0 * 60)
else:
    avg_travel_min = None

cap_ok    = selected_count <= total_cap
travel_ok = (avg_travel_min is not None and avg_travel_min <= settings.maximum_travel_time)

# ── Helper: progress bar HTML ─────────────────────────────────────────────────
def _pbar(pct: float, color: str) -> str:
    pct = min(max(pct, 0), 100)
    return (
        f"<div class='ov-kpi-bar'>"
        f"<div class='ov-kpi-fill' style='width:{pct:.0f}%;background:{color};'></div>"
        f"</div>"
    )

# ── KPI Cards Row ─────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(f"""
    <div class='ov-card'>
      <div class='ov-kpi-label'>
        <span class='material-symbols-rounded ov-kpi-icon'>warning</span>High-Risk Reached
      </div>
      <div class='ov-kpi-value' style='color:#ef4444;'>{high_risk_reached}
        <span class='ov-kpi-denom'> / {high_risk_count}</span>
      </div>
      <div class='ov-kpi-sub'>Neighbourhoods in plan</div>
      {_pbar((high_risk_reached/high_risk_count*100) if high_risk_count > 0 else 0, '#ef4444')}
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class='ov-card'>
      <div class='ov-kpi-label'>
        <span class='material-symbols-rounded ov-kpi-icon'>smartphone</span>Mobile Pop. Reached
      </div>
      <div class='ov-kpi-value'>{mobile_reached:,}
        <span class='ov-kpi-denom'> / {mobile_total:,}</span>
      </div>
      <div class='ov-kpi-sub'>{mobile_pct:.1f}% covered — target 70%</div>
      {_pbar(mobile_pct, '#3b82f6')}
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class='ov-card'>
      <div class='ov-kpi-label'>
        <span class='material-symbols-rounded ov-kpi-icon'>local_hospital</span>Low-Service Reached
      </div>
      <div class='ov-kpi-value'>{lsa_reached:,}
        <span class='ov-kpi-denom'> / {lsa_total:,}</span>
      </div>
      <div class='ov-kpi-sub'>{lsa_pct:.1f}% covered — target 70%</div>
      {_pbar(lsa_pct, '#8b5cf6')}
    </div>""", unsafe_allow_html=True)

with k4:
    cap_color = "#10b981" if cap_ok else "#ef4444"
    cap_label = "Within Capacity" if cap_ok else "Over Capacity"
    st.markdown(f"""
    <div class='ov-card'>
      <div class='ov-kpi-label'>
        <span class='material-symbols-rounded ov-kpi-icon'>calendar_today</span>Planned Events
      </div>
      <div class='ov-kpi-value'>{selected_count}</div>
      <div class='ov-kpi-sub' style='color:{cap_color};font-weight:700;'>{cap_label}</div>
      <div class='ov-kpi-sub'>Capacity: {total_cap} events</div>
      {_pbar((selected_count/total_cap*100) if total_cap > 0 else 0, cap_color)}
    </div>""", unsafe_allow_html=True)

with k5:
    if avg_travel_min is not None:
        tv_color = "#10b981" if travel_ok else "#ef4444"
        tv_label = "Within Target" if travel_ok else "Over Target"
        tv_val   = f"{avg_travel_min:.1f} min"
    else:
        tv_color, tv_label, tv_val = "#94a3b8", "No schedule data", "N/A"
    st.markdown(f"""
    <div class='ov-card'>
      <div class='ov-kpi-label'>
        <span class='material-symbols-rounded ov-kpi-icon'>directions_car</span>Avg. Travel Time
      </div>
      <div class='ov-kpi-value'>{tv_val}</div>
      <div class='ov-kpi-sub' style='color:{tv_color};font-weight:700;'>{tv_label}</div>
      <div class='ov-kpi-sub'>Target &le; {settings.maximum_travel_time} min</div>
      {_pbar((avg_travel_min/settings.maximum_travel_time*100) if avg_travel_min else 0, tv_color)}
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 1: Map (wide) + Baseline Comparison (narrow) ─────────────────────────
map_col, compare_col = st.columns([1, 1], gap="medium")

with map_col:
    with st.container(border=True):
        st.markdown(
            "<div class='ov-section-h'>"
            "<span class='material-symbols-rounded'>map</span>"
            "Heat-Risk Map (Active Dataset)</div>",
            unsafe_allow_html=True,
        )
        try:
            from src.utils.map_utils import (
                prepare_map_dataframe, scatter_map as geo_scatter_map,
                RISK_COLOR_MAP, CHENNAI_CENTER,
            )
            map_df, map_info = prepare_map_dataframe(df)

            if map_df is not None and not map_df.empty:
                hover_data = {c: True for c in
                              ("district", "_map_risk_score", "mobile_population",
                               "confidence_score", "outreach_priority")
                              if c in map_df.columns}

                fig_map = geo_scatter_map(
                    data_frame=map_df,
                    lat="_map_lat", lon="_map_lon",
                    color="_map_risk_level",
                    size="_map_risk_score",
                    hover_name="neighbourhood_name" if "neighbourhood_name" in map_df.columns else None,
                    hover_data=hover_data or None,
                    color_discrete_map=RISK_COLOR_MAP,
                    map_style="carto-positron",
                    center=map_info.get("centre", CHENNAI_CENTER),
                    zoom=10, height=420, opacity=0.85, size_max=20,
                )
                fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                                      legend=dict(orientation="v", yanchor="top", y=0.98,
                                                  xanchor="left", x=0.01,
                                                  bgcolor="rgba(255,255,255,0.88)",
                                                  bordercolor="#e2e8f0", borderwidth=1,
                                                  font=dict(size=10)))

                # Planned events overlay
                sel_map = map_df[map_df.get("selected_for_outreach",
                                            pd.Series(False, index=map_df.index)).astype(bool)]
                if len(sel_map) > 0 and hasattr(go, "Scattermap"):
                    fig_map.add_trace(go.Scattermap(
                        lat=sel_map["_map_lat"], lon=sel_map["_map_lon"],
                        mode="markers",
                        marker=dict(size=12, color="#3b82f6", symbol="circle"),
                        name="Planned Event",
                        customdata=sel_map[["neighbourhood_name"]].values
                                   if "neighbourhood_name" in sel_map.columns else None,
                        hovertemplate="<b>Planned Event</b><br>"
                                      + ("%{customdata[0]}" if "neighbourhood_name" in sel_map.columns else "")
                                      + "<extra></extra>",
                    ))

                st.plotly_chart(fig_map, use_container_width=True,
                                config={"displayModeBar": True, "scrollZoom": True})
            else:
                st.info("Map data not available.")

        except Exception as _map_err:
            import logging as _log
            _log.getLogger(__name__).error("Dashboard map error: %s", _map_err, exc_info=True)
            st.markdown(
                "<div style='background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;"
                "padding:16px;font-size:0.85rem;color:#991b1b;'>"
                "<span class='material-symbols-rounded' style='color:#ef4444;'>error</span>"
                " Map rendering error. Use the Risk Map page for the full interactive map.</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div style='text-align:right;margin-top:6px;'>"
            "<a class='ov-nav-link' href='pages/risk_map'>Full Risk Map &rarr;</a></div>",
            unsafe_allow_html=True,
        )

with compare_col:
    with st.container(border=True):
        st.markdown(
            "<div class='ov-section-h'>"
            "<span class='material-symbols-rounded'>stacked_bar_chart</span>"
            "Baseline vs Proposed</div>",
            unsafe_allow_html=True,
        )
        try:
            bl = baseline_res
            if bl and hasattr(bl, "records") and bl.records:
                bl_sel_ids = {r.neighbourhood_id for r in bl.records if getattr(r, "baseline_selected", False)}
                hr_ids     = set(df.loc[is_hr, "neighbourhood_id"]) if "neighbourhood_id" in df.columns else set()
                bl_hr_matched = len(bl_sel_ids & hr_ids)

                labels    = ["High-Risk\nCoverage", "Mobile Pop\nCoverage (%)", "Low-Service\nCoverage (%)"]
                bl_vals   = [(bl_hr_matched / high_risk_count * 100) if high_risk_count > 0 else 0, 0, 0]
                prop_vals = [
                    (high_risk_reached / high_risk_count * 100) if high_risk_count > 0 else 0,
                    mobile_pct,
                    lsa_pct,
                ]

                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    name="Baseline (Temp Only)", x=labels, y=bl_vals,
                    marker_color="#ef4444",
                    text=[f"{v:.1f}%" for v in bl_vals], textposition="outside",
                ))
                fig_bar.add_trace(go.Bar(
                    name="Proposed (Multi-factor)", x=labels, y=prop_vals,
                    marker_color="#10b981",
                    text=[f"{v:.1f}%" for v in prop_vals], textposition="outside",
                ))
                fig_bar.update_layout(
                    barmode="group", height=380,
                    margin=dict(l=10, r=10, t=20, b=10),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=-0.18, font=dict(size=10)),
                    yaxis=dict(title="Coverage (%)", range=[0, 115]),
                    font=dict(size=11),
                )
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Baseline comparison not available yet.")
        except Exception:
            st.info("Baseline comparison not available.")

        st.markdown(
            "<div style='text-align:right;margin-top:6px;'>"
            "<a class='ov-nav-link' href='pages/baseline'>Full Comparison &rarr;</a></div>",
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 2: Outreach Schedule (full width) ─────────────────────────────────────
with st.container(border=True):
    st.markdown(
        "<div class='ov-section-h'>"
        "<span class='material-symbols-rounded'>schedule</span>"
        "Outreach Schedule (Upcoming)</div>",
        unsafe_allow_html=True,
    )
    try:
        if "selected_for_outreach" in df.columns and "outreach_date" in df.columns:
            sched_df = df[df["selected_for_outreach"] == True].copy()
            if not sched_df.empty:
                # Compact column selection — only what's needed
                col_map = {
                    "outreach_date":    "Date",
                    "neighbourhood_name": "Neighbourhood",
                    "neighbourhood_id": "ID",
                    "district":         "District",
                    "risk_level":       "Risk Level",
                    "outreach_priority":"Event Type",
                    "mobile_population": "Mobile Pop",
                    "assigned_team":    "Team",
                    "start_time":       "Start",
                    "end_time":         "End",
                }
                avail = {k: v for k, v in col_map.items() if k in sched_df.columns}
                sched_disp = sched_df[list(avail.keys())].head(10).rename(columns=avail)

                # Style risk levels
                def _risk_style(val):
                    return {
                        "VERY HIGH": "background-color:#fef2f2;color:#dc2626;font-weight:600;",
                        "HIGH":      "background-color:#fff7ed;color:#ea580c;font-weight:600;",
                        "MODERATE":  "background-color:#fefce8;color:#ca8a04;",
                        "LOW":       "background-color:#f0fdf4;color:#16a34a;",
                    }.get(str(val), "")

                styler = sched_disp.style
                if "Risk Level" in sched_disp.columns:
                    styler = styler.map(_risk_style, subset=["Risk Level"])

                # Compact column widths via column_config
                col_cfg = {}
                if "Date" in sched_disp.columns:
                    col_cfg["Date"] = st.column_config.TextColumn("Date", width="small")
                if "ID" in sched_disp.columns:
                    col_cfg["ID"] = st.column_config.TextColumn("ID", width="small")
                if "Risk Level" in sched_disp.columns:
                    col_cfg["Risk Level"] = st.column_config.TextColumn("Risk Level", width="small")
                if "Event Type" in sched_disp.columns:
                    col_cfg["Event Type"] = st.column_config.TextColumn("Event Type", width="small")
                if "Mobile Pop" in sched_disp.columns:
                    col_cfg["Mobile Pop"] = st.column_config.NumberColumn("Mobile Pop", width="small", format="%d")
                if "Team" in sched_disp.columns:
                    col_cfg["Team"] = st.column_config.TextColumn("Team", width="small")
                if "Start" in sched_disp.columns:
                    col_cfg["Start"] = st.column_config.TextColumn("Start", width="small")
                if "End" in sched_disp.columns:
                    col_cfg["End"] = st.column_config.TextColumn("End", width="small")

                st.dataframe(
                    styler,
                    use_container_width=True,
                    hide_index=True,
                    column_config=col_cfg,
                )
            else:
                st.info("No outreach events scheduled yet.")
        else:
            st.info("Schedule data not yet available — run the analysis.")
    except Exception:
        st.info("Schedule not available.")

    st.markdown(
        "<div style='text-align:right;margin-top:6px;'>"
        "<a class='ov-nav-link' href='pages/outreach_planner'>Full Schedule &rarr;</a></div>",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 3: Priority Table (left) + Fairness & Comms + Alerts (right) ─────────
pri_col, right_col = st.columns([3, 2], gap="medium")

with pri_col:
    with st.container(border=True):
        st.markdown(
            "<div class='ov-section-h'>"
            "<span class='material-symbols-rounded'>priority_high</span>"
            "Top Priority Neighbourhoods</div>",
            unsafe_allow_html=True,
        )
        try:
            sort_col_opt = next(
                (c for c in ["multi_factor_risk_score", "risk_score", "composite_risk_score"]
                 if c in df.columns), None
            )
            top_df = (df[is_hr].sort_values(sort_col_opt, ascending=False).head(10)
                      if sort_col_opt else df[is_hr].head(10))

            cols_want = {
                "neighbourhood_id":   "ID",
                "neighbourhood_name": "Neighbourhood",
                "district":           "District",
                sort_col_opt:         "Risk Score",
                "risk_level":         "Risk Level",
                "mobile_population":  "Mobile Pop",
                "outreach_priority":  "Action",
                "confidence_score":   "Conf.",
                "assigned_team":      "Team",
            }
            avail2 = {k: v for k, v in cols_want.items() if k and k in top_df.columns}
            prio_disp = top_df[list(avail2.keys())].rename(columns=avail2).reset_index(drop=True)
            prio_disp.index += 1

            if "Risk Score" in prio_disp.columns:
                prio_disp["Risk Score"] = prio_disp["Risk Score"].round(3)
            if "Conf." in prio_disp.columns:
                prio_disp["Conf."] = prio_disp["Conf."].round(2)

            pri_cfg = {}
            if "ID" in prio_disp.columns:
                pri_cfg["ID"] = st.column_config.TextColumn("ID", width="small")
            if "Risk Score" in prio_disp.columns:
                pri_cfg["Risk Score"] = st.column_config.NumberColumn("Risk Score", width="small", format="%.3f")
            if "Risk Level" in prio_disp.columns:
                pri_cfg["Risk Level"] = st.column_config.TextColumn("Risk Level", width="small")
            if "Mobile Pop" in prio_disp.columns:
                pri_cfg["Mobile Pop"] = st.column_config.NumberColumn("Mobile Pop", width="small", format="%d")
            if "Action" in prio_disp.columns:
                pri_cfg["Action"] = st.column_config.TextColumn("Action", width="small")
            if "Conf." in prio_disp.columns:
                pri_cfg["Conf."] = st.column_config.NumberColumn("Conf.", width="small", format="%.2f")
            if "Team" in prio_disp.columns:
                pri_cfg["Team"] = st.column_config.TextColumn("Team", width="small")

            st.dataframe(prio_disp, use_container_width=True, column_config=pri_cfg)
        except Exception as _e:
            st.info("Priority data not available.")

with right_col:
    # ── Fairness & Bias Summary ────────────────────────────────────────────
    with st.container(border=True):
        st.markdown(
            "<div class='ov-section-h'>"
            "<span class='material-symbols-rounded'>balance</span>"
            "Fairness &amp; Bias Summary</div>",
            unsafe_allow_html=True,
        )
        try:
            grp_defs = {
                "group_mobile":             "Mobile Population",
                "group_low_service_access": "Low Service Access",
            }
            any_grp = False
            for gc, gname in grp_defs.items():
                if gc not in df.columns:
                    continue
                g_mask = df[gc].astype(bool)
                g_total = int(g_mask.sum())
                g_sel   = int((g_mask & is_sel).sum())
                overall_rate = selected_count / len(df) if len(df) > 0 else 0
                grp_rate = g_sel / g_total if g_total > 0 else 0
                parity   = grp_rate / overall_rate if overall_rate > 0 else 0
                gap      = abs(grp_rate - overall_rate)
                ok = parity >= 0.8
                sc = "#10b981" if ok else "#f59e0b"
                sl = "Acceptable" if ok else "Review Required"
                any_grp = True
                st.markdown(f"""
                <div style='margin-bottom:12px;'>
                  <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <span style='font-size:0.82rem;font-weight:600;color:#334155;'>{gname}</span>
                    <span style='font-size:0.74rem;font-weight:700;color:{sc};'>{sl}</span>
                  </div>
                  <div style='font-size:0.74rem;color:#64748b;margin-top:2px;'>
                    Parity: <b style='color:#0f172a;'>{parity:.2f}</b>
                    &nbsp;|&nbsp; Gap: <b style='color:#0f172a;'>{gap:.1%}</b>
                  </div>
                </div>""", unsafe_allow_html=True)
            if not any_grp:
                if fairness_warnings:
                    for w in fairness_warnings[:2]:
                        msg = w.get("message", str(w)) if isinstance(w, dict) else str(w)
                        st.markdown(f"<div class='ov-alert-warn'>{msg}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='ov-alert-ok'>No fairness violations detected.</div>",
                                unsafe_allow_html=True)
        except Exception:
            st.info("Fairness data not available.")
        st.markdown(
            "<div style='text-align:right;margin-top:6px;'>"
            "<a class='ov-nav-link' href='pages/fairness_analysis'>Full Fairness Report &rarr;</a></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Communication Preview ──────────────────────────────────────────────
    with st.container(border=True):
        st.markdown(
            "<div class='ov-section-h'>"
            "<span class='material-symbols-rounded'>campaign</span>"
            "Communication Preview</div>",
            unsafe_allow_html=True,
        )
        try:
            if "communication_plan" in df.columns:
                top_comm = (
                    df[is_hr]
                    .sort_values(
                        next((c for c in ["multi_factor_risk_score", "risk_score"]
                              if c in df.columns), df.columns[0]),
                        ascending=False,
                    )
                    .head(3)
                )
                for _, row in top_comm.iterrows():
                    name = row.get("neighbourhood_name", row.get("neighbourhood_id", "N/A"))
                    plan = str(row.get("communication_plan", ""))[:200]
                    st.markdown(
                        f"<div style='margin-bottom:10px;padding:10px 12px;"
                        f"background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;'>"
                        f"<div style='font-size:0.8rem;font-weight:700;color:#0f172a;"
                        f"margin-bottom:4px;'>{name}</div>"
                        f"<div style='font-size:0.75rem;color:#475569;'>{plan}{'…' if len(plan)==200 else ''}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Communication plans not yet available.")
        except Exception:
            st.info("Communication preview not available.")
        st.markdown(
            "<div style='text-align:right;margin-top:6px;'>"
            "<a class='ov-nav-link' href='pages/communication_planner'>Full Comms Plan &rarr;</a></div>",
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 4: Active Overrides & Alerts (full width) ─────────────────────────────
with st.container(border=True):
    st.markdown(
        "<div class='ov-section-h'>"
        "<span class='material-symbols-rounded'>notifications_active</span>"
        "Active Overrides &amp; Alerts</div>",
        unsafe_allow_html=True,
    )
    a1, a2, a3 = st.columns(3)

    with a1:
        st.markdown("<div style='font-size:0.78rem;font-weight:700;color:#64748b;margin-bottom:8px;"
                    "text-transform:uppercase;letter-spacing:0.05em;'>System Health</div>",
                    unsafe_allow_html=True)
        overall = health.get("overall_status", "UNKNOWN") if health else "UNKNOWN"
        cls = "ok" if overall == "HEALTHY" else "warn"
        st.markdown(f"<div class='ov-alert-{cls}'>"
                    f"<span class='material-symbols-rounded' style='font-size:0.9rem;vertical-align:middle;'>"
                    f"{'check_circle' if overall == 'HEALTHY' else 'warning'}</span> {overall}</div>",
                    unsafe_allow_html=True)

    with a2:
        st.markdown("<div style='font-size:0.78rem;font-weight:700;color:#64748b;margin-bottom:8px;"
                    "text-transform:uppercase;letter-spacing:0.05em;'>Fairness</div>",
                    unsafe_allow_html=True)
        if fairness_warnings:
            st.markdown(f"<div class='ov-alert-warn'>"
                        f"<span class='material-symbols-rounded' style='font-size:0.9rem;vertical-align:middle;'>warning</span>"
                        f" {len(fairness_warnings)} warning(s)</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='ov-alert-ok'>"
                        "<span class='material-symbols-rounded' style='font-size:0.9rem;vertical-align:middle;'>"
                        "check_circle</span> All checks passed</div>", unsafe_allow_html=True)

    with a3:
        st.markdown("<div style='font-size:0.78rem;font-weight:700;color:#64748b;margin-bottom:8px;"
                    "text-transform:uppercase;letter-spacing:0.05em;'>Capacity</div>",
                    unsafe_allow_html=True)
        cap_cls = "ok" if cap_ok else "warn"
        cap_icon = "check_circle" if cap_ok else "warning"
        st.markdown(f"<div class='ov-alert-{cap_cls}'>"
                    f"<span class='material-symbols-rounded' style='font-size:0.9rem;vertical-align:middle;'>"
                    f"{cap_icon}</span> {selected_count} / {total_cap} events</div>",
                    unsafe_allow_html=True)

    st.markdown(
        "<div style='text-align:right;margin-top:6px;'>"
        "<a class='ov-nav-link' href='pages/override_audit'>Audit Log &rarr;</a></div>",
        unsafe_allow_html=True,
    )
