import logging
from typing import Dict, Any

from src.services.pipeline_service import PipelineService
from src.evaluation.metrics import calculate_evaluation_metrics
from src.config.settings import settings

logger = logging.getLogger("failure_analysis")

class FailureAnalyzer:
    """
    Simulates failure modes by adjusting configuration or pipeline inputs
    and evaluating the robustness of the system.
    """
    
    def __init__(self, num_records: int = 50):
        self.num_records = num_records
        
    def run_scenario(self, scenario: str) -> Dict[str, Any]:
        """
        Runs a specific failure scenario.
        Supported: MISSING_TEMP, MISSING_COORDS, LOW_CAPACITY, UNTRUSTED_DATA, FAIRNESS_IMBALANCE
        """
        # Save original settings to restore later
        orig_missing_rate = 0.05
        orig_teams = settings.number_of_teams
        orig_visits = settings.maximum_visits_per_team
        
        try:
            if scenario == "MISSING_TEMP":
                logger.info("Simulating MISSING_TEMP failure mode...")
                # Increase missing rate significantly to force fallback on temp
                results = PipelineService.run_full_pipeline(num_records=self.num_records, missing_rate=0.40)
                
            elif scenario == "MISSING_COORDS":
                logger.info("Simulating MISSING_COORDS failure mode...")
                # The synthetic generator handles this if we set simulate_invalid_coordinates
                settings.simulate_invalid_coordinates = True
                results = PipelineService.run_full_pipeline(num_records=self.num_records)
                settings.simulate_invalid_coordinates = False
                
            elif scenario == "LOW_CAPACITY":
                logger.info("Simulating LOW_CAPACITY failure mode...")
                # Artificially constrain capacity so high risk areas go uncovered
                settings.number_of_teams = 1
                settings.maximum_visits_per_team = 2
                results = PipelineService.run_full_pipeline(num_records=self.num_records)
                
            elif scenario == "UNTRUSTED_DATA":
                logger.info("Simulating UNTRUSTED_DATA failure mode...")
                # Blank critical fields for all records to force LOW CONFIDENCE / MANUAL_REVIEW
                def blank_critical(df):
                    import pandas as pd
                    df = df.copy()
                    for col in ["temperature_c", "heat_index", "vulnerability_index",
                                "healthcare_capacity", "healthcare_distance_km"]:
                        if col in df.columns:
                            df[col] = float("nan")
                    return df
                results = PipelineService.run_full_pipeline(
                    num_records=self.num_records,
                    scenario_modifier_fn=blank_critical
                )
                
            elif scenario == "FAIRNESS_IMBALANCE":
                logger.info("Simulating FAIRNESS_IMBALANCE failure mode...")
                # Run with coverage focused, we rely on the natural imbalance in the data
                results = PipelineService.run_full_pipeline(num_records=self.num_records, strategy="COVERAGE_FOCUSED")
                
            else:
                raise ValueError(f"Unknown scenario {scenario}")
                
            if results["status"] == "FAILED":
                return {"status": "FAILED", "errors": results["errors"]}
                
            metrics = calculate_evaluation_metrics(
                df=results["pipeline_results"],
                baseline_results=results.get("baseline_results")
            )
            
            return {
                "status": "SUCCESS",
                "scenario": scenario,
                "results": results["pipeline_results"],
                "metrics": metrics,
                "fairness_warnings": results.get("fairness_warnings", [])
            }
            
        finally:
            # Restore settings
            settings.number_of_teams = orig_teams
            settings.maximum_visits_per_team = orig_visits
            settings.simulate_invalid_coordinates = False
