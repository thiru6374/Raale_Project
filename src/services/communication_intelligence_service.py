"""
src/services/communication_intelligence_service.py

Adaptive communication engine for Phase 11.
Generates neighbourhood-specific communication recommendations
from actual neighbourhood risk and population characteristics.
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
        Fields requested in Phase 11:
        - communication priority
        - target audience
        - risk level
        - urgency
        - recommended timing
        - communication channel
        - suggested message
        - outreach connection
        """
        risk = neighbourhood_data.get("multi_factor_risk_category", "LOW")
        temp = neighbourhood_data.get("temperature_c", 30.0)
        vuln = neighbourhood_data.get("vulnerability_index", 0.0)
        dist = neighbourhood_data.get("healthcare_distance_km", 0.0)
        mobile = neighbourhood_data.get("mobile_population", 0)
        selected = neighbourhood_data.get("selected_for_outreach", False)
        nid = neighbourhood_data.get("neighbourhood_id", "UNKNOWN")
        name = neighbourhood_data.get("neighbourhood_name", nid)
        risk_score = neighbourhood_data.get("multi_factor_risk_score", 0.0)
        
        rec_id = str(uuid.uuid4())
        
        # Communication Priority, Risk Level, Urgency, Timing
        if risk in ["EXTREME", "VERY HIGH"]:
            priority = "HIGH"
            urgency = "Immediate / Emergency"
            timing = "Morning (Before 10 AM)"
        elif risk == "HIGH":
            priority = "HIGH"
            urgency = "High"
            timing = "Morning (Before 10 AM) or Evening"
        elif risk == "MODERATE":
            priority = "MODERATE"
            urgency = "Standard"
            timing = "Afternoon / Evening"
        else:
            priority = "LOW"
            urgency = "Low"
            timing = "Any time"

        # Target Audience & Channel
        audiences = ["General Public"]
        channels = ["Community Boards", "Local Radio"]
        
        if vuln > 0.6:
            audiences.append("Vulnerable Populations")
            channels.append("Door-to-door (if selected)")
            
        elderly = neighbourhood_data.get('elderly_population_percent', 0.0)
        if elderly > 0.15:
            audiences.append("Elderly Residents")
            channels.append("Community Center Flyers")
            
        if mobile > 100:
            audiences.append("Mobile Workers")
            channels.append("SMS Alerts")
            channels.append("Transit Hub Displays")

        # Outreach Connection
        if selected:
            outreach_conn = "In-person outreach scheduled. Align messaging with deployed team."
            action = "Deploy mobile outreach and establish temporary cooling stations."
        elif risk in ['EXTREME', 'VERY HIGH', 'HIGH']:
            outreach_conn = "Waitlisted due to capacity. High reliance on broadcast communication."
            action = "Monitor closely and prepare secondary outreach teams."
        else:
            outreach_conn = "No active outreach scheduled. Standard monitoring."
            action = "No direct intervention required. Rely on general district advisories."
            
        # Suggested Message
        msg = f"Public Health Advisory for {name}: {risk} heat risks today. "
        
        green_cover = neighbourhood_data.get('green_cover_percent', 1.0)
        if green_cover < 0.15:
            msg += "Due to low tree canopy, avoid outdoor surfaces which will retain extreme heat. Seek air-conditioned indoor cooling centers. "
        else:
            msg += "Stay in shaded areas if you must be outside. "
            
        if dist > 3.0:
            msg += "Medical facilities are far from your location. Stay hydrated and call for emergency transit immediately at the first sign of heat illness. "
        else:
            msg += "Stay hydrated and seek local medical help if you experience nausea or dizziness. "
            
        msg += "\nDisclaimer: This is a preventative advisory, not a medically validated diagnostic alert."
        
        # Determine Decision-level priority
        if risk in ["EXTREME", "VERY HIGH"] and selected:
            decision_priority = "CRITICAL"
        elif risk in ["EXTREME", "VERY HIGH", "HIGH"]:
            decision_priority = "HIGH"
        elif risk == "MODERATE":
            decision_priority = "MEDIUM"
        else:
            decision_priority = "LOW"
            
        # Explanation
        reasoning = []
        if risk in ["EXTREME", "VERY HIGH", "HIGH"]: reasoning.append(f"Elevated heat exposure (Risk: {risk}).")
        if vuln > 0.6: reasoning.append("High vulnerability indicators.")
        if dist > 3.0: reasoning.append("Limited healthcare access.")
        if mobile > 100: reasoning.append("Significant mobile population.")
        if selected: reasoning.append("Selected by optimizer for outreach.")
        explanation = " ".join(reasoning) if reasoning else "Routine conditions."

        return {
            "recommendation_id": rec_id,
            "neighbourhood_id": nid,
            "risk_level": risk,
            "priority": decision_priority,
            "communication_priority": priority,
            "target_audience": ", ".join(audiences),
            "urgency": urgency,
            "recommended_timing": timing,
            "communication_channel": ", ".join(channels),
            "outreach_connection": outreach_conn,
            "recommended_action": action,
            "communication_message": {
                "short": f"{risk} heat risk in {name}.",
                "action": msg.strip(),
                "explanation": explanation,
                "general_baseline": "Stay safe during hot weather. Drink water and avoid direct sun."
            },
            "reasoning_summary": explanation,
            "confidence": "HIGH" if neighbourhood_data.get("fallback_status") != "FALLBACK_ACTIVATED" else "LOW",
            "fallback_status": neighbourhood_data.get("fallback_status", "NORMAL"),
            "pipeline_run_id": pipeline_run_id,
            "config_version": config_version,
            "decision_trace_id": decision_trace_id
        }
