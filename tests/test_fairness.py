import pandas as pd
from src.fairness.bias_detection import FairnessAuditor
from src.config.settings import settings

def test_fairness_audit_passes():
    # 10 neighbourhoods, 5 selected (50% global coverage)
    # The group has 4 neighbourhoods, 2 selected (50% group coverage)
    # Gap is 0% -> Should pass
    data = pd.DataFrame({
        'selected_for_outreach': [True, True, True, True, True, False, False, False, False, False],
        'group_mobile': [True, True, False, False, False, True, True, False, False, False]
    })
    
    auditor = FairnessAuditor(target_groups=['group_mobile'])
    warnings = auditor.audit_plan(data)
    
    assert len(warnings) == 0

def test_fairness_audit_fails():
    # 10 neighbourhoods, 5 selected (50% global coverage)
    # The group has 4 neighbourhoods, but NONE are selected (0% group coverage)
    # Gap is 50% -> Should fail because default max gap is 10%
    data = pd.DataFrame({
        'selected_for_outreach': [True, True, True, True, True, False, False, False, False, False],
        'group_mobile': [False, False, False, False, False, True, True, True, True, False]
    })
    
    # Ensure settings allow catching this (default is 0.1 / 10%)
    settings.maximum_coverage_gap = 0.1
    
    auditor = FairnessAuditor(target_groups=['group_mobile'])
    warnings = auditor.audit_plan(data)
    
    assert len(warnings) == 1
    assert warnings[0]['group'] == 'group_mobile'
    assert warnings[0]['coverage_gap'] == 0.5
