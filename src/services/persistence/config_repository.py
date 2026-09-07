"""
src/services/persistence/config_repository.py
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.services.persistence.jsonl_store import JSONLStore

class ConfigRepository:
    def __init__(
        self, 
        version_filepath: str = "data/config/settings_versioned.jsonl",
        audit_filepath: str = "data/config/config_audit.jsonl"
    ):
        self.version_store = JSONLStore(version_filepath)
        self.audit_store = JSONLStore(audit_filepath)
        
    def save_version(self, version_data: Dict[str, Any]) -> bool:
        """Saves a new configuration version."""
        if "config_version" not in version_data:
            version_data["config_version"] = f"v_{uuid.uuid4().hex[:8]}"
            
        if "created_at" not in version_data:
            version_data["created_at"] = datetime.utcnow().isoformat() + "Z"
            
        return self.version_store.append(version_data)
        
    def get_all_versions(self) -> List[Dict[str, Any]]:
        return self.version_store.read_all()
        
    def get_version(self, config_version: str) -> Optional[Dict[str, Any]]:
        versions = self.get_all_versions()
        for v in versions:
            if v.get("config_version") == config_version:
                return v
        return None
        
    def get_latest_approved_version(self) -> Optional[Dict[str, Any]]:
        versions = self.get_all_versions()
        # Filter for approved & valid
        approved = [v for v in versions if v.get("approval_status") == "APPROVED" and v.get("validation_status") == "VALID"]
        if not approved:
            return None
        # Sort by creation time
        approved.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return approved[0]
        
    def log_audit_event(self, event_type: str, config_version: str, 
                        actor: str = "SYSTEM", reason: str = "", 
                        previous_version: str = None, new_version: str = None) -> bool:
        """Logs an event in the configuration audit log."""
        record = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "config_version": config_version,
            "event_type": event_type,
            "actor": actor,
            "reason": reason,
            "previous_version": previous_version,
            "new_version": new_version
        }
        return self.audit_store.append(record)
