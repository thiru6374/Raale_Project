"""
app/pages/experiment_evaluation.py  –  Experiment & Evaluation UI.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import pandas as pd
import plotly.express as px

from src.services.app_state import AppState
from src.evaluation.experiment_runner import ExperimentRunner

page_header(" Experiment & Evaluation", subtitle=None, icon=":material/biotech:")
st.markdown("Compare the operational outcomes between the Baseline strategy and multiple Optimization strategies.")

# We don't just rely on the main AppState pipeline here, because this page RUNS experiments.
# But we should still initialize it to keep the sidebar happy.
apply_global_styles()
render_sidebar()

AppState.initialize_application()

if st.button("Run Strategy Comparison Experiment", type="primary"):
    with st.spinner("Running Experiment (Baseline vs Coverage-Focused vs Fairness-Aware)..."):
        runner = ExperimentRunner(num_records=100)
        results = runner.run_comparison()
        
    if results["status"] == "FAILED":
        st.error("Experiment failed.")
        st.stop()
        
    st.session_state["experiment_results"] = results
    st.success("Experiment completed successfully!")

if "experiment_results" not in st.session_state:
    st.info("Click the button above to run the experiment.")
    st.stop()
    
exp = st.session_state["experiment_results"]
cov_metrics = exp["coverage_focused"]["metrics"]
fair_metrics = exp["fairness_aware"]["metrics"]
base = cov_metrics.get("baseline_comparison", {})

# ── High-Level Summary ────────────────────────────────────────────────────────
st.subheader("High-Risk Coverage Comparison")

c1, c2, c3 = st.columns(3)
c1.metric("Baseline Strategy", f"{base.get('baseline_high_risk_coverage_pct', 0):.1f}%")
c2.metric("Coverage-Focused (Optimized)", f"{cov_metrics['high_risk_coverage_pct']:.1f}%", 
          delta=f"{base.get('coverage_improvement_pct', 0):.1f}% improvement")
c3.metric("Fairness-Aware (Optimized)", f"{fair_metrics['high_risk_coverage_pct']:.1f}%",
          delta=f"{fair_metrics['high_risk_coverage_pct'] - base.get('baseline_high_risk_coverage_pct', 0):.1f}% improvement")

st.markdown("---")
st.subheader("Fairness Trade-offs")
st.markdown("Observe how shifting the optimization objective affects different groups.")

def plot_fairness(metrics_dict, title):
    records = []
    for g, m in metrics_dict["fairness"].items():
        records.append({
            "Group": g,
            "Selection Rate (%)": m["selection_rate_pct"],
            "High-Risk Coverage (%)": m["high_risk_coverage_pct"]
        })
    df = pd.DataFrame(records)
    fig = px.bar(df, x="Group", y=["Selection Rate (%)", "High-Risk Coverage (%)"], 
                 barmode='group', title=title, template="plotly_dark")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(plot_fairness(cov_metrics, "Coverage-Focused"), use_container_width=True)
with col2:
    st.plotly_chart(plot_fairness(fair_metrics, "Fairness-Aware"), use_container_width=True)
