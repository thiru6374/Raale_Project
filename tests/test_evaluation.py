import pytest
from src.evaluation.metrics import calculate_evaluation_metrics
from src.evaluation.experiment_runner import ExperimentRunner
from src.evaluation.stakeholder_validation import StakeholderFeedbackManager
import pandas as pd
import os

def test_calculate_evaluation_metrics_empty():
    metrics = calculate_evaluation_metrics(pd.DataFrame())
    assert metrics["total_analyzed"] == 0

def test_experiment_runner():
    runner = ExperimentRunner(num_records=10)
    results = runner.run_comparison()
    
    assert results["status"] == "SUCCESS"
    assert "coverage_focused" in results
    assert "fairness_aware" in results
    
    cov = results["coverage_focused"]["metrics"]
    fair = results["fairness_aware"]["metrics"]
    
    assert cov["total_analyzed"] > 0
    assert fair["total_analyzed"] == cov["total_analyzed"]

def test_stakeholder_feedback_manager(tmp_path):
    # Use tmp_path for isolated testing
    manager = StakeholderFeedbackManager(feedback_dir=str(tmp_path))
    
    record = {
        "role": "District Planner",
        "prioritization_clarity": 5,
        "recommendation_usefulness": 4
    }
    
    assert manager.save_feedback(record) == True
    
    feedback = manager.get_all_feedback()
    assert len(feedback) == 1
    assert feedback[0]["role"] == "District Planner"
    
    metrics = manager.get_aggregated_metrics()
    assert metrics["total_responses"] == 1
    assert metrics["avg_prioritization_clarity"] == 5.0
