"""
src/evaluation/experiment_runner.py

Phase 9 upgrade: full 4-way comparison (BASELINE + 3 optimization strategies)
on the actual 50,000-row dataset.

For each strategy the runner calculates:
  - high-risk coverage, total/mobile/low-service population reached
  - travel time / distance / events
  - capacity utilization, constraint violations, fairness gap
  - objective score, avg confidence, runtime
  - proxy validation (top-risk capture, rank stability, rule agreement, etc.)
    OR supervised metrics if ground-truth labels exist.

Experiments are persisted with a full metadata envelope (experiment_id,
dataset_signature, configuration snapshot, model/optimizer versions).
"""
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

import pandas as pd

from src.services.pipeline_service import PipelineService
from src.evaluation.metrics import calculate_evaluation_metrics
from src.evaluation.validation_engine import validate_experiment_results
from src.evaluation.experiment_store import ExperimentStore
from src.config.settings import settings

logger = logging.getLogger("experiment_runner")

_STRATEGIES = ["COVERAGE_FOCUSED", "BALANCED", "FAIRNESS_AWARE"]


def _configuration_snapshot() -> Dict[str, Any]:
    """Capture key settings at experiment runtime for reproducibility."""
    return {
        "number_of_teams":            settings.number_of_teams,
        "maximum_visits_per_team":    settings.maximum_visits_per_team,
        "maximum_coverage_gap":       settings.maximum_coverage_gap,
        "minimum_confidence_for_auto": settings.minimum_confidence_for_automatic_recommendation,
        "working_hours":              settings.working_hours,
        "random_seed":                settings.random_seed,
        "data_mode":                  settings.data_mode,
        "active_csv_dataset":         settings.active_csv_dataset,
        "risk_weights": {
            "temperature":   settings.temperature_weight,
            "built_env":     settings.built_environment_weight,
            "service_access": settings.service_access_weight,
            "vulnerability": settings.vulnerability_weight,
            "mobility":      settings.mobility_weight,
        },
    }


class ExperimentRunner:
    """
    Runs evaluation experiments comparing BASELINE + 3 optimization strategies.
    Uses the actual 50,000-row dataset (num_records=0 means full load).
    """

    def __init__(self, num_records: int = 0, missing_rate: float = 0.05):
        self.num_records  = num_records   # 0 = load all rows
        self.missing_rate = missing_rate

    def run_comparison(self) -> Dict[str, Any]:
        """
        Full 4-way comparison: BASELINE + COVERAGE_FOCUSED + BALANCED + FAIRNESS_AWARE.
        Returns measured outcomes for all strategies plus experiment metadata.
        """
        t_start = time.time()
        logger.info(
            "Starting Phase 9 Experiment (4 strategies, num_records=%d)…",
            self.num_records,
        )

        # ── 1. Anchor run (COVERAGE_FOCUSED) ──────────────────────────────────
        results_cov = PipelineService.run_full_pipeline(
            num_records=self.num_records,
            missing_rate=self.missing_rate,
            strategy="COVERAGE_FOCUSED",
        )

        if results_cov["status"] == "FAILED":
            logger.error("Anchor pipeline run failed: %s", results_cov.get("errors"))
            return {"status": "FAILED", "errors": results_cov.get("errors", [])}

        raw_df           = results_cov["raw_df"]
        baseline_results = results_cov["baseline_results"]
        dataset_sig      = results_cov.get("dataset_signature", "")
        dataset_rows     = results_cov.get("dataset_rows", len(raw_df))
        dataset_name     = results_cov.get("dataset_name", "")

        strategy_results: Dict[str, Any] = {}

        # ── 2. Baseline strategy metrics ──────────────────────────────────────
        t0 = time.time()
        baseline_metrics = self._compute_baseline_metrics(
            results_cov["pipeline_results"], baseline_results
        )
        strategy_results["baseline"] = {
            "metrics":     baseline_metrics,
            "validation":  validate_experiment_results(results_cov["pipeline_results"]),
            "runtime_s":   round(time.time() - t0, 4),
        }

        # ── 3. COVERAGE_FOCUSED (already solved in anchor run) ────────────────
        t0 = time.time()
        cov_metrics = calculate_evaluation_metrics(
            df=results_cov["pipeline_results"],
            baseline_results=baseline_results,
            strategy_name="COVERAGE_FOCUSED",
        )
        cov_metrics["runtime_s"] = round(time.time() - t0, 4)
        strategy_results["coverage_focused"] = {
            "metrics":    cov_metrics,
            "validation": validate_experiment_results(results_cov["pipeline_results"]),
            "runtime_s":  cov_metrics["runtime_s"],
        }

        # ── 4. Re-run BALANCED and FAIRNESS_AWARE on identical raw data ────────
        for key, strat_name in [("balanced", "BALANCED"), ("fairness_aware", "FAIRNESS_AWARE")]:
            t0 = time.time()
            logger.info("Running %s strategy on identical dataset…", strat_name)
            run = self._run_pipeline_from_raw(raw_df, strat_name, dataset_sig)
            elapsed = round(time.time() - t0, 4)

            strat_metrics = calculate_evaluation_metrics(
                df=run["pipeline_results"],
                baseline_results=baseline_results,
                strategy_name=strat_name,
            )
            strat_metrics["runtime_s"] = elapsed
            strategy_results[key] = {
                "metrics":    strat_metrics,
                "validation": validate_experiment_results(run["pipeline_results"]),
                "runtime_s":  elapsed,
            }

        # ── 5. Persist experiment ─────────────────────────────────────────────
        total_runtime = round(time.time() - t_start, 4)
        store = ExperimentStore()
        experiment_id = store.save_experiment(
            strategy_results={
                k: {
                    "metrics":    v["metrics"],
                    "validation": v["validation"],
                    "runtime_s":  v["runtime_s"],
                }
                for k, v in strategy_results.items()
            },
            dataset_signature=dataset_sig,
            dataset_rows=dataset_rows,
            dataset_name=dataset_name,
            configuration=_configuration_snapshot(),
            runtime_s=total_runtime,
        )

        logger.info("Experiment %s completed in %.2fs.", experiment_id, total_runtime)

        return {
            "status":            "SUCCESS",
            "experiment_id":     experiment_id,
            "dataset_signature": dataset_sig,
            "dataset_rows":      dataset_rows,
            "dataset_name":      dataset_name,
            "total_runtime_s":   total_runtime,
            "configuration":     _configuration_snapshot(),
            "baseline_results":  baseline_results,
            **strategy_results,
        }

    # ── Baseline-specific metric builder ──────────────────────────────────────
    def _compute_baseline_metrics(self, pipeline_df: pd.DataFrame, baseline_results) -> Dict[str, Any]:
        """
        Build a metrics dict that represents the baseline model's selections,
        using the same metric schema as the optimizer strategies.
        """
        metrics = {
            "strategy": "BASELINE",
            "total_analyzed": len(pipeline_df),
            "high_risk_identified":       0,
            "high_risk_reached":          0,
            "high_risk_coverage_pct":     0.0,
            "total_selected":             0,
            "total_population_reached":   0,
            "mobile_population_reached":  0,
            "low_service_access_reached": 0,
            "travel_distance_total_km":   0.0,
            "estimated_travel_time_h":    0.0,
            "num_outreach_events":        0,
            "capacity_utilization_pct":   0.0,
            "fairness_gap_pct":           0.0,
            "avg_selected_risk_score":    0.0,
            "fallback_count":             0,
            "fairness_report":            [],
            "constraint_violations":      0,
            "runtime_s":                  0.0,
        }
        if baseline_results is None or not hasattr(baseline_results, "records"):
            return metrics

        selected_ids = {
            r.neighbourhood_id
            for r in baseline_results.records
            if getattr(r, "baseline_selected", False)
        }
        metrics["total_selected"] = len(selected_ids)
        metrics["num_outreach_events"] = len(selected_ids)

        if pipeline_df is not None and not pipeline_df.empty:
            is_high = pipeline_df.get("multi_factor_risk_category", pd.Series(dtype=str)).isin(
                {"VERY HIGH", "EXTREME", "HIGH"}
            )
            is_sel = pipeline_df["neighbourhood_id"].astype(str).isin(selected_ids)
            metrics["high_risk_identified"] = int(is_high.sum())
            metrics["high_risk_reached"]    = int((is_high & is_sel).sum())
            if metrics["high_risk_identified"] > 0:
                metrics["high_risk_coverage_pct"] = round(
                    metrics["high_risk_reached"] / metrics["high_risk_identified"] * 100.0, 2
                )
            sel_df = pipeline_df[is_sel]
            pop_col = "population" if "population" in pipeline_df.columns else "mobile_population"
            if pop_col in pipeline_df.columns:
                metrics["total_population_reached"] = int(sel_df[pop_col].fillna(0).sum())
            max_cap = settings.number_of_teams * settings.maximum_visits_per_team
            if max_cap > 0:
                metrics["capacity_utilization_pct"] = round(
                    len(selected_ids) / max_cap * 100.0, 2
                )

        return metrics

    # ── Internal re-run on shared raw_df ──────────────────────────────────────
    def _run_pipeline_from_raw(
        self,
        raw_df: pd.DataFrame,
        strategy: str,
        dataset_signature: str = "",
    ) -> Dict[str, Any]:
        """
        Runs preprocessing → features → risk → confidence → planner
        on an already-loaded raw DataFrame for a given strategy.
        """
        from src.data.preprocessing import DataPreprocessor
        from src.features.engineering import FeatureEngineer
        from src.risk.risk_engine import MultiFactorRiskModel
        from src.risk.confidence import ConfidenceEvaluator
        from src.optimisation.planner import OutreachPlanner
        from src.services.pipeline_service import (
            _normalise_columns,
            _ensure_baseline_temperature_column,
        )

        preprocessor  = DataPreprocessor()
        processed_df  = preprocessor.process_dataframe(raw_df)
        processed_df  = _normalise_columns(processed_df)
        processed_df  = _ensure_baseline_temperature_column(processed_df)

        engineer      = FeatureEngineer()
        featured_df   = engineer.generate_features(processed_df)

        risk_model    = MultiFactorRiskModel()
        risk_df       = risk_model.calculate_risk(featured_df)

        evaluator     = ConfidenceEvaluator()
        confident_df  = evaluator.evaluate(raw_df, risk_df)

        planner       = OutreachPlanner()
        planned_df    = planner.plan_outreach(
            confident_df,
            strategy=strategy,
            dataset_signature=dataset_signature,
        )

        return {"status": "SUCCESS", "pipeline_results": planned_df}
