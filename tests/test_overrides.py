import os
import pandas as pd
import pytest
from src.governance.audit_logger import AuditLogger
from src.governance.overrides import OverrideManager

def test_human_override_and_audit(tmp_path):
    # Use tmp_path fixture to avoid cluttering real logs during tests
    log_file = tmp_path / "test_audit.jsonl"
    logger = AuditLogger(log_path=str(log_file))
    manager = OverrideManager(audit_logger=logger)
    
    # Original data
    data = pd.DataFrame({
        'neighbourhood_id': ['N1', 'N2'],
        'selected_for_outreach': [False, True],
        'outreach_priority': ['NO_ACTION', 'PRIMARY_OUTREACH']
    })
    
    # Force N1 to be selected
    result = manager.force_selection(
        df=data,
        neighbourhood_id='N1',
        force_select=True,
        user_id='admin_jane',
        reason='Local clinic lost power, need immediate dispatch.'
    )
    
    # Verify DataFrame changes
    assert result.loc[result['neighbourhood_id'] == 'N1', 'selected_for_outreach'].iloc[0] == True
    assert result.loc[result['neighbourhood_id'] == 'N1', 'override_status'].iloc[0] == 'MANUAL_OVERRIDE'
    assert result.loc[result['neighbourhood_id'] == 'N1', 'outreach_priority'].iloc[0] == 'HUMAN_MANDATED'
    
    # Verify N2 was untouched
    assert result.loc[result['neighbourhood_id'] == 'N2', 'selected_for_outreach'].iloc[0] == True
    
    # Verify Audit Log was written securely
    logs = logger.read_logs()
    assert len(logs) == 1
    assert logs[0]['user_id'] == 'admin_jane'
    assert logs[0]['neighbourhood_id'] == 'N1'
    assert logs[0]['original_decision'] == False
    assert logs[0]['new_decision'] == True
    assert 'Local clinic lost power' in logs[0]['reason']

def test_override_missing_neighbourhood(tmp_path):
    log_file = tmp_path / "test_audit.jsonl"
    logger = AuditLogger(log_path=str(log_file))
    manager = OverrideManager(audit_logger=logger)
    
    data = pd.DataFrame({'neighbourhood_id': ['N1'], 'selected_for_outreach': [False]})
    
    with pytest.raises(ValueError):
        manager.force_selection(data, 'UNKNOWN_ID', True, 'admin', 'test')
