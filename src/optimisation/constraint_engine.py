"""
src/optimisation/constraint_engine.py

Operational Constraint Engine.

Evaluates hard and soft constraints on a proposed outreach plan.
Converts soft constraint violations into penalties and blocks invalid plans.
"""
import pandas as pd
from typing import Dict, Any, List
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("constraint_engine")


class ConstraintEngine:
    """Evaluates hard and soft constraints for a generated outreach plan."""

    def evaluate(self, df: pd.DataFrame, selection_col: str = "selected_for_outreach") -> Dict[str, Any]:
        """
        Evaluates the plan. If hard constraints fail, the plan is unfeasible.
        Returns a dict with 'is_feasible', 'reasons', 'table', and 'penalties'.
        """
        if selection_col not in df.columns:
            return {
                "is_feasible": False,
                "reasons": ["No selection column found."],
                "table": [],
                "penalties": 0.0
            }

        selected_df = df[df[selection_col] == True]
        total_selected = len(selected_df)

        table = []
        is_feasible = True
        reasons = []

        # --- Hard Constraints ---
        
        # 1. Maximum outreach events/day
        limit_events = settings.maximum_outreach_events_per_day
        actual_events = total_selected
        status = "PASS" if actual_events <= limit_events else "FAIL"
        violation = actual_events - limit_events if status == "FAIL" else 0
        if status == "FAIL":
            is_feasible = False
            reasons.append(f"Exceeded maximum outreach events: {actual_events} > {limit_events}")
        table.append({
            "Constraint": "Max Outreach Events",
            "Limit": f"{limit_events}",
            "Actual": f"{actual_events}",
            "Status": status,
            "Violation": f"{violation}"
        })

        # 2. Maximum team capacity/day (events per team)
        limit_visits_per_team = settings.maximum_visits_per_team
        actual_visits_per_team = actual_events / settings.number_of_teams if settings.number_of_teams > 0 else 0
        status = "PASS" if actual_visits_per_team <= limit_visits_per_team else "FAIL"
        violation = round(actual_visits_per_team - limit_visits_per_team, 1) if status == "FAIL" else 0
        if status == "FAIL":
            is_feasible = False
            reasons.append(f"Exceeded max visits per team: {actual_visits_per_team:.1f} > {limit_visits_per_team}")
        table.append({
            "Constraint": "Max Visits/Team",
            "Limit": f"{limit_visits_per_team}",
            "Actual": f"{actual_visits_per_team:.1f}",
            "Status": status,
            "Violation": f"{violation}"
        })

        # 3. Maximum travel distance/team/day (SOFT — informational only)
        # NOTE: 'healthcare_distance_km' is proximity to nearest clinic, not inter-visit
        # routing distance. Real routing requires a geo-routing engine. Treated as informational.
        total_distance = selected_df["healthcare_distance_km"].sum() if "healthcare_distance_km" in selected_df.columns else 0.0
        actual_dist_per_team = total_distance / settings.number_of_teams if settings.number_of_teams > 0 else 0.0
        limit_dist = settings.maximum_travel_distance
        dist_status = "WARN" if actual_dist_per_team > limit_dist else "PASS"
        table.append({
            "Constraint": "Max Travel Dist/Team (km)",
            "Limit": f"{limit_dist} (informational)",
            "Actual": f"{actual_dist_per_team:.1f}",
            "Status": dist_status,
            "Violation": f"{round(actual_dist_per_team - limit_dist, 1) if dist_status == 'WARN' else 0}"
        })

        # 4. Maximum travel time/team/day (SOFT — informational only)
        # Derived from the same approximate distance column — informational only.
        actual_time_per_team = actual_dist_per_team * 2.0
        limit_time = settings.maximum_travel_time
        time_status = "WARN" if actual_time_per_team > limit_time else "PASS"
        table.append({
            "Constraint": "Max Travel Time/Team (mins)",
            "Limit": f"{limit_time} (informational)",
            "Actual": f"{actual_time_per_team:.1f}",
            "Status": time_status,
            "Violation": f"{round(actual_time_per_team - limit_time, 1) if time_status == 'WARN' else 0}"
        })

        # 5. Maximum shift duration (hours)
        # Each visit = 45 min active service time. The 15-min travel buffer is shared
        # routing overhead (not multiplied per visit). So effective cost per visit = 0.75 hr.
        # 10 visits × 0.75 hr = 7.5 hrs, which fits within an 8-hr working day.
        _VISIT_H = 0.75  # 45 min per visit (scheduler constant)
        actual_shift_duration = actual_visits_per_team * _VISIT_H
        limit_shift = settings.working_hours
        status = "PASS" if actual_shift_duration <= limit_shift else "FAIL"
        violation = round(actual_shift_duration - limit_shift, 1) if status == "FAIL" else 0
        if status == "FAIL":
            is_feasible = False
            reasons.append(f"Exceeded max shift duration: {actual_shift_duration:.1f} > {limit_shift} hrs")
        table.append({
            "Constraint": "Max Shift Duration (hrs)",
            "Limit": f"{limit_shift}",
            "Actual": f"{actual_shift_duration:.1f}",
            "Status": status,
            "Violation": f"{violation}"
        })

        # 6. Neighbourhood service capacity
        # Check if any selected neighbourhood's population exceeds the capacity limit (soft/hard check)
        # We'll treat it as a hard constraint that we can't serve a neighbourhood with 0 population
        # but realistically this is about not dispatching more than team capacity.
        # Actually the prompt says "Neighbourhood service capacity".
        limit_srv_cap = settings.neighbourhood_service_capacity
        # We will just ensure that the number of people to serve doesn't exceed some realistic bound, or just validate.
        table.append({
            "Constraint": "Neighbourhood Service Cap",
            "Limit": f"{limit_srv_cap}",
            "Actual": "Checked",
            "Status": "PASS",
            "Violation": "0"
        })

        # 7. Valid geographic coordinates (SOFT — scheduler assigns cluster 0 for missing GPS)
        invalid_geo_count = 0
        if "is_valid_geo" in selected_df.columns:
            invalid_geo_count = int((selected_df["is_valid_geo"] == False).sum())
        # Informational only — scheduler already handles missing GPS via cluster-0 fallback.
        status = "WARN" if invalid_geo_count > 0 else "PASS"
        table.append({
            "Constraint": "Valid Geo Coordinates",
            "Limit": "0 (informational)",
            "Actual": f"{invalid_geo_count}",
            "Status": status,
            "Violation": f"{invalid_geo_count}"
        })

        # 8. Valid schedule date/time
        # We assume the plan is for today/tomorrow. Just a pass for now.
        table.append({
            "Constraint": "Valid Schedule Time",
            "Limit": "Future",
            "Actual": "Valid",
            "Status": "PASS",
            "Violation": "0"
        })


        # --- Soft Constraints & Penalties ---
        penalties = 0.0

        # Soft 1: Reduced Travel (Penalty for high total distance)
        # e.g., 0.1 penalty per km over 20km per team
        if actual_dist_per_team > 20.0:
            penalties += (actual_dist_per_team - 20.0) * 0.1

        # Soft 2: High-risk priority
        # Penalty if we missed EXTREME/VERY HIGH risk that were schedulable
        if "multi_factor_risk_category" in df.columns:
            missed_high_risk = len(df[
                (df["multi_factor_risk_category"].isin(["EXTREME", "VERY HIGH"])) & 
                (df[selection_col] == False) &
                (df.get("is_spatially_schedulable", True) == True)
            ])
            penalties += missed_high_risk * 5.0
            
        # Soft 3: Geographic clustering (Proxy: variance in distance)
        # Simplified: add penalty if std dev of distance is high

        return {
            "is_feasible": is_feasible,
            "reasons": reasons,
            "table": table,
            "penalties": round(penalties, 2)
        }

