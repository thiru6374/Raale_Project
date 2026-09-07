"""
app/pages/failure_analysis.py  –  Failure Analysis UI.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar

from src.services.app_state import AppState
from src.evaluation.failure_analysis import FailureAnalyzer

page_header(" Failure Analysis", subtitle=None, icon=":material/troubleshoot:")
st.markdown("Simulate realistic edge cases and evaluate the system's robustness and fallback mechanisms.")

apply_global_styles()
render_sidebar()

AppState.initialize_application()

scenario = st.selectbox(
    "Select Failure Scenario",
    ["MISSING_TEMP", "MISSING_COORDS", "LOW_CAPACITY", "UNTRUSTED_DATA", "FAIRNESS_IMBALANCE"]
)

if st.button("Run Simulation", type="primary"):
    with st.spinner(f"Simulating {scenario}..."):
        analyzer = FailureAnalyzer(num_records=50)
        result = analyzer.run_scenario(scenario)
        
    if result["status"] == "FAILED":
        st.error(f"Simulation failed with errors: {result['errors']}")
        st.stop()
        
    metrics = result["metrics"]
    
    st.success(f"Simulation {scenario} completed.")
    
    st.subheader("Simulation Results")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Fallback Count", metrics.get("fallback_count", 0))
    c2.metric("High-Risk Coverage (%)", f"{metrics.get('high_risk_coverage_pct', 0):.1f}%")
    c3.metric("Capacity Utilization (%)", f"{metrics.get('capacity_utilization_pct', 0):.1f}%")
    
    if scenario == "FAIRNESS_IMBALANCE":
        if result.get("fairness_warnings"):
            st.warning("Fairness Analysis correctly detected an imbalance:")
            for w in result["fairness_warnings"]:
                st.write(f"- {w['message']}")
        else:
            st.info("No fairness imbalance detected in this simulation run.")
            
    st.markdown("---")
    st.dataframe(result["results"], use_container_width=True)
