"""
src/services/capacity_pressure_service.py

Monitors outreach capacity and identifies unmet critical needs.
"""
from typing import Dict, Any, List

class CapacityPressureService:
    @staticmethod
    def evaluate_capacity(
        available_capacity: int,
        planned_actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates capacity utilization against planned high-priority actions.
        """
        critical_uncovered = []
        
        # High/Critical risk areas
        target_areas = [a for a in planned_actions if a.get("risk_level") == "HIGH"]
        
        used_capacity = 0
        for area in target_areas:
            if used_capacity < available_capacity:
                used_capacity += 1
            else:
                critical_uncovered.append(area["neighbourhood_id"])
                
        remaining = available_capacity - used_capacity
        
        if len(critical_uncovered) > 0:
            state = "INSUFFICIENT_CAPACITY"
        elif used_capacity == available_capacity:
            state = "CAPACITY_PRESSURE"
        elif used_capacity >= available_capacity * 0.8:
            state = "HIGH_UTILIZATION"
        else:
            state = "NORMAL"
            
        return {
            "available_capacity": available_capacity,
            "planned_capacity": len(target_areas),
            "used_capacity": used_capacity,
            "remaining_capacity": remaining,
            "critical_uncovered_areas": critical_uncovered,
            "estimated_capacity_gap": len(critical_uncovered),
            "status": state
        }
