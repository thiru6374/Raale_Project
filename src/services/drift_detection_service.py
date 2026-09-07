"""
src/services/drift_detection_service.py

Detects drift in recommendations and fairness metrics between pipeline runs.
"""
from typing import Dict, Any, List

class DriftDetectionService:
    
    @staticmethod
    def detect_recommendation_drift(
        current_recs: List[Dict[str, Any]], 
        reference_recs: List[Dict[str, Any]],
        threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        Detects drift in risk level distribution and coverage.
        """
        if not reference_recs:
            return {"status": "STABLE", "explanation": "No reference run available for comparison."}
            
        cur_high = sum(1 for r in current_recs if r.get("risk_level") == "HIGH")
        ref_high = sum(1 for r in reference_recs if r.get("risk_level") == "HIGH")
        
        cur_total = len(current_recs)
        ref_total = len(reference_recs)
        
        if ref_total == 0 or cur_total == 0:
            return {"status": "STABLE", "explanation": "Insufficient data for drift calculation."}
            
        cur_pct = cur_high / cur_total
        ref_pct = ref_high / ref_total
        
        diff = abs(cur_pct - ref_pct)
        
        if diff > threshold * 2:
            status = "SIGNIFICANT CHANGE"
            explanation = f"High-risk neighbourhood proportion changed significantly from {ref_pct:.1%} to {cur_pct:.1%}."
        elif diff > threshold:
            status = "MINOR CHANGE"
            explanation = f"Minor shift in high-risk distribution detected ({diff:.1%} difference)."
        else:
            status = "STABLE"
            explanation = "Risk distributions are stable."
            
        return {
            "status": status,
            "explanation": explanation,
            "current_high_risk_count": cur_high,
            "reference_high_risk_count": ref_high,
            "difference": diff
        }

    @staticmethod
    def detect_fairness_drift(
        current_fairness: Dict[str, Any],
        reference_fairness: Dict[str, Any],
        threshold: float = 0.05
    ) -> Dict[str, Any]:
        """
        Detects drift in fairness gaps between groups.
        """
        if not current_fairness or not reference_fairness:
            return {"status": "INSUFFICIENT DATA", "explanation": "Fairness data missing."}
            
        cur_gap = current_fairness.get("disparity", 0.0)
        ref_gap = reference_fairness.get("disparity", 0.0)
        
        diff = cur_gap - ref_gap
        
        if diff > threshold:
            status = "THRESHOLD EXCEEDED"
            explanation = f"Fairness gap has worsened by {diff:.3f} compared to reference."
        elif diff <= -threshold:
            status = "IMPROVED"
            explanation = f"Fairness gap has improved by {abs(diff):.3f} compared to reference."
        else:
            status = "WITHIN THRESHOLD"
            explanation = "Fairness metrics are stable."
            
        return {
            "status": status,
            "explanation": explanation,
            "current_gap": cur_gap,
            "reference_gap": ref_gap,
            "difference": diff
        }
