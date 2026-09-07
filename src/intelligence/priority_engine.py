"""
src/intelligence/priority_engine.py
"""
import pandas as pd
from typing import List, Dict, Any

class PriorityEngine:
    """Prioritizes which generated recommendations require stakeholder attention."""
    
    def prioritize_decisions(self, df: pd.DataFrame, fairness_warnings: List[Dict]) -> pd.DataFrame:
        if df is None or df.empty:
            return df
            
        df_out = df.copy()
        
        # Initialize
        df_out["decision_priority"] = "PRIORITY 4 — INFORMATIONAL"
        df_out["priority_reason"] = ""
        
        # Groups with fairness warnings
        fairness_groups = [w.get("group") for w in fairness_warnings if w.get("group")]
        
        for idx, row in df_out.iterrows():
            priority = 4
            reasons = []
            
            is_hr = row.get("multi_factor_risk_category") in ["EXTREME", "HIGH"]
            selected = row.get("selected_for_outreach", False)
            invalid_geo = not row.get("is_valid_geo", True)
            
            if is_hr and not selected:
                # High risk but uncovered -> Needs attention
                priority = min(priority, 2)
                reasons.append("High risk area left uncovered by optimization.")
                
            if is_hr and invalid_geo:
                # High risk but invalid geo -> Manual review immediately
                priority = 1
                reasons.append("High risk area requires manual location verification.")
                
            # Check fairness impact
            for g in fairness_groups:
                if row.get(g) == True and not selected and is_hr:
                    priority = 1
                    reasons.append(f"Uncovered high-risk area belongs to underserved group ({g}).")
                    
            if row.get("fallback_status") == "MANUAL_REVIEW":
                priority = min(priority, 2)
                if "Requires manual review" not in reasons:
                    reasons.append("Requires manual review.")
                    
            # Set values
            priority_str = {
                1: "PRIORITY 1 — IMMEDIATE ATTENTION",
                2: "PRIORITY 2 — HIGH PRIORITY",
                3: "PRIORITY 3 — MONITOR",
                4: "PRIORITY 4 — INFORMATIONAL"
            }[priority]
            
            df_out.at[idx, "decision_priority"] = priority_str
            df_out.at[idx, "priority_reason"] = " | ".join(reasons) if reasons else "Routine operational result."
            
        return df_out
