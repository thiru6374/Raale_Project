"""
src/services/decision_intelligence_service.py

Final decision intelligence layer for .
Combines risk, optimization, fairness, capacity, and system health into final priorities.
"""
from typing import Dict, Any, List
from src.services.communication_intelligence_service import CommunicationIntelligenceService

class DecisionIntelligenceService:
    @staticmethod
    def generate_final_decisions(
        neighbourhoods: List[Dict[str, Any]],
        system_health_status: str,
        alerts: List[Dict[str, Any]],
        pipeline_run_id: str,
        config_version: str
    ) -> List[Dict[str, Any]]:
        """
        Creates final actionable decisions combining all upstream outputs.
        """
        decisions = []
        
        has_critical_alerts = any(a.get("severity") == "CRITICAL" and a.get("status") != "RESOLVED" for a in alerts)
        
        for nbhd in neighbourhoods:
            # Check for fallback conditions
            fallback = nbhd.get("fallback_status", "NORMAL")
            
            # If system is degraded, provider failed, or critical alerts exist
            if system_health_status == "CRITICAL" or has_critical_alerts:
                fallback = "FALLBACK_ACTIVATED"
                
            # Update the neighbourhood dict before passing to communication service
            nbhd_copy = dict(nbhd)
            nbhd_copy["fallback_status"] = fallback
            
            rec = CommunicationIntelligenceService.generate_recommendation(
                neighbourhood_data=nbhd_copy,
                pipeline_run_id=pipeline_run_id,
                config_version=config_version,
                decision_trace_id=nbhd.get("decision_trace_id", "N/A"),
                active_alerts=alerts
            )
            
            # Apply safe fallback override
            if fallback == "FALLBACK_ACTIVATED":
                rec["priority"] = "MANUAL_REVIEW_REQUIRED"
                rec["recommended_action"] = "Automated recommendation disabled due to system constraints. Manual review required."
                rec["communication_message"]["action"] = "Standard district advisory only until manual review is completed."
                rec["reasoning_summary"] = "Fallback triggered. Original data may be unreliable."
            
            decisions.append(rec)
            
        return decisions
