"""
src/services/outcome_tracking_service.py

Outcome tracking for recommendations.
"""
from typing import Dict, Any, List
from datetime import datetime
from src.services.persistence.jsonl_store import JSONLStore
import os

OUTCOMES_FILE = "data/intelligence/outcomes.jsonl"

class OutcomeTrackingService:
    def __init__(self, filepath: str = OUTCOMES_FILE):
        self.store = JSONLStore(filepath)
        
    def log_recommendation_generated(self, rec: Dict[str, Any]) -> None:
        """Logs initial recommendation generation."""
        record = {
            "recommendation_id": rec["recommendation_id"],
            "neighbourhood_id": rec["neighbourhood_id"],
            "status": "GENERATED",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "priority": rec["priority"],
            "pipeline_run_id": rec.get("pipeline_run_id", "")
        }
        self.store.append(record)
        
    def update_status(self, recommendation_id: str, status: str, actor: str = "SYSTEM", reason: str = "") -> None:
        """Updates the status of a recommendation."""
        valid_statuses = {"GENERATED", "PLANNED", "ACKNOWLEDGED", "IN_PROGRESS", "COMPLETED", "NOT_COMPLETED", "CANCELLED", "EVALUATED"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")
            
        record = {
            "recommendation_id": recommendation_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor": actor,
            "reason": reason
        }
        self.store.append(record)
        
    def get_latest_status_map(self) -> Dict[str, str]:
        """Returns a map of recommendation_id to its latest status."""
        records = self.store.read_all()
        status_map = {}
        for r in records:
            status_map[r["recommendation_id"]] = r["status"]
        return status_map
        
    def get_all_records(self) -> List[Dict[str, Any]]:
        return self.store.read_all()
