"""
app/pages/fairness_analysis.py  –  Fairness audit results.
(UI Redesign)
"""
import streamlit as st
import plotly.express as px

from src.services.app_state import AppState
from app.components.layout import apply_global_styles, page_header, status_badge
from app.components.sidebar import render_sidebar
from app.components.cards import html_card
from app.components.empty_states import show_pipeline_uninitialized

st.set_page_config(page_title="Fairness & Bias Analysis", page_icon="", layout="wide")

apply_global_styles()
render_sidebar()

page_header(" Fairness & Bias Analysis", "Review equity metrics to ensure no demographic group is left behind.", icon=":material/balance:")

AppState.initialize_application()
if AppState.display_error_fallback():
    st.stop()

df = AppState.get_pipeline_results()
if df is None:
    show_pipeline_uninitialized()
    st.stop()

warnings = AppState.get_fairness_warnings()

# ── Audit summary ─────────────────────────────────────────────────────────────
st.markdown("### System-Wide Audit Summary")
if not warnings:
    st.markdown("<div style='background: #dcfce3; color: #10b981; padding: 15px; border-radius: 8px; border: 1px solid #a7f3d0; margin-bottom: 20px;'> <b>Fairness Check Passed:</b> The outreach plan meets all equitable coverage standards. No systemic bias detected.</div>", unsafe_allow_html=True)
else:
    for w in warnings:
        st.markdown(f"<div style='background: #fee2e2; color: #ef4444; padding: 15px; border-radius: 8px; border: 1px solid #fca5a5; margin-bottom: 10px;'> <b>Bias Detected:</b> In group <code>{w.get('group', 'Unknown')}</code>. {w.get('message', '')}</div>", unsafe_allow_html=True)

# ── Per-group breakdown ───────────────────────────────────────────────────────
st.markdown("### Group Coverage Analysis")

GROUPS = {
    "group_mobile": "Mobile Population",
    "group_low_service_access": "Low Service Access",
    "group_vulnerable": "Vulnerable Demographics"
}

any_group_shown = False
for group_col, group_name in GROUPS.items():
    if group_col not in df.columns:
        continue
    group_df = df[df[group_col] == True]
    if len(group_df) == 0:
        continue

    any_group_shown = True
    total_group  = len(group_df)
    sel_group    = int(group_df["selected_for_outreach"].sum())
    total_all    = len(df)
    sel_all      = int(df["selected_for_outreach"].sum())
    
    coverage_all = sel_all / total_all if total_all > 0 else 0
    coverage_grp = sel_group / total_group if total_group > 0 else 0
    
    parity_ratio = coverage_grp / coverage_all if coverage_all > 0 else 0
    parity_stat = "Acceptable" if parity_ratio >= 0.8 else "Review Required"
    parity_color = "success" if parity_ratio >= 0.8 else "critical"

    st.markdown(f"""
    <div style='background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 25px; margin-bottom: 20px;'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
            <h4 style='margin: 0; color: #0f172a;'>{group_name}</h4>
            {status_badge(parity_stat, parity_color)}
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total in Group", f"{total_group:,}", f"{(total_group / total_all)*100:.1f}% of city")
    with c2:
        st.metric("Selected for Outreach", f"{sel_group:,}")
    with c3:
        st.metric("Group Coverage Rate", f"{coverage_grp*100:.1f}%", f"{coverage_grp - coverage_all:.1%} vs global", delta_color="normal" if coverage_grp >= coverage_all else "inverse")
    with c4:
        st.metric("Parity Ratio", f"{parity_ratio:.2f}")

    with st.expander("View Statistical Chart"):
        fig = px.bar(
            x=[f"All Areas ({coverage_all*100:.1f}%)", f"{group_name} ({coverage_grp*100:.1f}%)"],
            y=[coverage_all, coverage_grp],
            labels={"x": "", "y": "Coverage Rate"},
            color=["All", "Group"],
            color_discrete_map={"All": "#94a3b8", "Group": "#3b82f6"},
            height=300
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        
    st.markdown("</div>", unsafe_allow_html=True)

if not any_group_shown:
    st.info("No fairness group columns found in the current dataset.")
