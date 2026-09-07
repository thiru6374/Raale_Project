import json
from datetime import datetime
import os
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("audit_logger")

class AuditLogger:
    """Provides a permanent, cryptographic-style log of all manual overrides."""
    
    def __init__(self, log_path: str = "logs/audit.jsonl"):
        self.log_path = Path(log_path)
        # Ensure directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
    def log_override(self, 
                     user_id: str, 
                     neighbourhood_id: str, 
                     original_decision: bool, 
                     new_decision: bool, 
                     reason: str):
        """Appends a structured JSON line to the audit log."""
        
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": user_id,
            "action": "OVERRIDE_OUTREACH_SELECTION",
            "neighbourhood_id": neighbourhood_id,
            "original_decision": original_decision,
            "new_decision": new_decision,
            "reason": reason
        }
        
        try:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(payload) + "\n")
            logger.info(f"Audit log successfully written for neighbourhood {neighbourhood_id} by {user_id}.")
        except Exception as e:
            logger.error(f"Failed to write to audit log! Overrides MUST NOT proceed without logging. Error: {str(e)}")
            raise IOError("Audit logging failure.") from e
            
    def read_logs(self):
        """Reads the audit logs for display or verification."""
        if not self.log_path.exists():
            return []
            
        logs = []
        with open(self.log_path, 'r') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        return logs
