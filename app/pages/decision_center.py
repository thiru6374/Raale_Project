"""
app/pages/decision_center.py

& 11: Intelligent Decision Center.
Centralized UI for operational alerting, priority decisions,
manual review queues, and improvement proposals.
adds access control to sensitive actions.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from app.components.constraints import render_constraint_status
from app.components.schedule_view import render_schedule_view
import pandas as pd
from src.services.app_state import AppState
from src.services.persistence.alert_repository import AlertRepository
from src.services.persistence.improvement_repository import ImprovementRepository
from src.services.config_version_service import ConfigVersionService
from src.security.security_service import SecurityService
from src.security.access_control import AccessControl
from src.security.permissions import (
  PERM_ACKNOWLEDGE_ALERT, PERM_DISMISS_CRITICAL_ALERT,
  PERM_APPROVE_CONFIG, PERM_REVIEW_PROPOSALS,
)
from src.governance.overrides import OverrideManager
from src.governance.audit_logger import AuditLogger



# Custom CSS for priority styling
st.markdown("""
<style>
  .priority-1 { border-left: 5px solid #FF4B4B; padding: 10px; background-color: rgba(255, 75, 75, 0.1); margin-bottom: 10px; border-radius: 4px; }
  .priority-2 { border-left: 5px solid #FF8C00; padding: 10px; background-color: rgba(255, 140, 0, 0.1); margin-bottom: 10px; border-radius: 4px; }
  .priority-3 { border-left: 5px solid #FFC107; padding: 10px; background-color: rgba(255, 193, 7, 0.1); margin-bottom: 10px; border-radius: 4px; }
  .priority-4 { border-left: 5px solid #2B9BF4; padding: 10px; background-color: rgba(43, 155, 244, 0.1); margin-bottom: 10px; border-radius: 4px; }
  .alert-card { border: 1px solid #444; border-radius: 8px; padding: 15px; margin-bottom: 15px; background-color: #1E1E2E; }
  .proposal-card { border: 1px dashed #00CC96; border-radius: 8px; padding: 15px; margin-bottom: 15px; background-color: #182A2B; }
</style>
""", unsafe_allow_html=True)

page_header(" Intelligent Decision Center", subtitle=None, icon=":material/psychology:")

# Role selector
role = SecurityService.render_role_selector(sidebar=True)
st.sidebar.markdown("---")

apply_global_styles()
render_sidebar()

AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()
  
# Check if Intelligence data exists via the canonical API
res = AppState.get_full_results()
if not res or res.get("status") != "SUCCESS":
  st.info("No decision intelligence available. Please run the pipeline first.")
  st.stop()
  
# Intelligence data may be generated inline from the pipeline results
intel = res.get("intelligence")
df = res.get("pipeline_results", pd.DataFrame())

# Initialize Repositories
alert_repo = AlertRepository()
prop_repo = ImprovementRepository()
config_service = ConfigVersionService()

active_alerts = alert_repo.get_active_alerts()
latest_proposals = prop_repo.get_latest_proposals()

# ── SYSTEM STATUS HEADER ──────────────────────────────────────────────────────
st.subheader("System Status")
col1, col2, col3, col4 = st.columns(4)

cr_count = sum(1 for a in active_alerts if a.get("severity") == "CRITICAL")
wr_count = sum(1 for a in active_alerts if a.get("severity") == "WARNING")

if cr_count > 0:
  status, color = "CRITICAL", "red"
elif wr_count > 0:
  status, color = "WARNING", "orange"
else:
  status, color = "HEALTHY", "green"
  
col1.metric("Overall Intelligence Status", status, delta_color="off" if color != "red" else "inverse")
col2.metric("Critical Alerts", cr_count)
col3.metric("Warning Alerts", wr_count)

pending_proposals = sum(1 for p in latest_proposals.values() if p.get("status") in ["PROPOSED", "UNDER_REVIEW"])
col4.metric("Improvement Proposals", pending_proposals)

st.markdown("---")

# ── CRITICAL ALERTS ───────────────────────────────────────────────────────────
if active_alerts:
  st.subheader(" Active Operational Alerts")
  for a in sorted(active_alerts, key=lambda x: {"CRITICAL": 0, "WARNING": 1, "WATCH": 2, "INFO": 3}.get(x.get("severity", "INFO"), 4)):
    sev = a.get("severity")
    sev_color = {"CRITICAL": "", "WARNING": "", "WATCH": "", "INFO": ""}.get(sev, "")
    
    with st.container():
      st.markdown(f"<div class='alert-card'>", unsafe_allow_html=True)
      c_alert1, c_alert2 = st.columns([3, 1])
      with c_alert1:
        st.markdown(f"**{sev_color} {sev} - {a.get('category')}**")
        st.write(f"**Evidence:** {a.get('evidence')}")
        st.write(f"**Recommended Action:** {a.get('recommended_action')}")
      with c_alert2:
        if st.button("Acknowledge", key=f"ack_{a['alert_id']}"):
          ok, msg = AccessControl.require(role, PERM_ACKNOWLEDGE_ALERT, action="acknowledge_alert", resource=a['alert_id'])
          if ok:
            alert_repo.add_event("ALERT_ACKNOWLEDGED", sev, a.get("category"), a.get("evidence"), a.get("recommended_action"), alert_id=a['alert_id'])
            st.rerun()
          else:
            SecurityService.access_denied_message(msg)
        if st.button("Resolve", key=f"res_{a['alert_id']}"):
          perm = PERM_DISMISS_CRITICAL_ALERT if sev == "CRITICAL" else PERM_ACKNOWLEDGE_ALERT
          ok, msg = AccessControl.require(role, perm, action="resolve_alert", resource=a['alert_id'])
          if ok:
            alert_repo.add_event("ALERT_RESOLVED", sev, a.get("category"), a.get("evidence"), a.get("recommended_action"), alert_id=a['alert_id'])
            AccessControl.log_action("ALERT_RESOLVED", role, "resolve_alert", resource=a['alert_id'])
            st.rerun()
          else:
            SecurityService.access_denied_message(msg)
      st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

render_constraint_status()

render_schedule_view(df, show_map=False)

st.markdown("---")

# ── DECISION QUEUE ────────────────────────────────────────────────────────────
st.subheader(" Prioritized Decision Queue")

if not df.empty and "decision_priority" in df.columns:
  # Filter priorities 1 and 2
  priority_df = df[df["decision_priority"].str.contains("PRIORITY 1|PRIORITY 2")]
  
  if priority_df.empty:
    st.success("No high-priority decisions require attention at this time.")
  else:
    for idx, row in priority_df.iterrows():
      p_class = "priority-1" if "PRIORITY 1" in row["decision_priority"] else "priority-2"
      
      st.markdown(f"<div class='{p_class}'>", unsafe_allow_html=True)
      st.markdown(f"**{row['neighbourhood_name']}** — {row['decision_priority']}")
      st.markdown(f"*Reason:* {row['priority_reason']}")
      st.markdown("</div>", unsafe_allow_html=True)
      
      with st.expander(f"Review Details: {row['neighbourhood_name']}"):
        st.write(f"**Risk Category:** {row['multi_factor_risk_category']}")
        st.write(f"**Confidence Level:** {row.get('confidence_level', 'N/A')}")
        st.write(f"**Confidence Reason:** {row.get('confidence_reason', 'N/A')}")
        st.write(f"**Valid Geo:** {row.get('is_valid_geo', True)}")
        if not row.get("is_valid_geo", True):
          st.error(f"Geographic Validation Status: {row.get('geo_validation_status')}")
        
        # Feedback hook
        st.page_link("pages/stakeholder_validation.py", label=f"Submit Feedback for {row['neighbourhood_name']}")
        
        st.markdown("#### Override Decision")
        with st.form(key=f"override_{row['neighbourhood_id']}"):
          new_dec = st.radio("Force Selection:", options=[True, False], index=0 if row.get("selected_for_outreach") else 1)
          override_reason = st.text_input("Override Reason (Required)")
          override_comment = st.text_input("Additional Comment (Optional)")
          if st.form_submit_button("Submit Override"):
            try:
              mgr = OverrideManager(AuditLogger())
              updated_df = mgr.apply_override(
                df=df,
                neighbourhood_id=row['neighbourhood_id'],
                force_select=new_dec,
                actor=st.session_state.get("user_id", "current_user"),
                role=role,
                reason=override_reason,
                comment=override_comment,
                analysis_id=AppState().get_pipeline_run_id() or "UNKNOWN"
              )
              AppState().set_pipeline_results(updated_df)
              st.success("Override applied securely.")
              st.rerun()
            except Exception as e:
              SecurityService.access_denied_message(str(e))
else:
  st.info("Run pipeline to populate decision queue.")
  
st.markdown("---")

# ── MANUAL REVIEW QUEUE ───────────────────────────────────────────────────────
st.subheader(" Manual Review Required")
if not df.empty and "fallback_status" in df.columns:
  manual_df = df[df["fallback_status"] == "MANUAL_REVIEW"]
  if manual_df.empty:
    st.success("No records require manual review.")
  else:
    st.warning(f"{len(manual_df)} records require manual location or data verification.")
    st.dataframe(manual_df[["neighbourhood_name", "multi_factor_risk_category", "is_valid_geo", "geo_validation_status", "fallback_status"]], use_container_width=True)
else:
  st.info("Run pipeline to populate manual review queue.")

st.markdown("---")

# ── IMPROVEMENT PROPOSALS ─────────────────────────────────────────────────────
st.subheader(" Configuration Improvement Proposals")
if pending_proposals > 0:
  for p_id, p in latest_proposals.items():
    if p.get("status") in ["PROPOSED", "UNDER_REVIEW"]:
      st.markdown("<div class='proposal-card'>", unsafe_allow_html=True)
      st.markdown(f"### {p.get('trigger_pattern')}")
      st.write(f"**Evidence:** {p.get('evidence')}")
      st.write(f"**Expected Benefit:** {p.get('expected_benefit')}")
      st.write(f"**Risk:** {p.get('risk_assessment')}")
      
      st.json(p.get("recommended_change"))
      
      c_p1, c_p2 = st.columns(2)
      with c_p1:
        if st.button(" Approve Proposal", key=f"app_{p_id}"):
          ok_perm, msg_perm = AccessControl.require(
            role, PERM_APPROVE_CONFIG,
            action="approve_improvement_proposal", resource=p_id
          )
          if not ok_perm:
            SecurityService.access_denied_message(msg_perm)
          else:
            version_id = config_service.propose_configuration(
              p.get("recommended_change"),
              reason=p.get('trigger_pattern'),
              actor=role.value
            )
            success = config_service.approve_and_activate(version_id, actor=role.value)
            if success:
              prop_repo.update_proposal_status(p_id, "IMPLEMENTED",
                decision_reason=f"Approved by {role.value}",
                related_config_version=version_id)
              AccessControl.log_action("CONFIGURATION_APPROVED", role,
                "approve_improvement_proposal", resource=p_id, config_version=version_id)
              st.success("Configuration updated successfully.")
              st.rerun()
            else:
              st.error("Validation failed. Configuration rejected.")
      with c_p2:
        if st.button(" Reject Proposal", key=f"rej_{p_id}"):
          ok_perm, msg_perm = AccessControl.require(
            role, PERM_REVIEW_PROPOSALS,
            action="reject_improvement_proposal", resource=p_id
          )
          if not ok_perm:
            SecurityService.access_denied_message(msg_perm)
          else:
            prop_repo.update_proposal_status(p_id, "REJECTED",
              decision_reason=f"Rejected by {role.value}")
            AccessControl.log_action("CONFIGURATION_REJECTED", role,
              "reject_improvement_proposal", resource=p_id)
            st.rerun()
          
      st.markdown("</div>", unsafe_allow_html=True)
else:
  st.info("No pending improvement proposals at this time.")

st.markdown("---")

# ── RECENT CHANGES ────────────────────────────────────────────────────────────
with st.expander(" Recent Pipeline Changes"):
  if intel.get("changes"):
    for c in intel["changes"]:
      st.write(f"- **{c.get('type')}**: {c.get('message')}")
  else:
    st.write("No significant changes detected compared to baseline/history.")
