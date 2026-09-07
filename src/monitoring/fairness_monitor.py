"""
src/monitoring/fairness_monitor.py

Monitors fairness continuously across two population groups using
real pipeline results and configured thresholds.
"""
from typing import Dict, Any, List
import pandas as pd
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("fairness_monitor")

MONITORED_GROUPS = ["group_mobile", "group_low_service_access"]
HIGH_RISK_CATS   = {"EXTREME", "HIGH"}


def _compute_group_metrics(df: pd.DataFrame, group_col: str) -> Dict[str, Any]:
    """Computes coverage metrics for a single binary group column."""
    if group_col not in df.columns:
        return {"status": "COLUMN_MISSING"}

    group_mask = df[group_col] == True
    total_group = int(group_mask.sum())
    if total_group == 0:
        return {"status": "NO_MEMBERS", "total_group": 0}

    is_hr = df["multi_factor_risk_category"].isin(HIGH_RISK_CATS)
    hr_in_group = int((group_mask & is_hr).sum())
    selected_in_group = int((group_mask & df["selected_for_outreach"]).sum())
    hr_covered = int((group_mask & is_hr & df["selected_for_outreach"]).sum())

    coverage_rate = hr_covered / hr_in_group if hr_in_group > 0 else 0.0
    selection_rate = selected_in_group / total_group if total_group > 0 else 0.0

    return {
        "total_group":       total_group,
        "high_risk_count":   hr_in_group,
        "selected_count":    selected_in_group,
        "high_risk_covered": hr_covered,
        "coverage_rate_pct": round(coverage_rate * 100, 1),
        "selection_rate_pct": round(selection_rate * 100, 1),
    }


def monitor_fairness(
    pipeline_df: pd.DataFrame,
    fairness_warnings: List[Dict] = None,
) -> Dict[str, Any]:
    """
    Full fairness monitoring report comparing coverage across all monitored groups.

    Returns:
        {
          "overall_status": "PASS" | "WARNING" | "CRITICAL",
          "groups": { group_col: {...metrics} },
          "max_coverage_gap_pct": float,
          "threshold_pct": float,
          "warnings": [str],
        }
    """
    fairness_warnings = fairness_warnings or []

    if pipeline_df is None or pipeline_df.empty:
        return {
            "overall_status": "NO_DATA",
            "groups": {},
            "max_coverage_gap_pct": 0.0,
            "warnings": ["No pipeline data available for fairness monitoring."],
        }

    group_results: Dict[str, Any] = {}
    coverage_rates: List[float] = []

    for grp in MONITORED_GROUPS:
        metrics = _compute_group_metrics(pipeline_df, grp)
        group_results[grp] = metrics
        if "coverage_rate_pct" in metrics:
            coverage_rates.append(metrics["coverage_rate_pct"])

    # Fairness gap = max − min coverage rate across groups
    max_gap = 0.0
    if len(coverage_rates) >= 2:
        max_gap = max(coverage_rates) - min(coverage_rates)

    threshold_pct = settings.maximum_coverage_gap * 100

    warnings: List[str] = []
    if max_gap > threshold_pct:
        warnings.append(
            f"Coverage gap between groups is {max_gap:.1f}% "
            f"(threshold: {threshold_pct:.0f}%)"
        )

    # Add system-level warnings from the auditor
    for w in fairness_warnings:
        msg = w.get("message") if isinstance(w, dict) else str(w)
        if msg and msg not in warnings:
            warnings.append(msg)

    if not warnings:
        overall = "PASS"
    elif max_gap > threshold_pct * 2:
        overall = "CRITICAL"
    else:
        overall = "WARNING"

    return {
        "overall_status":      overall,
        "groups":              group_results,
        "max_coverage_gap_pct": round(max_gap, 1),
        "threshold_pct":       threshold_pct,
        "warnings":            warnings,
    }
