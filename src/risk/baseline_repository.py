"""
src/risk/baseline_repository.py

Persists the results of the Baseline Model to the filesystem.
It treats the canonical dataset as read-only and writes exclusively to:
  data/results/baseline/
"""

import os
import pandas as pd
from typing import Optional
from src.config.settings import settings
from src.utils.logger import get_logger
from src.utils.helpers import ensure_dir, safe_write_json
from src.risk.baseline_contracts import BaselineRunResult

logger = get_logger("baseline_repository")


class BaselineRepository:
    """Handles saving and loading of Baseline outputs."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or settings.baseline_results_dir

    def save_run(self, run_result: BaselineRunResult) -> bool:
        """
        Save the complete run result (CSV, metadata JSON, summary JSON).
        """
        try:
            ensure_dir(self.output_dir)

            # 1. Save CSV
            if run_result.records:
                # Convert list of Pydantic models to list of dicts, then to DataFrame
                df = pd.DataFrame([r.model_dump() for r in run_result.records])
                csv_path = os.path.join(self.output_dir, "baseline_results.csv")
                df.to_csv(csv_path, index=False)
                logger.info(f"Saved baseline CSV to {csv_path}")

            # 2. Save Metadata
            if run_result.metadata:
                meta_path = os.path.join(self.output_dir, "baseline_metadata.json")
                safe_write_json(run_result.metadata.model_dump(), meta_path)
                logger.info(f"Saved baseline metadata to {meta_path}")

            # 3. Save Summary
            if run_result.summary:
                summary_path = os.path.join(self.output_dir, "baseline_summary.json")
                safe_write_json(run_result.summary.model_dump(), summary_path)
                logger.info(f"Saved baseline summary to {summary_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to save baseline run: {e}")
            return False
