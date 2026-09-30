import pandas as pd
import pytest
from src.fairness.metrics import calculate_fairness_metrics
from src.fairness.bias_detection import FairnessAuditor

def test_fairness_metrics_basic():
    df = pd.DataFrame({
        "selected_for_outreach": [True, True, False, False],
        "group_mobile": [True, False, True, False],
        "population": [100, 200, 100, 200]
    })
    
    # 2 selected out of 4 -> overall coverage 50%
    # Group mobile: 2 people, 1 selected -> group coverage 50%
    # Non-group: 2 people, 1 selected -> non-group coverage 50%
    # Pop target: 200, Pop reached: 100 -> pop weighted coverage 50%
    
    metrics = calculate_fairness_metrics(df, "group_mobile")
    
    assert metrics["group_name"] == "group_mobile"
    assert metrics["sample_size"] == 2
    assert metrics["target_population"] == 200
    assert metrics["reached_population"] == 100
    assert metrics["group_coverage"] == 0.5
    assert metrics["overall_coverage"] == 0.5
    assert metrics["coverage_gap"] == 0.0
    assert metrics["coverage_ratio"] == 1.0
    assert metrics["opportunity_difference"] == 0.0
    assert metrics["pop_weighted_coverage"] == 0.5

def test_fairness_metrics_disparity():
    df = pd.DataFrame({
        "selected_for_outreach": [True, True, True, False],
        "group_mobile": [False, False, False, True], # Group mobile is entirely skipped
        "population": [100, 100, 100, 100]
    })
    
    # 3 selected out of 4 -> overall coverage 75%
    # Group mobile: 1 person, 0 selected -> group coverage 0%
    # Non-group: 3 people, 3 selected -> non-group coverage 100%
    
    metrics = calculate_fairness_metrics(df, "group_mobile")
    
    assert metrics["group_coverage"] == 0.0
    assert metrics["overall_coverage"] == 0.75
    assert metrics["coverage_gap"] == 0.75
    assert metrics["coverage_ratio"] == 0.0
    assert metrics["opportunity_difference"] == -1.0 # 0.0 - 1.0
    
def test_bias_detection_auditor():
    df = pd.DataFrame({
        "selected_for_outreach": [True, True, True, False],
        "group_mobile": [False, False, False, True], # Mobile is underserved (gap = 0.75)
        "group_low_service_access": [True, True, False, False], # LSA is well served (2/2 vs 3/4)
        "population": [100, 100, 100, 100]
    })
    
    auditor = FairnessAuditor()
    report = auditor.generate_fairness_report(df)
    
    assert len(report) == 2
    
    # Mobile should be missing
    mobile_report = next(r for r in report if r["group_name"] == "group_mobile")
    assert mobile_report["coverage_gap"] == 0.75
    
    # Audit plan should return warnings
    warnings = auditor.audit_plan(df)
    # The default max gap is 0.15 (15%), so 0.75 should trigger a warning
    assert len([w for w in warnings if w.get("group") == "group_mobile"]) > 0
