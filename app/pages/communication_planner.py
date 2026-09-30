"""
app/pages/communication_planner.py
Neighbourhood Communication Planner Preview
"""
import json
import streamlit as st
import pandas as pd
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from src.services.app_state import AppState


apply_global_styles()
render_sidebar()

page_header(" Neighbourhood Communication Planner", "Tailored messaging and outreach planning based on local risk and demographics.", icon=":material/campaign:")

AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()

df = AppState.get_pipeline_results()
if df is None or df.empty or 'communication_plan' not in df.columns:
  st.warning("No communication plans available. Please run the pipeline first.")
  st.stop()

st.markdown("""
<style>
.comm-card { background: #0f172a; border: 1px solid #1e3a5f; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
.comm-title { font-size: 1.2rem; font-weight: bold; color: #e2e8f0; margin-bottom: 10px; }
.comm-tag-high { background-color: rgba(255, 75, 75, 0.2); color: #FF4B4B; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; margin-right: 5px; border: 1px solid #FF4B4B; }
.comm-tag-mod { background-color: rgba(255, 193, 7, 0.2); color: #FFC107; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; margin-right: 5px; border: 1px solid #FFC107; }
.comm-tag-low { background-color: rgba(0, 204, 150, 0.2); color: #00CC96; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; margin-right: 5px; border: 1px solid #00CC96; }
.msg-box { background-color: rgba(99, 102, 241, 0.1); border-left: 4px solid #6366f1; padding: 10px; margin-top: 10px; margin-bottom: 10px; border-radius: 4px; font-style: italic; }
.comm-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9rem; }
.comm-grid div span { color: #94a3b8; font-weight: 600; display: block; font-size: 0.8rem; text-transform: uppercase; }
.disclaimer { font-size: 0.8rem; color: #cbd5e1; margin-top: 5px; opacity: 0.8; }
</style>
""", unsafe_allow_html=True)

# Parse communication plans
plans = []
for _, row in df.iterrows():
  if pd.notna(row.get('communication_plan')):
    try:
      plan = json.loads(row['communication_plan'])
      plan['neighbourhood_id'] = row['neighbourhood_id']
      plan['neighbourhood_name'] = row.get('neighbourhood_name', row['neighbourhood_id'])
      plans.append(plan)
    except json.JSONDecodeError:
      pass

if not plans:
  st.warning("No valid communication plans found.")
  st.stop()

# Filter by Priority
priorities = ["ALL", "HIGH", "MODERATE", "LOW"]
selected_priority = st.radio("Filter by Priority:", priorities, horizontal=True)

filtered_plans = plans
if selected_priority != "ALL":
  filtered_plans = [p for p in plans if p.get('communication_priority') == selected_priority]

st.markdown(f"**Showing {len(filtered_plans)} communication plans.**")

# Search
search_term = st.text_input("Search Neighbourhoods", "", placeholder="Enter name or ID...")
if search_term:
  filtered_plans = [p for p in filtered_plans if search_term.lower() in p['neighbourhood_name'].lower() or search_term.lower() in p['neighbourhood_id'].lower()]

# Render Plans
for plan in filtered_plans:
  pri = plan.get('communication_priority', 'LOW')
  if pri == 'HIGH': tag_class = 'comm-tag-high'
  elif pri == 'MODERATE': tag_class = 'comm-tag-mod'
  else: tag_class = 'comm-tag-low'
  
  st.markdown(f"""
  <div class="comm-card">
    <div class="comm-title">{plan['neighbourhood_name']} ({plan['neighbourhood_id']})</div>
    <div style="margin-bottom: 10px;">
      <span class="{tag_class}">Priority: {pri}</span>
      <span class="{tag_class}">Risk: {plan.get('risk_level', 'UNKNOWN')}</span>
      <span class="{tag_class}">Urgency: {plan.get('urgency', 'Standard')}</span>
    </div>
    <div class="msg-box">"{plan.get('suggested_message', 'No message generated.')}"</div>
    <div class="comm-grid">
      <div><span>Target Audience</span>{plan.get('target_audience', 'General')}</div>
      <div><span>Recommended Channels</span>{plan.get('communication_channel', 'Standard Broadcast')}</div>
      <div><span>Recommended Timing</span>{plan.get('recommended_timing', 'Routine')}</div>
      <div><span>Outreach Connection</span>{plan.get('outreach_connection', 'None')}</div>
    </div>
  </div>
  """, unsafe_allow_html=True)

st.markdown("---")
st.caption("Note: Generated messages are automated public health advisories based on environmental indicators and demographic data. They are not medically validated diagnostic alerts.")
