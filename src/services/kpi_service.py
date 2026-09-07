"""
src/services/kpi_service.py

KPI calculation service.
"""
from typing import Dict, Any, List

class KPIService:
    @staticmethod
    def calculate_kpis(
        recommendations: List[Dict[str, Any]],
        outcome_status_map: Dict[str, str],
        fairness_results: Dict[str, Any],
        system_health: str,
        capacity_used: int,
        capacity_total: int
    ) -> Dict[str, Any]:
        """Calculates final KPIs."""
        
        total_recs = len(recommendations)
        high_risk_areas = [r for r in recommendations if r.get("risk_level") == "HIGH"]
        total_high_risk = len(high_risk_areas)
        
        # Risk Coverage Rate
        reached = sum(1 for r in high_risk_areas if r.get("priority") in ["CRITICAL", "HIGH"])
        risk_coverage = reached / total_high_risk if total_high_risk > 0 else 1.0
        
        # Capacity Utilization
        cap_util = capacity_used / capacity_total if capacity_total > 0 else 0.0
        
        # Action Completion Rate
        completed = sum(1 for status in outcome_status_map.values() if status == "COMPLETED")
        planned = sum(1 for status in outcome_status_map.values() if status in ["PLANNED", "IN_PROGRESS", "COMPLETED"])
        completion_rate = completed / planned if planned > 0 else 0.0
        
        # Recommendation Acceptance Rate
        accepted = sum(1 for status in outcome_status_map.values() if status in ["ACKNOWLEDGED", "IN_PROGRESS", "COMPLETED", "PLANNED"])
        acceptance_rate = accepted / total_recs if total_recs > 0 else 0.0
        
        # Trust/Fallback Rate
        fallback_recs = sum(1 for r in recommendations if r.get("fallback_status") == "FALLBACK_ACTIVATED")
        fallback_rate = fallback_recs / total_recs if total_recs > 0 else 0.0
        trust_rate = 1.0 - fallback_rate
        
        # Fairness Gap
        fairness_gap = 0.0
        if fairness_results and "disparity" in fairness_results:
            fairness_gap = fairness_results["disparity"]
            
        return {
            "risk_coverage_rate": risk_coverage,
            "capacity_utilization": cap_util,
            "action_completion_rate": completion_rate,
            "recommendation_acceptance_rate": acceptance_rate,
            "system_trust_rate": trust_rate,
            "fallback_rate": fallback_rate,
            "fairness_gap": fairness_gap,
            "system_health_status": system_health,
            "total_recommendations": total_recs,
            "missed_high_risk_areas": total_high_risk - reached
        }
