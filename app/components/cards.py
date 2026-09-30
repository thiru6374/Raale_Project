"""
app/components/cards.py

Reusable UI cards for the application.
"""
import streamlit as st

def metric_card(title: str, value: str, subtext: str = None, trend: str = None, trend_color: str = "normal"):
  """
  Renders a premium metric card using standard Streamlit metrics,
  styled by our layout.py CSS.
  """
  delta = None
  delta_color = "normal"
  
  if trend:
    delta = trend
    delta_color = trend_color
    
  # We can just use the native metric which gets styled by layout.py
  st.metric(label=title, value=value, delta=delta, delta_color=delta_color)

def html_card(title: str, value: str, subtext: str = None, icon: str = ""):
  """Renders a custom HTML metric card matching the design system."""
  subtext_html = f"<div style='font-size: 0.8rem; color: #64748b; margin-top: 5px;'>{subtext}</div>" if subtext else ""
  icon_html = f"<span class='material-symbols-rounded' style='font-size: 1.2rem; margin-right: 8px; color: #64748b;'>{icon}</span>" if icon else ""
  st.markdown(f"""
  <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); height: 100%;">
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
      {icon_html}
      <span style="font-size: 0.9rem; font-weight: 600; color: #64748b;">{title}</span>
    </div>
    <div style="font-size: 2rem; font-weight: 700; color: #0f172a;">{value}</div>
    {subtext_html}
  </div>
  """, unsafe_allow_html=True)
