"""
src/services/data_refresh_service.py

Manages continuous data refresh and monitors data freshness.
"""
from typing import Dict, Any
from datetime import datetime, timedelta

class DataRefreshService:
    @staticmethod
    def check_freshness(last_refresh: str, current_time: str = None) -> str:
        """
        Determines freshness state based on last successful refresh timestamp.
        Possible states: FRESH, AGING, STALE, UNAVAILABLE
        """
        if not last_refresh:
            return "UNAVAILABLE"
            
        try:
            last = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
            curr = datetime.fromisoformat(current_time.replace("Z", "+00:00")) if current_time else datetime.utcnow()
            
            delta = curr - last
            
            if delta <= timedelta(hours=12):
                return "FRESH"
            elif delta <= timedelta(hours=24):
                return "AGING"
            else:
                return "STALE"
        except Exception:
            return "UNAVAILABLE"

    @staticmethod
    def execute_refresh(provider_status: str, record_count: int, last_successful: str = None) -> Dict[str, Any]:
        """
        Simulates a manual or scheduled refresh and calculates freshness.
        """
        now = datetime.utcnow().isoformat() + "Z"
        
        status = "SUCCESS" if provider_status == "HEALTHY" else "FAILED"
        
        updated_last_successful = now if status == "SUCCESS" else last_successful
        
        freshness = DataRefreshService.check_freshness(updated_last_successful, now)
        
        return {
            "last_attempt": now,
            "last_successful_refresh": updated_last_successful,
            "refresh_status": status,
            "record_count": record_count if status == "SUCCESS" else 0,
            "data_quality_score": 0.95 if status == "SUCCESS" else 0.0,
            "provider_status": provider_status,
            "freshness_status": freshness,
            "failure_reason": "Provider unreachable" if status == "FAILED" else ""
        }
