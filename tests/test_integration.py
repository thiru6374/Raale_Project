import pytest
import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock
from src.services.pipeline_service import PipelineService
from src.services.app_state import AppState
from src.governance.audit_logger import AuditLogger
from src.governance.overrides import OverrideManager

def test_imports_from_root():
    """
    Verify that all core src modules import cleanly from the project root
    without any ModuleNotFoundError.
    Streamlit page scripts (app/pages/*) are not imported here because they
    call st.title() and similar at module-level; they require the Streamlit
    runtime and are verified via the live application instead.
    """
    from src.services.pipeline_service import PipelineService   # noqa: F401
    from src.services.app_state import AppState                  # noqa: F401
    from src.data.ingestion import load_synthetic_data           # noqa: F401
    from src.data.preprocessing import DataPreprocessor          # noqa: F401
    from src.features.engineering import FeatureEngineer         # noqa: F401
    from src.risk.risk_engine import MultiFactorRiskModel        # noqa: F401
    from src.risk.confidence import ConfidenceEvaluator          # noqa: F401
    from src.risk.baseline import BaselinePrioritisationModel    # noqa: F401
    from src.optimisation.planner import OutreachPlanner         # noqa: F401
    from src.fairness.bias_detection import FairnessAuditor      # noqa: F401
    from src.communication.message_generator import MessageGenerator  # noqa: F401
    from src.governance.audit_logger import AuditLogger          # noqa: F401
    from src.governance.overrides import OverrideManager         # noqa: F401
    from src.config.settings import settings                     # noqa: F401
    assert True  # All imports above passed without ModuleNotFoundError

def test_pipeline_execution():
    """Verify the full pipeline runs successfully and returns expected structure."""
    result = PipelineService.run_full_pipeline(num_records=50, missing_rate=0.0)
    assert result["status"] == "SUCCESS"
    assert result["raw_df"] is not None
    assert result["pipeline_results"] is not None
    assert len(result["pipeline_results"]) == 50

def test_missing_temperature_fallback():
    """Verify missing temperature doesn't crash the pipeline."""
    # Force high missing rate to ensure some temperatures are missing
    result = PipelineService.run_full_pipeline(num_records=50, missing_rate=0.5)
    assert result["status"] == "SUCCESS"
    # Even with missing temps, we expect a fallback or safe handling
    df = result["pipeline_results"]
    assert 'fallback_status' in df.columns

def test_fairness_groups():
    """Verify at least two population groups are tested for fairness."""
    result = PipelineService.run_full_pipeline(num_records=50, missing_rate=0.0)
    warnings = result["fairness_warnings"]
    assert isinstance(warnings, list)
    # The groups should exist in the dataframe
    df = result["pipeline_results"]
    assert 'group_mobile' in df.columns
    assert 'group_low_service_access' in df.columns

def test_override_recording(tmp_path):
    """Verify manual override is recorded."""
    log_file = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path=str(log_file))
    manager = OverrideManager(audit_logger=logger)
    
    # Create mock dataframe
    df = pd.DataFrame({
        'neighbourhood_id': ['N001', 'N002'],
        'selected_for_outreach': [False, True],
        'outreach_priority': ['NO_ACTION', 'PRIMARY_OUTREACH']
    })
    
    updated = manager.apply_override(
        df=df,
        neighbourhood_id='N001',
        force_select=True,
        actor='admin',
        role='ADMIN',
        reason='test override reason',
        comment=''
    )
    
    assert updated.loc[updated['neighbourhood_id'] == 'N001', 'selected_for_outreach'].iloc[0] == True
    assert updated.loc[updated['neighbourhood_id'] == 'N001', 'outreach_priority'].iloc[0] == 'HUMAN_MANDATED'
    assert os.path.exists(str(log_file))

def test_app_state_caching():
    """Verify app_state does not re-run pipeline if data exists, but refresh works."""
    with patch('src.services.pipeline_service.PipelineService.run_full_pipeline') as mock_run:
        mock_run.return_value = {
            "status": "SUCCESS",
            "raw_df": "mock",
            "processed_df": "mock",
            "pipeline_results": "mock",
            "fairness_warnings": [],
            "baseline_results": "mock",
            "errors": []
        }
        
        # Initial run
        import streamlit as st
        if 'pipeline_results' in st.session_state:
            del st.session_state['pipeline_results']
            
        AppState.initialize_application()
        assert mock_run.call_count == 1
        
        # Second run should skip
        AppState.initialize_application()
        assert mock_run.call_count == 1
        
        # Refresh run should trigger
        AppState.initialize_application(force_refresh=True)
        assert mock_run.call_count == 2
