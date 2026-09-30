"""
src/evaluation/metrics.py

Calculates operational and fairness evaluation metrics for any optimization run.
Compatible with the multi-objective planner output (Phase 3 upgrade).
"""
import pandas as pd
from typing import Dict, Any
from src.config.settings import settings
from src.fairness.metrics import calculate_fairness_metrics


def calculate_evaluation_metrics(
    df: pd.DataFrame,
    baseline_results=None,
    strategy_name: str = "Unknown"
) -> Dict[str, Any]:
    """
    Calculates operational and fairness metrics for a given pipeline result.
    If baseline_results are provided, compares against the baseline.
    """
    metrics = {
        "strategy":                   strategy_name,
        "total_analyzed":             len(df),
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
        "uncovered_high_risk":        0,
        "fairness":                   {},
        "fairness_report":            [],
        "fallback_count":             0,
        "manual_override_count":      0,
    }

    if df is None or df.empty:
        return metrics

    # High risk definition – support both old EXTREME and new VERY HIGH
    is_high_risk = df["multi_factor_risk_category"].isin(
        ["VERY HIGH", "EXTREME", "HIGH"]
    ) if "multi_factor_risk_category" in df.columns else pd.Series(False, index=df.index)

    is_selected = (
        df.get("selected_for_outreach", pd.Series([False] * len(df))) == True
    )

    metrics["high_risk_identified"] = int(is_high_risk.sum())
    metrics["total_selected"]       = int(is_selected.sum())
    metrics["num_outreach_events"]  = metrics["total_selected"]

    # Risk coverage
    high_risk_reached = int((is_high_risk & is_selected).sum())
    metrics["high_risk_reached"] = high_risk_reached

    if metrics["high_risk_identified"] > 0:
        metrics["high_risk_coverage_pct"] = round(
            high_risk_reached / metrics["high_risk_identified"] * 100.0, 2
        )
    metrics["uncovered_high_risk"] = metrics["high_risk_identified"] - high_risk_reached

    # Population metrics
    selected_df = df[is_selected]
    pop_col = "population" if "population" in df.columns else "mobile_population"
    if pop_col in df.columns:
        metrics["total_population_reached"] = int(selected_df[pop_col].fillna(0).sum())
    if "mobile_population" in df.columns:
        metrics["mobile_population_reached"] = int(selected_df["mobile_population"].fillna(0).sum())
    if "group_low_service_access" in df.columns:
        metrics["low_service_access_reached"] = int(
            (is_selected & (df["group_low_service_access"] == True)).sum()
        )

    # Travel metrics
    if "healthcare_distance_km" in df.columns and not selected_df.empty:
        total_dist = float(selected_df["healthcare_distance_km"].fillna(0).sum())
        metrics["travel_distance_total_km"] = round(total_dist, 2)
        metrics["estimated_travel_time_h"]  = round(total_dist / 30.0, 2)

    # Capacity utilization
    max_capacity = settings.number_of_teams * settings.maximum_visits_per_team
    if max_capacity > 0:
        metrics["capacity_utilization_pct"] = round(
            metrics["total_selected"] / max_capacity * 100.0, 2
        )

    # Risk profile of selected
    if not selected_df.empty and "multi_factor_risk_score" in selected_df.columns:
        metrics["avg_selected_risk_score"] = float(selected_df["multi_factor_risk_score"].mean())

    # Fallback / overrides
    if "fallback_status" in df.columns:
        metrics["fallback_count"]       = int((df["fallback_status"] != "STANDARD").sum())
        metrics["manual_override_count"] = int((df["fallback_status"] == "MANUAL_REVIEW").sum())

    # Fairness metrics per protected group
    group_rates = {}
    for group in ["group_mobile", "group_low_service_access"]:
        if group in df.columns:
            g_mask    = df[group] == True
            g_total   = int(g_mask.sum())
            g_hr      = int((g_mask & is_high_risk).sum())
            g_sel     = int((g_mask & is_selected).sum())
            sel_rate  = round(g_sel / g_total * 100.0, 2) if g_total > 0 else 0.0
            hr_cov    = round(g_sel / g_hr * 100.0, 2) if g_hr > 0 else 0.0
            group_rates[group] = sel_rate
            metrics["fairness"][group] = {
                "total":                 g_total,
                "high_risk":             g_hr,
                "selected":              g_sel,
                "selection_rate_pct":    sel_rate,
                "high_risk_coverage_pct": hr_cov,
            }
            metrics["fairness_report"].append(calculate_fairness_metrics(df, group))

    # Fairness gap – absolute difference between group selection rates
    if len(group_rates) == 2:
        rates = list(group_rates.values())
        metrics["fairness_gap_pct"] = round(abs(rates[0] - rates[1]), 2)

    # Baseline comparison
    if baseline_results and baseline_results.status != "FAILED":
        baseline_selected_ids = [
            r.neighbourhood_id for r in baseline_results.records if r.baseline_selected
        ]
        df_base = df.copy()
        df_base["baseline_selected"] = df_base["neighbourhood_id"].astype(str).isin(
            baseline_selected_ids
        )
        base_hr_reached = int((is_high_risk & df_base["baseline_selected"]).sum())
        base_hr_cov = round(
            base_hr_reached / metrics["high_risk_identified"] * 100.0, 2
        ) if metrics["high_risk_identified"] > 0 else 0.0
        metrics["baseline_comparison"] = {
            "baseline_selected_total":       len(baseline_selected_ids),
            "baseline_high_risk_reached":    base_hr_reached,
            "baseline_high_risk_coverage_pct": base_hr_cov,
            "coverage_improvement_pct":      round(
                metrics["high_risk_coverage_pct"] - base_hr_cov, 2
            ),
        }

    return metrics
