"""
app/pages/evidence_report.py  –  Evidence Report UI.
"""
import os
import glob
import json
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar

from src.services.app_state import AppState

page_header(" Evidence Report", subtitle=None, icon=":material/article:")
st.markdown("Defensible summaries of completed experiments and system validations.")

apply_global_styles()
render_sidebar()

AppState.initialize_application()

evidence_dir = "data/experiments"
if not os.path.exists(evidence_dir):
    st.info("No evidence reports found. Please run an experiment from the Experiment & Evaluation page first.")
    st.stop()
    
reports = glob.glob(os.path.join(evidence_dir, "*.json"))

if not reports:
    st.info("No evidence reports found. Please run an experiment from the Experiment & Evaluation page first.")
    st.stop()
    
# Sort by modified time descending
reports.sort(key=os.path.getmtime, reverse=True)

selected_report = st.selectbox("Select Evidence Report", reports, format_func=os.path.basename)

if selected_report:
    try:
        with open(selected_report, "r") as f:
            report_data = json.load(f)
            
        st.subheader("SYSTEM PERFORMANCE SUMMARY")
        st.write(f"**Experiment ID:** {report_data.get('experiment_id')}")
        st.write(f"**Timestamp:** {report_data.get('timestamp')}")
        st.write(f"**Status:** {report_data.get('status')}")
        
        st.markdown("---")
        
        c1, c2, c3 = st.columns(3)
        base = report_data.get('baseline_performance', {})
        cov = report_data.get('optimized_coverage_focused', {})
        
        c1.metric("Baseline Coverage", f"{base.get('high_risk_coverage_pct', 0):.1f}%")
        c2.metric("Optimized Coverage", f"{cov.get('high_risk_coverage_pct', 0):.1f}%")
        c3.metric("Improvement", f"{cov.get('improvement_over_baseline_pct', 0):.1f}%")
        
        st.markdown("---")
        
        # We can analyze the fairness and capacity status
        fair_metrics = cov.get("fairness_metrics", {})
        fairness_status = "PASS"
        for g, m in fair_metrics.items():
            if m.get("high_risk_coverage_pct", 100) < 50.0:
                fairness_status = "WARNING"
                
        capacity_pct = cov.get('capacity_utilization_pct', 0)
        capacity_status = "Constrained" if capacity_pct >= 95.0 else "Within Limit"
        
        c4, c5 = st.columns(2)
        c4.write(f"**Fairness Status:** {fairness_status}")
        c5.write(f"**Capacity Status:** {capacity_status}")
        
        st.markdown("---")
        with st.expander("Raw Evidence Data JSON"):
            st.json(report_data)
            
    except Exception as e:
        st.error(f"Failed to load evidence report: {e}")
