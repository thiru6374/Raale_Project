"""
src/services/persistence/alert_repository.py
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.services.persistence.jsonl_store import JSONLStore

class AlertRepository:
    def __init__(self, filepath: str = "data/intelligence/alerts.jsonl"):
        self.store = JSONLStore(filepath)
        
    def add_event(self, event_type: str, severity: str, category: str, 
                  evidence: str, recommended_action: str, pipeline_run_id: str = None, 
                  alert_id: str = None, actor: str = "SYSTEM", reason: str = None) -> str:
        """Adds a lifecycle event for an alert. Returns the alert_id."""
        
        event_id = str(uuid.uuid4())
        
        # If it's a NEW alert, generate an alert_id
        if event_type == "ALERT_CREATED":
            alert_id = str(uuid.uuid4())
        elif not alert_id:
            raise ValueError("alert_id must be provided for non-creation events.")
            
        record = {
            "event_id": event_id,
            "alert_id": alert_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "severity": severity,
            "category": category,
            "pipeline_run_id": pipeline_run_id,
            "evidence": evidence,
            "recommended_action": recommended_action,
            "actor": actor,
            "reason": reason
        }
        
        self.store.append(record)
        return alert_id
        
    def get_all_events(self) -> List[Dict[str, Any]]:
        return self.store.read_all()
        
    def get_alert_history(self, alert_id: str) -> List[Dict[str, Any]]:
        events = self.get_all_events()
        return [e for e in events if e.get("alert_id") == alert_id]
        
    def get_current_alerts(self) -> Dict[str, Dict[str, Any]]:
        """
        Reconstructs the current state of all alerts from their event history.
        Returns a dictionary mapping alert_id to its latest state.
        """
        events = self.get_all_events()
        # Sort events chronologically just in case
        events.sort(key=lambda x: x.get("timestamp", ""))
        
        alerts = {}
        for event in events:
            a_id = event.get("alert_id")
            if not a_id:
                continue
                
            if a_id not in alerts:
                alerts[a_id] = {
                    "alert_id": a_id,
                    "created_at": event.get("timestamp"),
                    "severity": event.get("severity"),
                    "category": event.get("category"),
                    "pipeline_run_id": event.get("pipeline_run_id"),
                    "evidence": event.get("evidence"),
                    "recommended_action": event.get("recommended_action")
                }
            
            # The event_type dictates the current status
            alerts[a_id]["status"] = event.get("event_type").replace("ALERT_", "")
            alerts[a_id]["last_updated"] = event.get("timestamp")
            
        return alerts
        
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        alerts = self.get_current_alerts()
        return [a for a in alerts.values() if a["status"] not in ["RESOLVED", "DISMISSED"]]
