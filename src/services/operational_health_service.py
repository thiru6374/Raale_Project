"""
src/services/operational_health_service.py

Monitors overall system health for .
"""
from typing import Dict, Any, List

class OperationalHealthService:
    
    @staticmethod
    def get_overall_health(
        pipeline_status: str,
        provider_status: str,
        freshness_status: str,
        security_status: str,
        persistence_status: str
    ) -> Dict[str, Any]:
        """
        Creates a unified operational health score.
        """
        degraded_components = []
        
        if pipeline_status != "HEALTHY":
            degraded_components.append({"component": "Pipeline", "status": pipeline_status, "reason": "Pipeline execution failed or is degraded.", "action": "Check pipeline logs."})
        if provider_status != "HEALTHY":
            degraded_components.append({"component": "Data Provider", "status": provider_status, "reason": "Provider is unreachable.", "action": "Verify API connections."})
        if freshness_status in ["STALE", "UNAVAILABLE"]:
            degraded_components.append({"component": "Data Freshness", "status": freshness_status, "reason": "Data is out of date.", "action": "Trigger manual refresh."})
        if security_status != "HEALTHY":
            degraded_components.append({"component": "Security", "status": security_status, "reason": "Security checks failing.", "action": "Review access logs."})
        if persistence_status != "HEALTHY":
            degraded_components.append({"component": "Persistence", "status": persistence_status, "reason": "Cannot write to storage.", "action": "Check disk space and permissions."})

        overall = "HEALTHY"
        if len(degraded_components) > 0:
            if any(c["status"] in ["CRITICAL", "FAILED", "UNAVAILABLE"] for c in degraded_components):
                overall = "CRITICAL"
            elif any(c["status"] == "STALE" for c in degraded_components):
                overall = "DEGRADED"
            else:
                overall = "WARNING"
                
        return {
            "overall_status": overall,
            "degraded_components": degraded_components
        }
