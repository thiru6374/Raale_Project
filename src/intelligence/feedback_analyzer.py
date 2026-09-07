"""
src/intelligence/feedback_analyzer.py
"""
import pandas as pd
from typing import List, Dict, Any
from src.services.persistence.feedback_repository import FeedbackRepository

class FeedbackAnalyzer:
    def __init__(self):
        self.repo = FeedbackRepository()
        
    def analyze_feedback(self) -> Dict[str, Any]:
        """Analyzes aggregated feedback."""
        records = self.repo.get_all_feedback()
        if not records or len(records) < 5:
            return {"status": "INSUFFICIENT FEEDBACK FOR RELIABLE ANALYSIS"}
            
        df = pd.DataFrame(records)
        
        # Calculate rates based on Yes/Partially/No
        # Let's assume standard ratings are mapping: Yes=1.0, Partially=0.5, No=0.0
        # If they are strings:
        def calc_score(series):
            # mapping strings to scores
            mapping = {"Yes": 1.0, "Partially": 0.5, "No": 0.0}
            mapped = series.map(mapping)
            return mapped.mean() if not mapped.empty else 0.0
            
        usefulness = calc_score(df["usefulness_rating"])
        clarity = calc_score(df["clarity_rating"])
        feasibility = calc_score(df["feasibility_rating"])
        
        analysis = {
            "status": "SUCCESS",
            "total_responses": len(df),
            "recommendation_acceptance_rate": usefulness,
            "explanation_clarity_score": clarity,
            "operational_feasibility_score": feasibility,
            "bias_analysis": self._analyze_bias(df)
        }
        return analysis
        
    def _analyze_bias(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Test whether feedback acceptance differs across relevant groups."""
        # Check if group_context exists in the feedback records
        if "group_context" not in df.columns:
            return {"status": "INSUFFICIENT GROUP DATA"}
            
        bias_res = {}
        target_groups = ["group_mobile", "group_low_service_access"]
        
        for g in target_groups:
            group_df = df[df["group_context"].apply(lambda x: isinstance(x, dict) and x.get(g) == True)]
            non_group_df = df[df["group_context"].apply(lambda x: not isinstance(x, dict) or x.get(g) != True)]
            
            if len(group_df) < 3 or len(non_group_df) < 3:
                bias_res[g] = "INSUFFICIENT SAMPLE SIZE"
                continue
                
            # Compare usefulness
            mapping = {"Yes": 1.0, "Partially": 0.5, "No": 0.0}
            g_score = group_df["usefulness_rating"].map(mapping).mean()
            ng_score = non_group_df["usefulness_rating"].map(mapping).mean()
            
            bias_res[g] = {
                "group_acceptance": g_score,
                "non_group_acceptance": ng_score,
                "gap": ng_score - g_score
            }
            
        return bias_res
