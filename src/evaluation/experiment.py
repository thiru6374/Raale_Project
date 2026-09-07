import pandas as pd
import json
from typing import Dict
from datetime import datetime
from src.evaluation.metrics import compute_model_comparison
from src.utils.logger import get_logger

logger = get_logger("experiment")

class ExperimentRunner:
    """Orchestrates a repeatable baseline vs multi-factor model comparison experiment."""

    def run_experiment(self, df_with_both_scores: pd.DataFrame, experiment_name: str = "default") -> Dict:
        """
        Runs the comparison experiment and returns a results dictionary.
        Expects the DataFrame to contain both 'baseline_risk_score' and 'multi_factor_risk_score'.
        """
        logger.info(f"Running experiment: '{experiment_name}'...")

        metrics = compute_model_comparison(df_with_both_scores, df_with_both_scores)

        result = {
            "experiment_name": experiment_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "num_records": len(df_with_both_scores),
            "metrics": metrics
        }

        logger.info(f"Experiment '{experiment_name}' complete.")
        return result

    def save_results(self, result: Dict, path: str = "data/processed/experiment_results.json"):
        """Persists experiment results to disk."""
        import os, json
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Experiment results saved to {path}")
