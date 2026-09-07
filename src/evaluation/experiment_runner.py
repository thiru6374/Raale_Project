import logging
import pandas as pd
from typing import Dict, Any

from src.services.pipeline_service import PipelineService
from src.evaluation.metrics import calculate_evaluation_metrics

logger = logging.getLogger("experiment_runner")

class ExperimentRunner:
    """
    Runs evaluation experiments comparing multiple optimization strategies against the baseline.
    """
    
    def __init__(self, num_records: int = 100, missing_rate: float = 0.05):
        self.num_records = num_records
        self.missing_rate = missing_rate
        
    def run_comparison(self) -> Dict[str, Any]:
        """
        Runs the pipeline with different strategies and compares the results.
        """
        logger.info("Starting Strategy Comparison Experiment...")
        
        # 1. Run COVERAGE_FOCUSED (This is our standard pipeline and acts as the anchor for the dataset)
        results_coverage = PipelineService.run_full_pipeline(
            num_records=self.num_records, 
            missing_rate=self.missing_rate, 
            strategy="COVERAGE_FOCUSED"
        )
        
        if results_coverage["status"] == "FAILED":
            logger.error("Base pipeline execution failed. Cannot run experiment.")
            return {"status": "FAILED", "errors": results_coverage["errors"]}
            
        # Extract the exact dataset to ensure FAIR comparison across strategies
        raw_df = results_coverage["raw_df"]
        baseline_results = results_coverage["baseline_results"]
        
        # Calculate metrics for COVERAGE_FOCUSED
        metrics_coverage = calculate_evaluation_metrics(
            df=results_coverage["pipeline_results"],
            baseline_results=baseline_results,
            strategy_name="COVERAGE_FOCUSED"
        )
        
        # 2. Run FAIRNESS_AWARE on the exact same dataset
        # We need to bypass the random synthetic generation for the second run to ensure a fair comparison.
        # But PipelineService.run_full_pipeline calls load_synthetic_data inside it.
        # So we will run a slightly modified internal pipeline execution just for the experiment.
        
        logger.info("Running FAIRNESS_AWARE strategy on identical dataset...")
        results_fairness = self._run_pipeline_from_raw(raw_df, strategy="FAIRNESS_AWARE")
        
        metrics_fairness = calculate_evaluation_metrics(
            df=results_fairness["pipeline_results"],
            baseline_results=baseline_results,
            strategy_name="FAIRNESS_AWARE"
        )
        
        return {
            "status": "SUCCESS",
            "baseline_results": baseline_results,
            "coverage_focused": {
                "results": results_coverage["pipeline_results"],
                "metrics": metrics_coverage
            },
            "fairness_aware": {
                "results": results_fairness["pipeline_results"],
                "metrics": metrics_fairness
            }
        }
        
    def _run_pipeline_from_raw(self, raw_df: pd.DataFrame, strategy: str) -> Dict[str, Any]:
        """
        Runs onwards on an existing raw dataset.
        """
        from src.data.preprocessing import DataPreprocessor
        from src.features.engineering import FeatureEngineer
        from src.risk.risk_engine import MultiFactorRiskModel
        from src.risk.confidence import ConfidenceEvaluator
        from src.optimisation.planner import OutreachPlanner
        from src.services.pipeline_service import _normalise_columns, _ensure_baseline_temperature_column
        
        preprocessor = DataPreprocessor()
        processed_df = preprocessor.process_dataframe(raw_df)
        processed_df = _normalise_columns(processed_df)
        processed_df = _ensure_baseline_temperature_column(processed_df)
        
        engineer = FeatureEngineer()
        featured_df = engineer.generate_features(processed_df)
        
        multi_model = MultiFactorRiskModel()
        risk_df = multi_model.calculate_risk(featured_df)
        
        evaluator = ConfidenceEvaluator()
        confident_df = evaluator.evaluate(raw_df, risk_df)
        
        planner = OutreachPlanner()
        planned_df = planner.plan_outreach(confident_df, strategy=strategy)
        
        return {
            "status": "SUCCESS",
            "pipeline_results": planned_df
        }
