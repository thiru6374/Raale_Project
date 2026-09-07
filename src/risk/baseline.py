"""
src/risk/baseline.py

Contains two classes:

  BaselineRiskModel (era)
      ↳ Used by MultiFactorRiskModel in risk_engine.py.
        Calculates a [0-1] risk score from heat_index / temperature_c.
        Preserved unchanged for backward compatibility.

  BaselinePrioritisationModel ()
      ↳ Implements the Temperature-Only Baseline Prioritisation Model.
        Consumes the canonical processed dataset exclusively.
        Produces structured, auditable, experiment-ready results.
        Does NOT use vulnerability, fairness, or service-access features.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Optional

from src.config.settings import settings
from src.utils.logger import get_logger
from src.utils.helpers import dataframe_fingerprint, safe_read_json
from src.data.loader import DataLoader
from src.data.validation import DataQualityStatus
from src.risk.baseline_contracts import (
    BaselineRecordResult,
    BaselineRecordStatus,
    BaselinePriority,
    BaselineMetadata,
    BaselineSummary,
    BaselineRunResult,
    BaselineRunStatus,
)
from src.risk.baseline_ranking import (
    validate_baseline_input,
    partition_by_temperature,
    rank_by_temperature,
    assign_priority_categories,
    select_top_n,
    select_by_threshold,
)

logger = get_logger("baseline_model")


# ─────────────────────────────────────────────────────────────
#  era model — PRESERVED for MultiFactorRiskModel
# ─────────────────────────────────────────────────────────────

class BaselineRiskModel:
    """
    A naive baseline model that evaluates heat risk strictly based on temperature
    and heat index, ignoring vulnerability and built environment factors.

    NOTE: This class is retained for backward compatibility with MultiFactorRiskModel
    (risk_engine.py). For the Temperature-Only Baseline Prioritisation,
    use BaselinePrioritisationModel instead.
    """

    # Chennai-specific categorisation thresholds for Heat Index (°C)
    # Sourced from general meteorological heat-stress guidelines
    THRESHOLD_MODERATE = 32.0
    THRESHOLD_HIGH = 39.0
    THRESHOLD_EXTREME = 45.0

    def calculate_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the baseline risk score (0-1) and category.
        Requires 'heat_index' (or 'temperature_c' as fallback).
        """
        result_df = df.copy()

        # Use heat index if available, fallback to temperature_c
        primary_metric = 'heat_index' if 'heat_index' in result_df.columns else 'temperature_c'

        if primary_metric not in result_df.columns:
            raise ValueError(f"Required column '{primary_metric}' missing for baseline model.")

        # Calculate a continuous score [0, 1] using min-max scaling bound between realistic extremes
        min_temp = 25.0
        max_temp = 50.0

        raw_scores = (result_df[primary_metric] - min_temp) / (max_temp - min_temp)
        result_df['baseline_risk_score'] = raw_scores.clip(0.0, 1.0)

        # Categorize
        conditions = [
            (result_df[primary_metric] >= self.THRESHOLD_EXTREME),
            (result_df[primary_metric] >= self.THRESHOLD_HIGH),
            (result_df[primary_metric] >= self.THRESHOLD_MODERATE),
            (result_df[primary_metric] < self.THRESHOLD_MODERATE)
        ]
        choices = ['EXTREME', 'HIGH', 'MODERATE', 'LOW']

        result_df['baseline_risk_category'] = np.select(conditions, choices, default='UNKNOWN')

        return result_df


# ─────────────────────────────────────────────────────────────
#  — Temperature-Only Baseline Prioritisation Model
# ─────────────────────────────────────────────────────────────

class BaselinePrioritisationModel:
    """
    Temperature-Only Baseline Prioritisation Model.

    Algorithm (intentionally simple and transparent):
      1. Load canonical processed dataset via DataLoader.
      2. Validate required columns exist.
      3. Partition records: valid temperature vs DATA_INSUFFICIENT.
      4. Sort valid records descending by temperature.
         Tie-break: alphabetical neighbourhood_id (deterministic, ID-only).
      5. Assign integer rank (1 = hottest).
      6. Assign priority categories (HIGH / MEDIUM / LOW) from percentile bounds.
      7. Select top-N or threshold-based records.
      8. Build structured BaselineRunResult with metadata and summary.

    This model MUST NOT use vulnerability, fairness, or service-access features.
    It is a genuine simple comparator for experimental evaluation.
    """

    def __init__(self):
        self.loader = DataLoader()
        self._run_timestamp = datetime.now().isoformat()

    def run(self) -> BaselineRunResult:
        """
        Execute the complete baseline pipeline.

        Returns a BaselineRunResult containing per-record results, metadata,
        summary, warnings, and errors. Saves results via BaselineRepository.
        """
        self._run_timestamp = datetime.now().isoformat()
        logger.info("=" * 60)
        logger.info("— TEMPERATURE-ONLY BASELINE — Starting pipeline")
        logger.info("=" * 60)

        # ── 1. Load canonical processed dataset ──────────────────────
        df = self.loader.load_processed_dataset()
        if df is None or len(df) == 0:
            return self._build_failed_result(
                "Canonical processed dataset could not be loaded or is empty. "
                "Run preprocessing first."
            )

        # ── 2. Load preprocessing metadata for provenance ────────────
        pp_meta = safe_read_json(
            f"{settings.processed_data_dir}/preprocessing_metadata.json"
        ) or {}
        input_dataset_version   = pp_meta.get("dataset_version", "unknown")
        preprocessing_version   = pp_meta.get("preprocessing_version", "unknown")

        # ── 3. Fingerprint the input dataset ─────────────────────────
        temp_feat = settings.baseline_temperature_feature
        fingerprint = dataframe_fingerprint(df)

        # ── 4. Validate input schema ──────────────────────────────────
        errors = validate_baseline_input(df, temp_feat)
        if errors:
            return self._build_failed_result(
                f"Input validation failed: {'; '.join(errors)}"
            )

        total_records = len(df)
        warnings: List[str] = []

        # ── 5. Partition: valid temp vs missing ───────────────────────
        valid_df, missing_df = partition_by_temperature(df, temp_feat)
        missing_count = len(missing_df)

        if missing_count > 0:
            warnings.append(
                f"{missing_count} neighbourhood(s) have missing '{temp_feat}' "
                "and cannot be automatically ranked (DATA_INSUFFICIENT)."
            )
        if len(valid_df) == 0:
            return self._build_failed_result(
                f"All {total_records} records have missing '{temp_feat}'. "
                "Ranking cannot be completed."
            )

        # ── 6. Rank valid records ─────────────────────────────────────
        ranked_df = rank_by_temperature(
            valid_df,
            temperature_feature=temp_feat,
            tie_break_column=settings.baseline_tie_break_column,
        )

        # ── 7. Assign priority categories ─────────────────────────────
        ranked_df = assign_priority_categories(
            ranked_df,
            high_percentile=settings.baseline_high_percentile,
            medium_percentile=settings.baseline_medium_percentile,
        )

        # ── 8. Selection (top-N or threshold) ─────────────────────────
        selection_mode = settings.baseline_selection_mode
        if selection_mode == "top_n":
            ranked_df, sel_warnings = select_top_n(ranked_df, settings.baseline_top_n)
            selection_param = settings.baseline_top_n
        elif selection_mode == "threshold":
            ranked_df, sel_warnings = select_by_threshold(
                ranked_df, temp_feat, settings.baseline_threshold_temperature
            )
            selection_param = settings.baseline_threshold_temperature
        else:
            sel_warnings = [f"Unknown selection mode '{selection_mode}'. Defaulting to top_n=10."]
            ranked_df, _ = select_top_n(ranked_df, 10)
            selection_param = 10

        warnings.extend(sel_warnings)

        # ── 9. Build per-record results ───────────────────────────────
        records = self._build_records(ranked_df, missing_df, temp_feat, fingerprint)

        selected_count  = int(ranked_df.get("baseline_selected", pd.Series()).sum())
        ranked_count    = len(ranked_df)

        # ── 10. Statistics ────────────────────────────────────────────
        highest_temp = float(ranked_df[temp_feat].max()) if ranked_count > 0 else None
        lowest_ranked = float(ranked_df[temp_feat].min()) if ranked_count > 0 else None

        # ── 11. Build metadata ────────────────────────────────────────
        metadata = BaselineMetadata(
            baseline_version=settings.baseline_version,
            run_timestamp=self._run_timestamp,
            input_dataset_version=input_dataset_version,
            preprocessing_version=preprocessing_version,
            dataset_fingerprint=fingerprint,
            temperature_feature=temp_feat,
            selection_mode=selection_mode,
            selection_parameter=selection_param,
            tie_break_column=settings.baseline_tie_break_column,
            missing_temperature_policy=settings.baseline_missing_temperature_policy,
            high_percentile=settings.baseline_high_percentile,
            medium_percentile=settings.baseline_medium_percentile,
            total_neighbourhoods=total_records,
            ranked_neighbourhoods=ranked_count,
            data_insufficient_neighbourhoods=missing_count,
            selected_neighbourhoods=selected_count,
            missing_temperature_count=missing_count,
            highest_temperature=highest_temp,
            lowest_ranked_temperature=lowest_ranked,
        )

        # ── 12. Build summary ─────────────────────────────────────────
        run_status = (
            BaselineRunStatus.COMPLETED_WITH_WARNING if warnings
            else BaselineRunStatus.COMPLETED
        )
        summary = BaselineSummary(
            temperature_feature=temp_feat,
            status=run_status,
            total_neighbourhoods=total_records,
            ranked_neighbourhoods=ranked_count,
            data_insufficient_neighbourhoods=missing_count,
            selected_neighbourhoods=selected_count,
            highest_temperature_c=highest_temp,
            lowest_ranked_temperature_c=lowest_ranked,
            warnings=warnings,
        )

        result = BaselineRunResult(
            status=run_status,
            records=records,
            metadata=metadata,
            summary=summary,
            warnings=warnings,
        )

        logger.info(
            f"Pipeline complete. Status={run_status.value}  "
            f"Ranked={ranked_count}  Insufficient={missing_count}  "
            f"Selected={selected_count}"
        )
        return result

    # ─────────────────────────────────────────────────────────
    #  Private helpers
    # ─────────────────────────────────────────────────────────

    def _build_records(
        self,
        ranked_df: pd.DataFrame,
        missing_df: pd.DataFrame,
        temp_feat: str,
        fingerprint: str,
    ) -> List[BaselineRecordResult]:
        records: List[BaselineRecordResult] = []

        # Ranked records
        for _, row in ranked_df.iterrows():
            temp_val = row.get(temp_feat)
            records.append(BaselineRecordResult(
                neighbourhood_id=str(row["neighbourhood_id"]),
                neighbourhood_name=row.get("neighbourhood_name"),
                baseline_temperature_feature=temp_feat,
                baseline_temperature_value=float(temp_val) if pd.notna(temp_val) else None,
                baseline_score=float(temp_val) if pd.notna(temp_val) else None,
                baseline_rank=int(row["baseline_rank"]),
                baseline_priority=BaselinePriority(row["baseline_priority"]),
                baseline_selected=bool(row.get("baseline_selected", False)),
                baseline_status=BaselineRecordStatus.RANKED,
                run_timestamp=self._run_timestamp,
                baseline_version=settings.baseline_version,
                dataset_fingerprint=fingerprint,
            ))

        # Missing temperature records — DATA_INSUFFICIENT
        for _, row in missing_df.iterrows():
            records.append(BaselineRecordResult(
                neighbourhood_id=str(row["neighbourhood_id"]),
                neighbourhood_name=row.get("neighbourhood_name"),
                baseline_temperature_feature=temp_feat,
                baseline_temperature_value=None,
                baseline_score=None,
                baseline_rank=None,
                baseline_priority=BaselinePriority.DATA_INSUFFICIENT,
                baseline_selected=False,
                baseline_status=BaselineRecordStatus.DATA_INSUFFICIENT,
                status_reason=f"'{temp_feat}' is missing — cannot rank automatically.",
                run_timestamp=self._run_timestamp,
                baseline_version=settings.baseline_version,
                dataset_fingerprint=fingerprint,
            ))

        return records

    def _build_failed_result(self, reason: str) -> BaselineRunResult:
        logger.error(f"Baseline pipeline FAILED: {reason}")
        return BaselineRunResult(
            status=BaselineRunStatus.FAILED,
            errors=[reason],
        )


if __name__ == "__main__":
    from src.risk.baseline_repository import BaselineRepository
    import sys
    
    # Configure logger for terminal output
    import logging
    logging.getLogger().setLevel(logging.INFO)
    
    print("\n========================================")
    print("— TEMPERATURE-ONLY BASELINE")
    print("========================================\n")
    
    model = BaselinePrioritisationModel()
    result = model.run()
    
    if result.status == BaselineRunStatus.FAILED:
        print("\nPipeline FAILED:")
        for err in result.errors:
            print(f" - {err}")
        sys.exit(1)
        
    repo = BaselineRepository()
    saved = repo.save_run(result)
    
    print("\nSummary:")
    print(f"  Input Dataset:           neighbourhood_dataset")
    print(f"  Temperature Feature:     {result.summary.temperature_feature}")
    print(f"  Total Neighbourhoods:    {result.summary.total_neighbourhoods}")
    print(f"  Ranked:                  {result.summary.ranked_neighbourhoods}")
    print(f"  Data Insufficient:       {result.summary.data_insufficient_neighbourhoods}")
    print(f"  Selected:                {result.summary.selected_neighbourhoods}")
    print(f"  Status:                  {result.status}")
    
    if saved:
        print(f"  Output:                  {repo.output_dir}\\baseline_results.csv")
    
    print("\n========================================\n")

