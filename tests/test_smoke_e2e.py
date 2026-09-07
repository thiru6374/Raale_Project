"""
tests/test_smoke_e2e.py

End-to-End smoke test executing the full flow from Data to Executive Dashboard.
"""
import pytest
from src.services.pipeline_service import PipelineService
from src.simulation.scenario_runner import run_scenario
from src.config.settings import settings

def test_full_pipeline_smoke():
    """Smoke test to ensure the full Phase 1-7 pipeline runs without crashing."""
    result = PipelineService.run_full_pipeline(num_records=50)
    
    assert result["status"] == "SUCCESS", f"Pipeline failed: {result.get('errors')}"
    assert result["pipeline_results"] is not None
    assert "dataset_id" in result
    assert result["pipeline_duration_s"] > 0
    
    df = result["pipeline_results"]
    assert "multi_factor_risk_score" in df.columns
    assert "selected_for_outreach" in df.columns
    assert "fallback_status" in df.columns
