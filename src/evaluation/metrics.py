import pandas as pd
from typing import Dict, Any
from src.config.settings import settings

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
        "strategy": strategy_name,
        "total_analyzed": len(df),
        "high_risk_identified": 0,
        "high_risk_reached": 0,
        "high_risk_coverage_pct": 0.0,
        "total_selected": 0,
        "capacity_utilization_pct": 0.0,
        "uncovered_high_risk": 0,
        "avg_selected_risk_score": 0.0,
        "fairness": {},
        "fallback_count": 0,
        "manual_override_count": 0,
    }
    
    if df is None or df.empty:
        return metrics

    # Basic counts
    is_high_risk = df["multi_factor_risk_category"].isin(["EXTREME", "HIGH"])
    is_selected = df.get("selected_for_outreach", pd.Series([False]*len(df))) == True
    
    metrics["high_risk_identified"] = int(is_high_risk.sum())
    metrics["total_selected"] = int(is_selected.sum())
    
    # Coverage
    high_risk_reached = (is_high_risk & is_selected).sum()
    metrics["high_risk_reached"] = int(high_risk_reached)
    
    if metrics["high_risk_identified"] > 0:
        metrics["high_risk_coverage_pct"] = (metrics["high_risk_reached"] / metrics["high_risk_identified"]) * 100.0
        
    metrics["uncovered_high_risk"] = metrics["high_risk_identified"] - metrics["high_risk_reached"]
    
    # Capacity Utilization
    # Available capacity = number_of_teams * maximum_visits_per_team
    max_capacity = settings.number_of_teams * settings.maximum_visits_per_team
    if max_capacity > 0:
        metrics["capacity_utilization_pct"] = (metrics["total_selected"] / max_capacity) * 100.0
        
    # Risk Profile of Selected
    selected_df = df[is_selected]
    if not selected_df.empty and "multi_factor_risk_score" in selected_df.columns:
        metrics["avg_selected_risk_score"] = float(selected_df["multi_factor_risk_score"].mean())
        
    # Fallback and Overrides
    if "fallback_status" in df.columns:
        metrics["fallback_count"] = int((df["fallback_status"] != "STANDARD").sum())
        metrics["manual_override_count"] = int((df["fallback_status"] == "MANUAL_REVIEW").sum())

    # Fairness Metrics
    groups = ["group_mobile", "group_low_service_access"]
    for group in groups:
        if group in df.columns:
            group_mask = df[group] == True
            group_total = group_mask.sum()
            group_hr = (group_mask & is_high_risk).sum()
            group_selected = (group_mask & is_selected).sum()
            
            group_sel_rate = (group_selected / group_total * 100.0) if group_total > 0 else 0.0
            group_hr_cov = (group_selected / group_hr * 100.0) if group_hr > 0 else 0.0
            
            metrics["fairness"][group] = {
                "total": int(group_total),
                "high_risk": int(group_hr),
                "selected": int(group_selected),
                "selection_rate_pct": float(group_sel_rate),
                "high_risk_coverage_pct": float(group_hr_cov)
            }
            
    # Baseline Comparison (if BaselineRunResult is provided)
    # The Baseline prioritizes strictly by temperature.
    # To compare, we calculate what the baseline's High Risk Coverage would be.
    if baseline_results and baseline_results.status != "FAILED":
        # baseline_results.records contains the ranking
        baseline_selected_ids = [
            r.neighbourhood_id for r in baseline_results.records if r.baseline_selected
        ]
        
        # Merge baseline selection back to the main df for comparison
        df_base = df.copy()
        df_base["baseline_selected"] = df_base["neighbourhood_id"].astype(str).isin(baseline_selected_ids)
        
        base_hr_reached = (is_high_risk & df_base["baseline_selected"]).sum()
        base_hr_cov = (base_hr_reached / metrics["high_risk_identified"] * 100.0) if metrics["high_risk_identified"] > 0 else 0.0
        
        metrics["baseline_comparison"] = {
            "baseline_selected_total": len(baseline_selected_ids),
            "baseline_high_risk_reached": int(base_hr_reached),
            "baseline_high_risk_coverage_pct": float(base_hr_cov),
            "coverage_improvement_pct": float(metrics["high_risk_coverage_pct"] - base_hr_cov)
        }

    return metrics
