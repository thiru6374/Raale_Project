"""
src/services/persistence/feedback_repository.py
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any
from src.services.persistence.jsonl_store import JSONLStore

class FeedbackRepository:
    def __init__(self, filepath: str = "data/intelligence/feedback.jsonl"):
        self.store = JSONLStore(filepath)
        
    def save_feedback(self, data: Dict[str, Any]) -> str:
        """Saves a stakeholder feedback record."""
        feedback_id = str(uuid.uuid4())
        
        record = {
            "feedback_id": feedback_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "recommendation_id": data.get("recommendation_id"),
            "pipeline_run_id": data.get("pipeline_run_id"),
            "usefulness_rating": data.get("usefulness_rating"),
            "clarity_rating": data.get("clarity_rating"),
            "feasibility_rating": data.get("feasibility_rating"),
            "comment": data.get("comment"),
            "group_context": data.get("group_context"),
            "submitted_by": data.get("submitted_by", "ANONYMOUS_STAKEHOLDER")
        }
        
        self.store.append(record)
        return feedback_id
        
    def get_all_feedback(self) -> List[Dict[str, Any]]:
        return self.store.read_all()
