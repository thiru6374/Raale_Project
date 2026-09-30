"""
src/fairness/metrics.py

Phase 6: Fairness and Bias Analysis Upgrade

Calculates mathematically rigorous fairness metrics for outreach plans.
"""
import pandas as pd
from typing import Dict, Any

def _safe_div(n, d):
    return float(n) / float(d) if d > 0 else 0.0

def calculate_fairness_metrics(df: pd.DataFrame, group_col: str) -> Dict[str, Any]:
    """
    Computes rigorous fairness metrics for a specific vulnerable group.
    
    Metrics:
    - Coverage Gap: ABS(Group Coverage - Overall Coverage)
    - Coverage Ratio: Group Coverage / Overall Coverage
    - Opportunity Difference: Group Coverage - Non-Group Coverage
    - Population-Weighted Coverage: (Group Pop Reached) / (Group Pop Total)
    """
    if "selected_for_outreach" not in df.columns:
        raise ValueError("DataFrame must contain 'selected_for_outreach'")
        
    pop_col = "population" if "population" in df.columns else "mobile_population"
    
    total_count = len(df)
    total_selected = int(df["selected_for_outreach"].sum())
    overall_coverage = _safe_div(total_selected, total_count)
    
    is_group = df[group_col] == True
    is_non_group = ~is_group
    
    group_count = int(is_group.sum())
    non_group_count = int(is_non_group.sum())
    
    group_selected = int((is_group & df["selected_for_outreach"]).sum())
    non_group_selected = int((is_non_group & df["selected_for_outreach"]).sum())
    
    group_coverage = _safe_div(group_selected, group_count)
    non_group_coverage = _safe_div(non_group_selected, non_group_count)
    
    # Mathematical definitions
    coverage_gap = abs(group_coverage - overall_coverage)
    coverage_ratio = _safe_div(group_coverage, overall_coverage)
    opportunity_difference = group_coverage - non_group_coverage
    
    # Population weighting
    group_pop_total = float(df.loc[is_group, pop_col].fillna(0).sum()) if pop_col in df.columns else 0.0
    group_pop_reached = float(df.loc[is_group & df["selected_for_outreach"], pop_col].fillna(0).sum()) if pop_col in df.columns else 0.0
    pop_weighted_coverage = _safe_div(group_pop_reached, group_pop_total)
    
    return {
        "group_name": group_col,
        "sample_size": group_count,
        "target_population": int(group_pop_total),
        "reached_population": int(group_pop_reached),
        "group_coverage": group_coverage,
        "overall_coverage": overall_coverage,
        "coverage_gap": coverage_gap,
        "coverage_ratio": coverage_ratio,
        "opportunity_difference": opportunity_difference,
        "pop_weighted_coverage": pop_weighted_coverage
    }
