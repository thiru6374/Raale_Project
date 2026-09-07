"""
src/intelligence/improvement_service.py
"""
import pandas as pd
from typing import List, Dict, Any
from src.services.persistence.improvement_repository import ImprovementRepository
from src.config.settings import settings

class ImprovementService:
    def __init__(self):
        self.repo = ImprovementRepository()
        
    def generate_proposals(self, pipeline_df: pd.DataFrame, changes: List[Dict], alerts: List[Dict]) -> List[Dict]:
        """
        Identify systemic issues and propose configuration changes for human approval.
        """
        proposals = []
        
        # 1. Capacity Exhaustion
        if "selected_for_outreach" in pipeline_df.columns:
            capacity_util = pipeline_df["selected_for_outreach"].sum()
            max_cap = settings.number_of_teams * settings.maximum_visits_per_team
            
            # If capacity is > 95% utilized
            if capacity_util >= max_cap * 0.95:
                # Propose increasing teams
                proposals.append({
                    "trigger_pattern": "CAPACITY_EXHAUSTED",
                    "evidence": f"Capacity utilization is at {capacity_util}/{max_cap} slots.",
                    "affected_component": "number_of_teams",
                    "recommended_change": {"number_of_teams": settings.number_of_teams + 2},
                    "expected_benefit": "Increase high-risk coverage by expanding available outreach teams.",
                    "risk_assessment": "May require additional personnel budget."
                })
                
        # Persist new proposals
        # First, deduplicate (don't propose if one already exists for the same pattern that is PROPOSED or UNDER_REVIEW)
        existing_proposals = self.repo.get_latest_proposals().values()
        active_patterns = [p["trigger_pattern"] for p in existing_proposals if p["status"] in ["PROPOSED", "UNDER_REVIEW"]]
        
        created = []
        for p in proposals:
            if p["trigger_pattern"] not in active_patterns:
                p_id = self.repo.add_proposal(**p)
                p["proposal_id"] = p_id
                created.append(p)
                
        return created
