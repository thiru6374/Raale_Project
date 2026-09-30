"""
app/components/sidebar.py

Professional sidebar navigation elements.
"""
import streamlit as st
from src.services.app_state import AppState
from src.config.settings import settings

def render_confidence_card():
  """Renders the system confidence card in the sidebar."""
  # ── Brand ────────────────────────────────────────────────────────────
  st.markdown(
    "<div style='padding: 8px 0 20px 0;'>"
    "<div style='font-size:1.05rem;font-weight:700;color:#f1f5f9;letter-spacing:-0.01em;'>"
    "Heat-Risk Planner</div>"
    "<div style='font-size:0.72rem;color:#64748b;margin-top:2px;'>Decision Support System</div>"
    "</div>",
    unsafe_allow_html=True
  )

  # ── System Confidence Card ────────────────────────────────────────────
  st.markdown("<div style='margin-top:24px;border-top:1px solid #1e293b;padding-top:16px;'>", unsafe_allow_html=True)

  try:
    pipeline_df = AppState.get_pipeline_results()
    ds_info = AppState.get_active_dataset_info()

    if pipeline_df is not None and not pipeline_df.empty:
      conf = float(pipeline_df["confidence_score"].mean()) if "confidence_score" in pipeline_df.columns else None
      conf_label = "High Confidence" if (conf or 0) >= 0.85 else ("Moderate" if (conf or 0) >= 0.6 else "Low Confidence")
      conf_color = "#10b981" if (conf or 0) >= 0.85 else ("#f59e0b" if (conf or 0) >= 0.6 else "#ef4444")
      conf_str = f"{conf:.2f}" if conf is not None else "N/A"

      # Data quality from pipeline
      dq_ok = True
      dq_msg = "Good"
      dq_color = "#10b981"
      if pipeline_df is not None and "confidence_score" in pipeline_df.columns:
        low_conf_pct = (pipeline_df["confidence_score"] < 0.6).mean()
        if low_conf_pct > 0.2:
          dq_ok = False
          dq_msg = "Review Required"
          dq_color = "#f59e0b"

      st.markdown(f"""
      <div style='background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:14px 16px;'>
       <div style='font-size:0.72rem;font-weight:700;color:#475569;text-transform:uppercase;
          letter-spacing:0.06em;margin-bottom:10px;'>System Confidence</div>
       <div style='font-size:2rem;font-weight:700;color:{conf_color};'>{conf_str}</div>
       <div style='font-size:0.8rem;font-weight:600;color:{conf_color};margin-bottom:10px;'>{conf_label}</div>
       <div style='font-size:0.72rem;color:#64748b;margin-bottom:4px;'>
        <span style='color:{dq_color};font-weight:600;'>● </span>Data Quality: {dq_msg}
       </div>
       <div style='font-size:0.72rem;color:#64748b;'>
        <span style='color:#3b82f6;font-weight:600;'>● </span>Dataset: {ds_info.get('name', 'N/A')}
       </div>
      </div>
      """, unsafe_allow_html=True)
  except Exception as e:
    import logging
    logging.getLogger(__name__).error("Failed to render confidence card: %s", e)

  st.markdown("</div>", unsafe_allow_html=True)

def render_sidebar():
    """Legacy wrapper to maintain compatibility while migrating to st.navigation."""
    pass
