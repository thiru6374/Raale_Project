"""
src/simulation/scenario_runner.py

Executes a configured scenario, temporarily patching settings and input data,
running the pipeline, and persisting the results safely to disk.
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd
from pydantic_core import ValidationError

from src.config.settings import settings
from src.services.pipeline_service import PipelineService
from src.simulation.scenario_definitions import get_scenario_definition
from src.utils.logger import get_logger

logger = get_logger("scenario_runner")

SCENARIO_DATA_DIR = "data/scenarios"
SCENARIO_LATEST_DIR = os.path.join(SCENARIO_DATA_DIR, "latest")
SCENARIO_RUNS_DIR = os.path.join(SCENARIO_DATA_DIR, "scenario_runs")

def _ensure_directories():
    os.makedirs(SCENARIO_LATEST_DIR, exist_ok=True)
    os.makedirs(SCENARIO_RUNS_DIR, exist_ok=True)

def _build_modifier_fn(input_changes: dict):
    """Returns a function that mutates the raw dataframe based on scenario config."""
    def modifier(df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()
        
        # Scenario: Extreme Heat
        if "temperature_boost" in input_changes:
            boost = input_changes["temperature_boost"]
            if "temperature_c" in df_copy.columns:
                df_copy["temperature_c"] += boost
        
        # Scenario: Fairness Stress Test
        if "concentrate_risk_in_group" in input_changes:
            target_group = input_changes["concentrate_risk_in_group"]
            if target_group in df_copy.columns and "temperature_c" in df_copy.columns:
                # Force high temperatures for members of this group
                mask = df_copy[target_group] == True
                df_copy.loc[mask, "temperature_c"] = 42.0
                df_copy.loc[mask, "healthcare_distance_km"] = 10.0
                
        # Scenario: Pipeline Failure
        if "trigger_crash_at" in input_changes:
            # We can trigger a hard failure by raising an exception in the modifier
            if input_changes["trigger_crash_at"] == "preprocessing":
                raise RuntimeError("Simulated pipeline failure during preprocessing.")
        
        # Scenario: Safe Fallback Activation
        if input_changes.get("force_untrusted"):
            # Set missing values in critical fields to force confidence score to 0
            if "built_density" in df_copy.columns:
                df_copy["built_density"] = None
            if "vulnerability_index" in df_copy.columns:
                df_copy["vulnerability_index"] = None
                
        return df_copy
    return modifier

def _extract_metrics(pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts summary metrics from a pipeline result."""
    df = pipeline_result.get("pipeline_results")
    if df is None or df.empty:
        return {}

    high_risk = df[df["multi_factor_risk_category"].isin(["EXTREME", "HIGH"])]
    high_risk_count = len(high_risk)
    selected_count = high_risk["selected_for_outreach"].sum()
    coverage_pct = (selected_count / high_risk_count * 100) if high_risk_count > 0 else 0.0
    
    fallback_count = (df["fallback_status"] == "MANUAL_REVIEW").sum()
    untrusted_count = (df["fallback_status"] == "UNTRUSTED").sum()
    
    # Calculate fairness for mobile vs low_service
    groups = ["group_mobile", "group_low_service_access"]
    fairness = {}
    coverage_rates = []
    for g in groups:
        if g in df.columns:
            g_mask = df[g] == True
            g_hr = df[g_mask & df["multi_factor_risk_category"].isin(["EXTREME", "HIGH"])]
            g_hr_count = len(g_hr)
            g_reached = g_hr["selected_for_outreach"].sum()
            rate = (g_reached / g_hr_count * 100) if g_hr_count > 0 else 0.0
            fairness[g] = rate
            coverage_rates.append(rate)
            
    max_gap = (max(coverage_rates) - min(coverage_rates)) if len(coverage_rates) >= 2 else 0.0
    
    return {
        "total_records": len(df),
        "high_risk_count": int(high_risk_count),
        "selected_for_outreach": int(selected_count),
        "coverage_pct": round(coverage_pct, 2),
        "fallback_active_count": int(fallback_count),
        "untrusted_count": int(untrusted_count),
        "fairness_coverage_rates": fairness,
        "max_coverage_gap_pct": round(max_gap, 2)
    }

def run_scenario(scenario_id: str) -> Dict[str, Any]:
    """Runs a scenario and persists the result."""
    _ensure_directories()
    
    config = get_scenario_definition(scenario_id)
    logger.info(f"Starting Scenario Run: {config['name']}")
    
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # 1. Patch Settings
    original_teams = settings.number_of_teams
    original_visits = settings.maximum_visits_per_team
    
    cap_cfg = config.get("capacity_settings", {})
    settings.number_of_teams = cap_cfg.get("number_of_teams", original_teams)
    settings.maximum_visits_per_team = cap_cfg.get("maximum_visits_per_team", original_visits)
    
    # 2. Setup Run Parameters
    missing_rate = config.get("data_quality_conditions", {}).get("missing_rate", 0.05)
    strategy = config.get("strategy", "COVERAGE_FOCUSED")
    modifier_fn = _build_modifier_fn(config.get("input_changes", {}))
    
    # 3. Run Pipeline
    try:
        result = PipelineService.run_full_pipeline(
            num_records=100, 
            missing_rate=missing_rate, 
            strategy=strategy,
            scenario_modifier_fn=modifier_fn
        )
    except Exception as e:
        logger.error(f"Scenario pipeline crashed: {e}")
        result = {
            "status": "FAILED",
            "errors": [str(e)],
            "pipeline_results": None,
            "dataset_id": "N/A",
            "pipeline_duration_s": 0.0
        }
    finally:
        # Restore Settings
        settings.number_of_teams = original_teams
        settings.maximum_visits_per_team = original_visits
        
    # 4. Extract Metrics
    metrics = _extract_metrics(result)
    
    # 5. Determine Overall Scenario Result
    # Simple acceptance: If pipeline failed but we expected a failure, it's a PASS for the scenario.
    overall_result = "PASS"
    if scenario_id == "pipeline_failure":
        overall_result = "PASS" if result["status"] == "FAILED" else "FAIL (Expected pipeline failure)"
    else:
        overall_result = "PASS" if result["status"] == "SUCCESS" else "FAIL"
        
    if scenario_id == "safe_fallback" and result["status"] == "SUCCESS":
        if metrics.get("fallback_active_count", 0) == 0:
            overall_result = "FAIL (Fallback did not activate)"
            
    if scenario_id == "fairness_stress_test" and result["status"] == "SUCCESS":
        if metrics.get("max_coverage_gap_pct", 0) < 10.0:
             overall_result = "FAIL (Stress test didn't generate gap)"
             
    # 6. Format Final Result Record
    record = {
        "scenario_id": scenario_id,
        "scenario_name": config["name"],
        "run_id": run_id,
        "timestamp": timestamp,
        "pipeline_version": "8.0.0",
        "dataset_id": result.get("dataset_id", "N/A"),
        "scenario_configuration": config,
        "pipeline_status": result["status"],
        "pipeline_duration_s": result.get("pipeline_duration_s", 0.0),
        "errors": result.get("errors", []),
        "metrics": metrics,
        "overall_scenario_result": overall_result
    }
    
    # 7. Persist to disk
    run_file = os.path.join(SCENARIO_RUNS_DIR, f"{scenario_id}_{run_id}.json")
    latest_file = os.path.join(SCENARIO_LATEST_DIR, f"{scenario_id}.json")
    
    try:
        json_data = json.dumps(record, indent=2)
        with open(run_file, "w") as f:
            f.write(json_data)
        with open(latest_file, "w") as f:
            f.write(json_data)
        logger.info(f"Scenario results persisted to {run_file}")
    except Exception as e:
        logger.error(f"Failed to persist scenario results: {e}")
        
    # Inject record back into result so UI can display it
    result["scenario_record"] = record
    return result

def get_latest_scenario_result(scenario_id: str) -> Optional[Dict]:
    """Retrieves the latest run of a specific scenario from disk."""
    path = os.path.join(SCENARIO_LATEST_DIR, f"{scenario_id}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return None
