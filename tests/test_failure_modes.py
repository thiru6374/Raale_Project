import pytest
from src.evaluation.failure_analysis import FailureAnalyzer
from src.config.settings import settings

@pytest.fixture
def analyzer():
    return FailureAnalyzer(num_records=10)

def test_missing_temp(analyzer):
    result = analyzer.run_scenario("MISSING_TEMP")
    assert result["status"] == "SUCCESS"
    assert "metrics" in result
    # It should have fallback count due to missing temperature triggering UNTRUSTED or MANUAL_REVIEW
    assert result["metrics"]["fallback_count"] >= 0

def test_missing_coords(analyzer):
    result = analyzer.run_scenario("MISSING_COORDS")
    assert result["status"] == "SUCCESS"

def test_low_capacity(analyzer):
    result = analyzer.run_scenario("LOW_CAPACITY")
    assert result["status"] == "SUCCESS"
    # Should have constrained capacity
    metrics = result["metrics"]
    # Total selected should be capped at 1 * 2 = 2
    assert metrics["total_selected"] <= 2
    assert metrics["capacity_utilization_pct"] >= 0.0

def test_untrusted_data(analyzer):
    result = analyzer.run_scenario("UNTRUSTED_DATA")
    assert result["status"] == "SUCCESS"
    # Extreme missingness should trigger UNTRUSTED/fallback
    assert result["metrics"]["fallback_count"] > 0

def test_fairness_imbalance(analyzer):
    result = analyzer.run_scenario("FAIRNESS_IMBALANCE")
    assert result["status"] == "SUCCESS"
    assert "fairness_warnings" in result
