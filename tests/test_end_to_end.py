import pytest
from src.services.pipeline_service import PipelineService
from src.validation.system_validator import SystemValidator
from src.config.settings import settings

def test_full_pipeline_end_to_end():
    """
    Executes the complete pipeline end-to-end to ensure all components 
    from Phase 2 to Phase 5 operate cohesively.
    """
    # 1. Run Pipeline
    results = PipelineService.run_full_pipeline()
    assert results["status"] == "SUCCESS", f"Pipeline failed: {results.get('errors')}"
    
    # 2. Extract dataframes
    raw_df = results["raw_df"]
    processed_df = results["processed_df"]
    pipeline_df = results["pipeline_results"]
    
    # 3. Assert Data Availability
    assert raw_df is not None and not raw_df.empty, "Phase 2 failed: No raw data."
    assert processed_df is not None and not processed_df.empty, "Phase 3 failed: No processed data."
    assert pipeline_df is not None and not pipeline_df.empty, "Phase 4 failed: No output data."
    
    # 4. Assert Risk & Optimization Columns Exist
    expected_columns = [
        "multi_factor_risk_score",
        "multi_factor_risk_category",
        "confidence_score",
        "selected_for_outreach",
        "fallback_status"
    ]
    for col in expected_columns:
        assert col in pipeline_df.columns, f"Missing critical column: {col}"

    # 5. Assert Baseline Results Exist (baseline_selected lives in the baseline_results object)
    baseline = results["baseline_results"]
    assert baseline is not None, "Phase 4 failed: No baseline results."
    assert baseline.status in ["COMPLETED", "COMPLETED_WITH_WARNING"], f"Baseline failed: {baseline.status}"
    assert len(baseline.records) > 0, "Baseline produced no records."

    # 6. Assert Constraints (Capacity)
    max_capacity = settings.number_of_teams * settings.maximum_visits_per_team
    selected_count = pipeline_df["selected_for_outreach"].sum()
    assert selected_count <= max_capacity, "Phase 4 failed: Capacity constraints violated."
    
    # 6. Assert System Validator 
    validator = SystemValidator(results)
    health = validator.validate()
    
    # We expect overall status to be HEALTHY or ATTENTION REQUIRED (due to capacity/fairness) 
    # but NOT FAILED.
    assert health["overall_status"] != "FAILED", f"System validator reported failure: {health.get('critical_errors')}"
    assert health["phase_1"] == "PASS"
    assert health["phase_2"] == "PASS"
    # Phase 3 may be WARNING when minor preprocessing issues (e.g. 5% missing values) exist.
    assert health["phase_3"] in ["PASS", "WARNING"]
    assert health["phase_4"] == "PASS"
    # Phase 5 might be warning if no feedback or experiments, but shouldn't be FAILED
    assert health["phase_5"] in ["PASS", "WARNING"]
