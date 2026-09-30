import json
from datetime import datetime
import os
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("audit_logger")

class AuditLogger:
    """Provides a permanent, cryptographic-style log of all manual overrides and actions."""
    
    def __init__(self, log_path: str = "data/logs/audit.jsonl"):
        self.log_path = Path(log_path)
        # Ensure directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
    def log_override_event(self, 
                           event_id: str,
                           analysis_id: str,
                           neighbourhood_id: str, 
                           original_decision: bool, 
                           new_decision: bool, 
                           actor: str,
                           role: str,
                           reason: str,
                           comment: str,
                           auth_status: str,
                           system_confidence: float):
        """Appends a structured JSON line to the audit log for an override event."""
        
        payload = {
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action_type": "MANUAL_OVERRIDE",
            "analysis_id": analysis_id,
            "neighbourhood_id": neighbourhood_id,
            "original_decision": original_decision,
            "new_decision": new_decision,
            "actor": actor,
            "role": role,
            "reason": reason,
            "comment": comment,
            "auth_status": auth_status,
            "system_confidence": system_confidence
        }
        
        try:
            with open(self.log_path, 'a', encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
            logger.info(f"Audit log successfully written for event {event_id} by {actor}.")
        except Exception as e:
            logger.error(f"Failed to write to audit log! Overrides MUST NOT proceed without logging. Error: {str(e)}")
            raise IOError("Audit logging failure.") from e

    def log_system_event(self, action_type: str, actor: str, details: dict):
        """Logs general system events like dataset changes or config updates."""
        payload = {
            "event_id": "SYS_" + datetime.utcnow().strftime("%Y%md%H%M%S%f"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action_type": action_type,
            "actor": actor,
            "details": details
        }
        try:
            with open(self.log_path, 'a', encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass

    def read_logs(self):
        """Reads the audit logs for display or verification."""
        if not self.log_path.exists():
            return []
            
        logs = []
        with open(self.log_path, 'r', encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    logs.append(json.loads(line))
        return logs
