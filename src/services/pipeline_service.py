import logging
import time
from typing import Dict, Any

import numpy as np
import pandas as pd

from src.data.ingestion import load_synthetic_data
from src.data.preprocessing import DataPreprocessor
from src.features.engineering import FeatureEngineer
from src.risk.risk_engine import MultiFactorRiskModel
from src.risk.confidence import ConfidenceEvaluator
from src.optimisation.planner import OutreachPlanner
from src.fairness.bias_detection import FairnessAuditor
from src.communication.message_generator import MessageGenerator
from src.risk.baseline import BaselinePrioritisationModel
from src.governance.dataset_registry import register_dataset, update_lineage_stage
from src.config.settings import settings

logger = logging.getLogger(__name__)


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Min-max normalise columns required by FeatureEngineer if they are not
    already present. The preprocessor normalises these when it is run from
    raw domain files; when called via process_dataframe() on a single
    unified CSV we have to do it here.
    """
    df = df.copy()
    norm_map = {
        "healthcare_capacity": "healthcare_capacity_normalized",
        "healthcare_distance_km": "healthcare_distance_km_normalized",
        "built_density": "built_density_normalized",
    }
    for src_col, dst_col in norm_map.items():
        if dst_col not in df.columns and src_col in df.columns:
            col = df[src_col].astype(float)
            col_min, col_max = col.min(), col.max()
            if col_max > col_min:
                df[dst_col] = (col - col_min) / (col_max - col_min)
            else:
                df[dst_col] = 0.0

    # green_cover_percent and impervious_surface_percent: already 0-100 raw;
    # standardise to 0-1 if not done yet.
    for pct_col in ["green_cover_percent", "impervious_surface_percent"]:
        if pct_col in df.columns and df[pct_col].max() > 1.0:
            df[pct_col] = df[pct_col] / 100.0

    return df


def _ensure_baseline_temperature_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    The Baseline model reads 'latest_temperature_c' from the
    canonical CSV.  When data comes directly from the synthetic generator
    (no multi-day observations), the column is simply 'temperature_c'.
    This function creates the alias so the baseline model works correctly
    without modifying the baseline code.
    """
    if "latest_temperature_c" not in df.columns:
        if "temperature_c" in df.columns:
            df = df.copy()
            df["latest_temperature_c"] = df["temperature_c"]
            logger.info(
                "Aliased 'temperature_c' → 'latest_temperature_c' for "
                "Baseline model compatibility."
            )
        else:
            logger.warning(
                "Neither 'temperature_c' nor 'latest_temperature_c' found. "
                "Baseline model will report DATA_INSUFFICIENT for all records."
            )
    return df


class PipelineService:
    """Central service to execute the end-to-end data pipeline once per session."""

    @staticmethod
    def run_full_pipeline(
        num_records: int = 0, 
        missing_rate: float = 0.05, 
        strategy: str = "COVERAGE_FOCUSED",
        scenario_modifier_fn = None
    ) -> Dict[str, Any]:
        """
        Executes Phases 1-4 + Optimisation + Fairness + Communications.
        If scenario_modifier_fn is provided, it is applied to valid_df immediately after ingestion.
        num_records=0 means load ALL rows (correct default for CSV_DATA mode).
        Returns a structured result dictionary.
        """
        try:
            _t0 = time.time()
            logger.info(
                "Pipeline started: %d records, missing_rate=%.2f, strategy=%s",
                num_records, missing_rate, strategy
            )

            # -------------------------------------------------------------- #
            # & 2 — Data Generation and Validation
            # — Data Providers and Spatial Validation
            # -------------------------------------------------------------- #
            from src.data_providers.provider_service import ProviderService
            raw_df, provider_metadata = ProviderService.get_data(
                data_mode=settings.data_mode,
                num_records=num_records, 
                missing_rate=missing_rate
            )
            
            # Spatial Validation ()
            from src.geo.spatial_validator import validate_spatial_data
            raw_df = validate_spatial_data(raw_df)
            
            # Validate through existing schema validator
            # We bypass the file-based CSVDataProvider to use the DataFrame directly for validation
            from src.data.ingestion import DataIngestor
            class DataFrameProvider:
                def __init__(self, df): self.df = df
                def fetch_data(self): return self.df
            ingestor = DataIngestor(DataFrameProvider(raw_df))
            valid_df, validation_report = ingestor.load_and_validate()
            
            if valid_df.empty:
                raise ValueError(
                    "Data ingestion yielded no valid records. "
                    f"Validation reported {validation_report.invalid_records} errors."
                )
            
            logger.info(
                "Ingested %d valid records (%d rejected). Source: %s",
                len(valid_df), validation_report.invalid_records, provider_metadata.get("source_type")
            )
            
            # ── Scenario Override ──────────────────────────────────
            if scenario_modifier_fn is not None:
                logger.info("Applying scenario input modifications...")
                valid_df = scenario_modifier_fn(valid_df)
                raw_df = valid_df.copy()  # Update raw_df to reflect scenario inputs
            
            # ── Register dataset in governance layer ────────────────
            dataset_id = register_dataset(
                raw_df,
                source_type="synthetic_generated",
                validation_status="PASS" if validation_report.invalid_records == 0 else "WARNING",
            )
            update_lineage_stage(dataset_id, "schema_validation", "COMPLETE")

            # -------------------------------------------------------------- #
            # a — Preprocessing
            # Saves canonical dataset to data/processed/ so can read it.
            # -------------------------------------------------------------- #
            preprocessor = DataPreprocessor()
            processed_df = preprocessor.process_dataframe(valid_df)
            logger.info("Preprocessing complete — %d records.", len(processed_df))
            update_lineage_stage(dataset_id, "preprocessing", "COMPLETE")

            # Ensure normalised feature columns expected by FeatureEngineer exist.
            processed_df = _normalise_columns(processed_df)

            # Ensure temperature alias expected by BaselinePrioritisationModel.
            processed_df = _ensure_baseline_temperature_column(processed_df)

            # Persist the augmented canonical dataset so the Baseline model
            # reads the correct column from disk.
            from src.data.loader import DataLoader
            DataLoader().save_processed_dataset(processed_df)

            # -------------------------------------------------------------- #
            # b — Feature Engineering
            # -------------------------------------------------------------- #
            engineer = FeatureEngineer()
            featured_df = engineer.generate_features(processed_df)
            logger.info("Feature engineering complete.")
            update_lineage_stage(dataset_id, "feature_engineering", "COMPLETE")

            # -------------------------------------------------------------- #
            # a — Multi-Factor Risk Scoring
            # -------------------------------------------------------------- #
            multi_model = MultiFactorRiskModel()
            risk_df = multi_model.calculate_risk(featured_df)
            logger.info("Multi-factor risk scoring complete.")
            update_lineage_stage(dataset_id, "risk_assessment", "COMPLETE")

            # -------------------------------------------------------------- #
            # b — Confidence Evaluation
            # Note: valid_df is used (not raw_df) because risk_df was derived
            # from valid_df after Pydantic validation (which may drop records).
            # Using raw_df here would cause a length mismatch.
            # -------------------------------------------------------------- #
            evaluator = ConfidenceEvaluator()
            confident_df = evaluator.evaluate(valid_df, risk_df)
            logger.info("Confidence evaluation complete.")

            # -------------------------------------------------------------- #
            # Optimisation — capacity-aware outreach planning
            # -------------------------------------------------------------- #
            planner = OutreachPlanner()
            planned_df = planner.plan_outreach(confident_df, strategy=strategy)
            selected_count = int(planned_df["selected_for_outreach"].sum())
            logger.info(
                "Outreach planning complete — %d selected.", selected_count
            )

            # -------------------------------------------------------------- #
            # Fairness Analysis — two target population groups audited
            # -------------------------------------------------------------- #
            auditor = FairnessAuditor(
                target_groups=["group_mobile", "group_low_service_access"]
            )
            fairness_warnings = auditor.audit_plan(planned_df)
            logger.info(
                "Fairness audit complete — %d warning(s).",
                len(fairness_warnings),
            )

            # -------------------------------------------------------------- #
            # Communication Recommendations — localised advisories
            # -------------------------------------------------------------- #
            generator = MessageGenerator()
            final_df = generator.generate_messages(planned_df)
            logger.info("Message generation complete.")

            # -------------------------------------------------------------- #
            # Baseline — Temperature-Only (reads canonical CSV)
            # Run AFTER saving the augmented processed dataset.
            # -------------------------------------------------------------- #
            baseline_model = BaselinePrioritisationModel()
            baseline_result = baseline_model.run()
            logger.info(
                "Baseline model complete — status: %s.", baseline_result.status
            )

            update_lineage_stage(dataset_id, "optimization", "COMPLETE")
            update_lineage_stage(dataset_id, "communication", "COMPLETE")
            
            _duration = time.time() - _t0
            
            # Create standard schema mapping for UI: risk_level
            if "multi_factor_risk_category" in final_df.columns:
                risk_mapping = {
                    "EXTREME": "VERY HIGH", # For backwards compatibility with old model runs
                    "VERY HIGH": "VERY HIGH",
                    "HIGH": "HIGH",
                    "MODERATE": "MODERATE",
                    "MEDIUM": "MODERATE", # For backwards compatibility
                    "LOW": "LOW"
                }
                final_df["risk_level"] = final_df["multi_factor_risk_category"].map(risk_mapping).fillna(final_df["multi_factor_risk_category"])

            # -------------------------------------------------------------- #
            # — Intelligence Service (Alerts, Priorities, Proposals)
            # -------------------------------------------------------------- #
            pipeline_result = {
                "status": "SUCCESS",
                "raw_df": raw_df,
                "processed_df": processed_df,
                "pipeline_results": final_df,
                "fairness_warnings": fairness_warnings,
                "baseline_results": baseline_result,
                "dataset_id": dataset_id,
                "provider_metadata": provider_metadata,
                "pipeline_duration_s": _duration,
                "errors": [],
                # Dataset identity — used by AppState to detect dataset switches
                "dataset_name": provider_metadata.get("filename", settings.active_csv_dataset),
                "dataset_rows": len(raw_df),
                "dataset_signature": provider_metadata.get("signature", ""),
                "date_range": (
                    f"{raw_df['date'].min()} to {raw_df['date'].max()}" 
                    if 'date' in raw_df.columns else "N/A"
                ),
                "configuration_version": getattr(settings, 'version', '1.0'),
                "pipeline_timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z",
            }
            
            from src.intelligence.intelligence_service import IntelligenceService
            intel_service = IntelligenceService()
            
            t_intel_start = time.time()
            enriched_result = intel_service.process_pipeline_result(pipeline_result)
            t_intel_end = time.time()
            enriched_result["timeliness"] = {
                "total_duration": _duration,
                "intelligence_duration": t_intel_end - t_intel_start
            }
            
            logger.info("Pipeline finished successfully in %.2fs (Intelligence: %.2fs).", _duration, t_intel_end - t_intel_start)
            return enriched_result

        except Exception as exc:
            logger.error("Pipeline failed: %s", str(exc), exc_info=True)
            return {
                "status": "FAILED",
                "raw_df": None,
                "processed_df": None,
                "pipeline_results": None,
                "fairness_warnings": [],
                "baseline_results": None,
                "dataset_id": "N/A",
                "pipeline_duration_s": 0.0,
                "errors": [str(exc)],
            }
