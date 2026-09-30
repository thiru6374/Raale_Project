import streamlit as st
import pandas as pd
from src.services.app_state import AppState

def render_constraint_status():
  """Renders the Operational Constraint Status table if available in AppState."""
  df = AppState.get_pipeline_results()
  if df is None or df.empty:
    return
    
  from src.optimisation.constraint_engine import ConstraintEngine
  ce = ConstraintEngine()
  ce_result = ce.evaluate(df, "selected_for_outreach")
  
  metrics = {
    "constraint_table": ce_result["table"],
    "is_feasible": ce_result["is_feasible"],
    "infeasibility_reasons": ce_result["reasons"]
  }
    
  table_data = metrics.get("constraint_table")
  if not table_data:
    return
    
  is_feasible = metrics.get("is_feasible", True)
  
  st.markdown("###  Operational Constraint Status")
  if is_feasible:
    st.success("Plan is operationally feasible.")
  else:
    st.error("Plan is NOT operationally feasible.")
    for reason in metrics.get("infeasibility_reasons", []):
      st.write(f"- {reason}")
      
  df = pd.DataFrame(table_data)
  
  def _highlight_status(val):
    if val == "FAIL":
      return "color: #ef4444; font-weight: bold"
    if val == "PASS":
      return "color: #22c55e; font-weight: bold"
    return ""
    
  st.dataframe(
    df.style.map(_highlight_status, subset=["Status"]),
    use_container_width=True,
    hide_index=True
  )
