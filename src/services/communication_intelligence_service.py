"""
src/services/communication_intelligence_service.py

Adaptive communication engine for .
Generates neighbourhood-specific communication recommendations.
"""
from typing import Dict, Any, List
import uuid

class CommunicationIntelligenceService:
    
    @staticmethod
    def generate_recommendation(
        neighbourhood_data: Dict[str, Any],
        pipeline_run_id: str,
        config_version: str,
        decision_trace_id: str,
        active_alerts: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates actionable communication recommendation based on existing data.
        """
        risk = neighbourhood_data.get("multi_factor_risk_category", "LOW")
        temp = neighbourhood_data.get("temperature_c", 30.0)
        vuln = neighbourhood_data.get("vulnerability_index", 0.5)
        service = neighbourhood_data.get("service_access_score", 0.5)
        mobile = neighbourhood_data.get("mobile_population_density", 0.0)
        selected = neighbourhood_data.get("selected_for_outreach", False)
        
        nid = neighbourhood_data.get("neighbourhood_id", "UNKNOWN")
        
        rec_id = str(uuid.uuid4())
        
        # Determine Priority
        if risk == "HIGH" and selected:
            priority = "CRITICAL"
        elif risk == "HIGH":
            priority = "HIGH"
        elif risk == "MEDIUM":
            priority = "MEDIUM"
        else:
            priority = "LOW"
            
        # Determine Recommended Action
        if selected:
            action = "Deploy mobile outreach and establish temporary cooling stations."
        elif risk == "HIGH":
            action = "Monitor closely and prepare secondary outreach teams."
        else:
            action = "No direct intervention required. Rely on general district advisories."
            
        # Level 1 - General Message
        msg_general = "Stay safe during hot weather. Drink water and avoid direct sun."
        
        # Level 2 & 3 - Localized Message
        if risk == "HIGH" and selected:
            if mobile > 0.6:
                msg_localized = f"CRITICAL: {nid} has elevated heat exposure with high mobile population. Outreach teams must visit before peak afternoon heat and provide water/shelter info."
                msg_short = f"Very high heat risk tomorrow in {nid}. Visit nearest support point."
            else:
                msg_localized = f"CRITICAL: {nid} has elevated heat risk and limited service access. Outreach recommended before peak hours."
                msg_short = f"High heat risk in {nid}. Seek cooling centers."
        elif risk == "HIGH":
            msg_localized = f"WARNING: {nid} shows high heat risk but was not selected for primary outreach due to capacity. Target with SMS and local radio warnings."
            msg_short = f"High heat risk in {nid}. Stay hydrated."
        else:
            msg_localized = msg_general
            msg_short = "Routine heat advisory."
            
        # Explanation
        reasoning = []
        if risk == "HIGH": reasoning.append("Elevated heat exposure.")
        if vuln > 0.7: reasoning.append("High vulnerability indicators.")
        if service < 0.4: reasoning.append("Limited service access.")
        if mobile > 0.6: reasoning.append("Significant mobile population.")
        if selected: reasoning.append("Selected by optimizer for outreach.")
        
        explanation = " ".join(reasoning) if reasoning else "Routine conditions."
        
        return {
            "recommendation_id": rec_id,
            "neighbourhood_id": nid,
            "risk_level": risk,
            "priority": priority,
            "recommended_action": action,
            "communication_message": {
                "short": msg_short,
                "action": msg_localized,
                "explanation": explanation,
                "general_baseline": msg_general
            },
            "recommended_timing": "Before 11:00 AM" if priority in ["CRITICAL", "HIGH"] else "Routine",
            "reasoning_summary": explanation,
            "confidence": "HIGH" if neighbourhood_data.get("fallback_status") != "FALLBACK_ACTIVATED" else "LOW",
            "fallback_status": neighbourhood_data.get("fallback_status", "NORMAL"),
            "pipeline_run_id": pipeline_run_id,
            "config_version": config_version,
            "decision_trace_id": decision_trace_id
        }
