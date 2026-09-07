"""
src/services/persistence/improvement_repository.py
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.services.persistence.jsonl_store import JSONLStore

class ImprovementRepository:
    def __init__(self, filepath: str = "data/intelligence/improvement_proposals.jsonl"):
        self.store = JSONLStore(filepath)
        
    def add_proposal(self, trigger_pattern: str, evidence: str, affected_component: str,
                     recommended_change: Dict[str, Any], expected_benefit: str, 
                     risk_assessment: str, requires_human_approval: bool = True) -> str:
        
        proposal_id = str(uuid.uuid4())
        
        record = {
            "proposal_id": proposal_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "PROPOSED",
            "trigger_pattern": trigger_pattern,
            "evidence": evidence,
            "affected_component": affected_component,
            "recommended_change": recommended_change,
            "expected_benefit": expected_benefit,
            "risk_assessment": risk_assessment,
            "requires_human_approval": requires_human_approval
        }
        
        self.store.append(record)
        return proposal_id
        
    def get_all_proposals(self) -> List[Dict[str, Any]]:
        return self.store.read_all()
        
    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        proposals = self.get_all_proposals()
        for p in proposals:
            if p.get("proposal_id") == proposal_id:
                return p
        return None
        
    def update_proposal_status(self, proposal_id: str, new_status: str, 
                               decision_reason: str = None, related_config_version: str = None) -> bool:
        """
        Since this is an append-only/read-all system without random access write, 
        we will simulate an update by appending a new record with the same ID, 
        and when reading, we merge them or take the latest.
        """
        existing = self.get_proposal(proposal_id)
        if not existing:
            return False
            
        # Create a new updated record
        updated = existing.copy()
        updated["status"] = new_status
        if decision_reason:
            updated["decision_reason"] = decision_reason
        if related_config_version:
            updated["related_config_version"] = related_config_version
        updated["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # In a real database we'd update. Here we just overwrite the whole file 
        # or append and read the latest. For simplicity, let's append and filter on read.
        self.store.append(updated)
        return True
        
    def get_latest_proposals(self) -> Dict[str, Dict[str, Any]]:
        """Returns a dict of proposal_id -> latest state"""
        records = self.store.read_all()
        # Sort by creation/update time
        records.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")))
        
        latest = {}
        for r in records:
            latest[r["proposal_id"]] = r
            
        return latest
