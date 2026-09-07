"""
tests/test_phase7_intelligence.py

Tests Phase 7 intelligence, explainability, monitoring, and governance features.
"""
import pytest
import pandas as pd
from src.explainability.risk_explainer import explain_risk
from src.explainability.recommendation_explainer import explain_recommendation
from src.explainability.decision_trace import create_decision_trace
from src.monitoring.data_monitor import monitor_data_quality, monitor_data_distribution
from src.monitoring.fairness_monitor import monitor_fairness
from src.governance.improvement_candidates import create_improvement_candidate, get_all_candidates

@pytest.fixture
def sample_pipeline_row():
    return pd.Series({
        "neighbourhood_id": "N-001",
        "temperature_c": 39.5,
        "healthcare_distance_km": 6.0,
        "vulnerability_index": 0.8,
        "built_density": 0.7,
        "baseline_risk_score": 0.9,
        "built_environment_score": 0.7,
        "service_deficit_score": 0.8,
        "multi_factor_risk_category": "HIGH",
        "multi_factor_risk_score": 0.85,
        "selected_for_outreach": True,
        "outreach_priority": "PRIMARY_OUTREACH",
        "fallback_status": "TRUSTED",
        "confidence_score": 1.0,
        "group_mobile": True,
        "group_low_service_access": True,
    })

def test_risk_explainer(sample_pipeline_row):
    exp = explain_risk(sample_pipeline_row)
    assert exp["risk_category"] == "HIGH"
    assert exp["risk_score"] == 0.85
    assert len(exp["top_factors"]) > 0
    assert "narrative" in exp

def test_recommendation_explainer(sample_pipeline_row):
    exp = explain_recommendation(sample_pipeline_row)
    assert exp["is_selected"] is True
    assert exp["priority"] == "PRIMARY_OUTREACH"
    assert "narrative" in exp
    assert "constraints" in exp

def test_decision_trace(sample_pipeline_row):
    trace = create_decision_trace(sample_pipeline_row, dataset_id="TEST-123")
    assert trace["dataset_id"] == "TEST-123"
    assert trace["neighbourhood_id"] == "N-001"
    assert trace["risk_classification"] == "HIGH"
    assert trace["final_selected"] is True
    assert "decision_id" in trace

def test_data_quality_monitor():
    raw_df = pd.DataFrame({
        "temperature_c": [38.0, None, 40.0],
        "healthcare_distance_km": [2.0, 3.0, 4.0]
    })
    proc_df = pd.DataFrame({
        "temperature_c": [38.0, 39.0, 40.0],
        "healthcare_distance_km": [2.0, 3.0, 4.0]
    })
    
    report = monitor_data_quality(raw_df, proc_df)
    assert report["total_records"] == 3
    assert report["valid_records"] == 3
    assert report["field_missing_rates"]["temperature_c"]["missing_count"] == 1
    # 1 missing out of 3 = 33.3%, which is > 10% so overall status shouldn't be PASS if threshold is 10%
    # Data quality score is 100% since all were processed, but missing rate might drop it to WARNING.

def test_fairness_monitor():
    df = pd.DataFrame({
        "neighbourhood_id": ["A", "B", "C", "D"],
        "multi_factor_risk_category": ["HIGH", "HIGH", "LOW", "HIGH"],
        "selected_for_outreach": [True, False, False, True],
        "group_mobile": [True, True, False, False],
        "group_low_service_access": [False, False, True, True]
    })
    report = monitor_fairness(df)
    assert "overall_status" in report
    assert "group_mobile" in report["groups"]
    
    # group_mobile has 2 HIGH, 1 selected -> 50% coverage
    assert report["groups"]["group_mobile"]["coverage_rate_pct"] == 50.0

def test_improvement_candidates(tmp_path, monkeypatch):
    # Patch file path to use tmp_path
    import src.governance.improvement_candidates as ic
    ic.CANDIDATES_FILE = str(tmp_path / "candidates.jsonl")
    ic.CANDIDATES_DIR = str(tmp_path)
    
    cid = ic.create_improvement_candidate(
        source="test",
        problem_description="test problem",
        affected_component="test component",
        proposed_improvement="test improvement",
        expected_benefit="test benefit"
    )
    
    cands = ic.get_all_candidates()
    assert len(cands) == 1
    assert cands[0]["improvement_id"] == cid
    assert cands[0]["status"] == "PROPOSED"
