"""
app/pages/release_readiness.py - Release Readiness UI.

Provides an operational check to ensure the environment, pipeline,
storage, and configurations are ready for a demonstration or release.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar

from src.services.app_state import AppState
from src.release.readiness_checker import ReleaseReadinessChecker



page_header(" Release Readiness", subtitle=None, icon=":material/rocket_launch:")
st.markdown(
  "Automated pre-flight checks to ensure the application is configured safely, "
  "storage is writable, and dependencies are intact before demonstration."
)

apply_global_styles()
render_sidebar()

AppState.initialize_application()
if AppState.display_error_fallback():
  st.stop()

if st.button(" Run Readiness Checks", type="primary"):
  with st.spinner("Running system checks..."):
    checker = ReleaseReadinessChecker()
    report = checker.run_all_checks()
    
  status = report["Overall"]
  
  if status == "READY FOR DEMONSTRATION":
    st.success(f"### {status}")
  elif status == "READY WITH WARNINGS":
    st.warning(f"### {status}")
  else:
    st.error(f"### {status}")
    
  st.markdown("---")
  
  col1, col2 = st.columns(2)
  
  # ── Check Results ─────────────────────────────────────────────────────────
  with col1:
    st.subheader("System Checks")
    
    checks = ["Environment", "Dependencies", "Configuration", 
         "Pipeline", "Application Imports", "Storage", "Testing"]
         
    for c in checks:
      val = report.get(c, "PENDING")
      if val == "PASS":
        icon = ""
      elif "WARNING" in val:
        icon = ""
      elif val == "FRAMEWORK NOT CONFIGURED" or val == "NO TESTS FOUND":
        icon = ""
      else:
        icon = ""
        
      st.markdown(f"**{c}:** {icon} {val}")
      
  # ── Warnings & Errors ─────────────────────────────────────────────────────
  with col2:
    st.subheader("Diagnostics")
    
    if not report["Critical_Errors"] and not report["Warnings"]:
      st.info("No issues detected.")
      
    if report["Critical_Errors"]:
      st.error("**Critical Errors:**")
      for e in report["Critical_Errors"]:
        st.write(f"- {e}")
        
    if report["Warnings"]:
      st.warning("**Warnings:**")
      for w in report["Warnings"]:
        st.write(f"- {w}")

  st.markdown("---")
  st.caption(
    "Note: Future production enhancements could integrate these checks with "
    "enterprise CI/CD tools (e.g., GitHub Actions, Azure DevOps). This check "
    "is a local prototype verification."
  )
else:
  st.info("Click 'Run Readiness Checks' to begin.")
