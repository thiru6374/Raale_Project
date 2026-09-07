"""
src/intelligence/change_detection.py
"""
import pandas as pd
from typing import Dict, Any, List

class ChangeDetector:
    def detect_changes(self, current_df: pd.DataFrame, previous_df: pd.DataFrame, 
                       current_meta: Dict[str, Any], previous_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detects meaningful changes between current run and previous valid run.
        """
        if current_df is None or previous_df is None:
            return [{"type": "INSUFFICIENT_HISTORY", "message": "Insufficient history for change analysis."}]
            
        changes = []
        
        # 1. High-Risk Areas Change
        def get_high_risk_count(df):
            if "multi_factor_risk_category" in df.columns:
                return len(df[df["multi_factor_risk_category"].isin(["EXTREME", "HIGH"])])
            return 0
            
        curr_hr = get_high_risk_count(current_df)
        prev_hr = get_high_risk_count(previous_df)
        
        if curr_hr > prev_hr:
            changes.append({
                "type": "HIGH_RISK_INCREASE",
                "message": f"High-risk neighbourhoods increased from {prev_hr} to {curr_hr}.",
                "metric": "high_risk_count",
                "current": curr_hr,
                "previous": prev_hr,
                "delta": curr_hr - prev_hr
            })
            
        # 2. Coverage Change
        def get_coverage(df):
            if "multi_factor_risk_category" in df.columns and "selected_for_outreach" in df.columns:
                hr_df = df[df["multi_factor_risk_category"].isin(["EXTREME", "HIGH"])]
                if len(hr_df) == 0:
                    return 0.0
                return len(hr_df[hr_df["selected_for_outreach"] == True]) / len(hr_df)
            return 0.0
            
        curr_cov = get_coverage(current_df)
        prev_cov = get_coverage(previous_df)
        
        if curr_cov < prev_cov - 0.05: # more than 5% drop
            changes.append({
                "type": "COVERAGE_DROP",
                "message": f"High-risk coverage dropped from {prev_cov:.1%} to {curr_cov:.1%}.",
                "metric": "coverage_pct",
                "current": curr_cov,
                "previous": prev_cov,
                "delta": curr_cov - prev_cov
            })
            
        # 3. Provider Change
        curr_provider = current_meta.get("provider_status", "UNKNOWN")
        prev_provider = previous_meta.get("provider_status", "UNKNOWN")
        
        if "FALLBACK" in curr_provider and "FALLBACK" not in prev_provider:
            changes.append({
                "type": "FALLBACK_ACTIVATED",
                "message": "System fell back to synthetic data due to provider failure.",
                "metric": "provider_status",
                "current": curr_provider,
                "previous": prev_provider
            })
            
        return changes
