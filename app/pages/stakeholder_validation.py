"""
app/pages/stakeholder_validation.py – & 10 Stakeholder Validation UI.
Enhanced with structured feedback (Usefulness/Clarity/Feasibility ratings)
and Feedback Analytics (Acceptance rate, Bias analysis).
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
import pandas as pd

from src.services.app_state import AppState
from src.evaluation.stakeholder_validation import StakeholderFeedbackManager
from src.services.persistence.feedback_repository import FeedbackRepository
from src.intelligence.feedback_analyzer import FeedbackAnalyzer

page_header(" Stakeholder Validation & Feedback", subtitle=None, icon=":material/groups:")
st.markdown("Provide feedback on recommendations, alerts, and system explanations.")

apply_global_styles()
render_sidebar()

AppState.initialize_application()

phase5_manager = StakeholderFeedbackManager()
phase10_repo  = FeedbackRepository()
analyzer    = FeedbackAnalyzer()

# ── CLASSIC FEEDBACK ────────────────────────────────────────────────
with st.expander(" — Classic Stakeholder Validation", expanded=True):
  st.subheader("Submit Classic Validation Feedback")

  with st.form("feedback_form_phase5"):
    role = st.selectbox(
      "Your Role",
      ["District Planner", "Field Outreach Coordinator",
       "Public Health Communication Officer", "Other"],
    )
    st.markdown("Rate the following 1 (Strongly Disagree) → 5 (Strongly Agree):")

    clarity  = st.slider("Is the high-risk prioritisation understandable?", 1, 5, 3)
    usefulness = st.slider("Are the recommended actions useful?",       1, 5, 3)
    realism  = st.slider("Are the capacity constraints realistic?",     1, 5, 3)
    fairness  = st.slider("Is the fairness/equity information clear?",    1, 5, 3)
    override  = st.slider("Is the manual override workflow clear?",      1, 5, 3)
    trust   = st.slider("Do you trust the automated recommendations?",   1, 5, 3)
    free_text = st.text_area("Additional Feedback (Optional)")

    if st.form_submit_button("Submit Classic Validation"):
      record = {
        "role": role,
        "prioritization_clarity": clarity,
        "recommendation_usefulness": usefulness,
        "capacity_realism": realism,
        "fairness_understanding": fairness,
        "override_clarity": override,
        "recommendation_trust": trust,
        "free_text": free_text,
      }
      if phase5_manager.save_feedback(record):
        st.success("Feedback submitted. Thank you!")
      else:
        st.error("Failed to save feedback.")

  # aggregate metrics
  st.markdown("---")
  st.subheader("Aggregated Metrics")
  metrics = phase5_manager.get_aggregated_metrics()
  if not metrics or metrics.get("total_responses", 0) == 0:
    st.info("No feedback collected yet.")
  else:
    st.metric("Total Responses", metrics["total_responses"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Clarity",  f"{metrics.get('avg_prioritization_clarity', 0):.1f} / 5")
    c2.metric("Avg Usefulness", f"{metrics.get('avg_recommendation_usefulness', 0):.1f} / 5")
    c3.metric("Avg Trust",   f"{metrics.get('avg_recommendation_trust', 0):.1f} / 5")
    c4, c5, c6 = st.columns(3)
    c4.metric("Avg Realism",      f"{metrics.get('avg_capacity_realism', 0):.1f} / 5")
    c5.metric("Avg Fairness Clarity", f"{metrics.get('avg_fairness_understanding', 0):.1f} / 5")
    c6.metric("Avg Override Clarity", f"{metrics.get('avg_override_clarity', 0):.1f} / 5")

st.markdown("---")

# ── STRUCTURED FEEDBACK ────────────────────────────────────────────
with st.expander(" — Structured Intelligence Feedback", expanded=True):
  st.subheader("Submit Decision Intelligence Feedback")
  st.caption(
    "Use this form to rate specific recommendations or alerts. "
    "This structured data powers the Feedback Analytics dashboard."
  )

  res = AppState.get_full_results()
  run_id = res.get("dataset_id", "UNKNOWN") if res else "UNKNOWN"

  with st.form("feedback_form_phase10"):
    st.write(f"**Pipeline Run ID:** `{run_id}`")

    f_recommendation_id = st.text_input(
      "Recommendation / Alert ID (optional)",
      placeholder="e.g. neighbourhood name or alert_id",
    )

    c_f1, c_f2, c_f3 = st.columns(3)
    f_useful  = c_f1.selectbox("Useful?",  ["Yes", "Partially", "No"], key="f_useful")
    f_clear  = c_f2.selectbox("Clear?",  ["Yes", "Partially", "No"], key="f_clear")
    f_feasible = c_f3.selectbox("Feasible?", ["Yes", "Partially", "No"], key="f_feasible")

    f_comment = st.text_area("Comment (optional)")

    # Group context (for bias analysis)
    st.caption("Group context helps us audit fairness across population types.")
    gc1, gc2 = st.columns(2)
    mobile_group   = gc1.checkbox("Represents mobile / transient population")
    low_service_group = gc2.checkbox("Represents low-service-access population")

    if st.form_submit_button("Submit Intelligence Feedback"):
      feedback_data = {
        "recommendation_id": f_recommendation_id or None,
        "pipeline_run_id":  run_id,
        "usefulness_rating": f_useful,
        "clarity_rating":   f_clear,
        "feasibility_rating": f_feasible,
        "comment":      f_comment,
        "group_context": {
          "group_mobile":      mobile_group,
          "group_low_service_access": low_service_group,
        },
        "submitted_by": "ANONYMOUS_STAKEHOLDER",
      }
      fid = phase10_repo.save_feedback(feedback_data)
      if fid:
        st.success(f"Feedback saved. ID: `{fid}`")
      else:
        st.error("Failed to save feedback.")

st.markdown("---")

# ── FEEDBACK ANALYTICS ─────────────────────────────────────────────
st.subheader(" Feedback Analytics ()")

analysis = analyzer.analyze_feedback()

if analysis.get("status") == "INSUFFICIENT FEEDBACK FOR RELIABLE ANALYSIS":
  st.info(
    "**INSUFFICIENT FEEDBACK FOR RELIABLE ANALYSIS**\n\n"
    f"At least 5 structured feedback records are required. "
    f"Currently: {len(phase10_repo.get_all_feedback())} record(s) on file."
  )
else:
  st.success(f"Analysis based on **{analysis['total_responses']}** feedback responses.")

  ca1, ca2, ca3 = st.columns(3)
  ca1.metric("Recommendation Acceptance", f"{analysis['recommendation_acceptance_rate']:.0%}")
  ca2.metric("Explanation Clarity",    f"{analysis['explanation_clarity_score']:.0%}")
  ca3.metric("Operational Feasibility",  f"{analysis['operational_feasibility_score']:.0%}")

  st.subheader("Feedback Bias Analysis")
  bias = analysis.get("bias_analysis", {})
  if not bias or bias.get("status") == "INSUFFICIENT GROUP DATA":
    st.info("Insufficient group context data for bias analysis.")
  else:
    rows = []
    for grp, result in bias.items():
      if isinstance(result, str):
        rows.append({"Group": grp, "Status": result, "Group Acceptance": "—", "Non-Group Acceptance": "—", "Gap": "—"})
      else:
        rows.append({
          "Group": grp,
          "Status": "OK",
          "Group Acceptance":   f"{result['group_acceptance']:.0%}",
          "Non-Group Acceptance": f"{result['non_group_acceptance']:.0%}",
          "Gap": f"{result['gap']:+.0%}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.caption(
      "A positive gap means the non-group population reports higher acceptance. "
      "This may indicate a fairness concern if sample size is sufficient."
    )
