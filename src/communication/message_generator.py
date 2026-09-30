import json
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("communication_planner")

class MessageGenerator:
    """Generates comprehensive communication plans for neighbourhoods."""

    def generate_messages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Appends a 'communication_plan' column (JSON string) and a 'localised_advisory'
        column for backward compatibility.
        """
        logger.info("Generating neighbourhood communication plans...")
        result_df = df.copy()
        
        plans = []
        advisories = []

        for _, row in result_df.iterrows():
            is_selected = row.get('selected_for_outreach', False)
            name = row.get('neighbourhood_name', 'your area')
            risk_cat = row.get('multi_factor_risk_category', 'UNKNOWN')
            risk_score = float(row.get('multi_factor_risk_score', 0.0))
            
            # Determine Communication Priority
            if risk_score >= 0.75 or risk_cat in ['EXTREME', 'VERY HIGH']:
                comm_priority = "HIGH"
                urgency = "Immediate / Emergency"
                timing = "Morning (Before 10 AM)"
            elif risk_score >= 0.50 or risk_cat == 'HIGH':
                comm_priority = "HIGH"
                urgency = "High"
                timing = "Morning (Before 10 AM) or Evening"
            elif risk_score >= 0.25 or risk_cat == 'MODERATE':
                comm_priority = "MODERATE"
                urgency = "Standard"
                timing = "Afternoon / Evening"
            else:
                comm_priority = "LOW"
                urgency = "Low"
                timing = "Any time"

            # Determine Target Audience & Channel
            audiences = ["General Public"]
            channels = ["Community Boards", "Local Radio"]
            
            vuln_idx = row.get('vulnerability_index')
            if pd.notna(vuln_idx) and vuln_idx > 0.6:
                audiences.append("Vulnerable Populations")
                channels.append("Door-to-door (if selected)")
                
            elderly = row.get('elderly_population_percent')
            if pd.notna(elderly) and elderly > 0.15:
                audiences.append("Elderly Residents")
                channels.append("Community Center Flyers")
                
            mobile = row.get('mobile_population', 0)
            if pd.notna(mobile) and mobile > 100:
                audiences.append("Mobile Workers")
                channels.append("SMS Alerts")
                channels.append("Transit Hub Displays")

            # Determine Outreach Connection
            if is_selected:
                outreach_conn = "In-person outreach scheduled. Align messaging with deployed team."
            elif risk_cat in ['EXTREME', 'VERY HIGH', 'HIGH']:
                outreach_conn = "Waitlisted due to capacity. High reliance on broadcast communication."
            else:
                outreach_conn = "No active outreach scheduled. Standard monitoring."

            # Construct Suggested Message
            msg = f"Public Health Advisory for {name}: {risk_cat} heat risks today. "
            
            green_cover = row.get('green_cover_percent')
            if pd.notna(green_cover) and green_cover < 0.15:
                msg += "Due to low tree canopy, avoid outdoor surfaces which will retain extreme heat. Seek air-conditioned indoor cooling centers. "
            else:
                msg += "Stay in shaded areas if you must be outside. "
                
            distance = row.get('healthcare_distance_km')
            if pd.notna(distance) and distance > 3.0:
                msg += "Medical facilities are far from your location. Stay hydrated and call for emergency transit immediately at the first sign of heat illness. "
            else:
                msg += "Stay hydrated and seek local medical help if you experience nausea or dizziness. "
                
            msg += "\nDisclaimer: This is a preventative advisory, not a medically validated diagnostic alert."

            plan = {
                "communication_priority": comm_priority,
                "target_audience": ", ".join(audiences),
                "risk_level": risk_cat,
                "urgency": urgency,
                "recommended_timing": timing,
                "communication_channel": ", ".join(channels),
                "suggested_message": msg.strip(),
                "outreach_connection": outreach_conn
            }
            
            plans.append(json.dumps(plan))
            advisories.append(msg.strip())

        result_df['communication_plan'] = plans
        result_df['localised_advisory'] = advisories
        return result_df
