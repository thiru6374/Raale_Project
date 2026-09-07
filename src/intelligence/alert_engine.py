"""
src/intelligence/alert_engine.py
"""
import pandas as pd
from typing import List, Dict, Any
from src.services.persistence.alert_repository import AlertRepository
from src.config.settings import settings

class AlertEngine:
    def __init__(self):
        self.alert_repo = AlertRepository()
        
    def generate_alerts(self, pipeline_df: pd.DataFrame, fairness_warnings: List[Dict], 
                        provider_meta: Dict[str, Any], pipeline_run_id: str, 
                        changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluates metrics and changes to generate lifecycle alerts.
        """
        alerts = []
        
        # 1. Capacity & Coverage Alert
        if "multi_factor_risk_category" in pipeline_df.columns and "selected_for_outreach" in pipeline_df.columns:
            hr_df = pipeline_df[pipeline_df["multi_factor_risk_category"].isin(["EXTREME", "HIGH"])]
            if len(hr_df) > 0:
                reached = hr_df["selected_for_outreach"].sum()
                coverage = reached / len(hr_df)
                
                if coverage < 0.80: # 80% is our target coverage
                    alerts.append({
                        "event_type": "ALERT_CREATED",
                        "severity": "CRITICAL" if coverage < 0.50 else "WARNING",
                        "category": "COVERAGE",
                        "evidence": f"Current coverage: {coverage:.1%}. Target: 80.0%. Missed: {len(hr_df) - reached} areas.",
                        "recommended_action": "Review capacity limits or trigger manual override for critical uncovered areas.",
                        "pipeline_run_id": pipeline_run_id
                    })
                    
        # 2. Fairness Alert
        if fairness_warnings:
            for w in fairness_warnings:
                alerts.append({
                    "event_type": "ALERT_CREATED",
                    "severity": "WARNING",
                    "category": "FAIRNESS",
                    "evidence": w.get("message", "Fairness parity gap detected."),
                    "recommended_action": "Adjust optimization strategy to FAIRNESS_AWARE or review group distributions.",
                    "pipeline_run_id": pipeline_run_id
                })
                
        # 3. Provider/Data Health
        status = provider_meta.get("provider_status", "UNKNOWN")
        if "FALLBACK" in status:
            alerts.append({
                "event_type": "ALERT_CREATED",
                "severity": "CRITICAL",
                "category": "DATA_HEALTH",
                "evidence": f"Provider failed. Fallback active: {status}",
                "recommended_action": "Investigate primary data provider API status.",
                "pipeline_run_id": pipeline_run_id
            })
            
        freshness = provider_meta.get("freshness", "UNKNOWN")
        if freshness in ["STALE", "CRITICAL"]:
            alerts.append({
                "event_type": "ALERT_CREATED",
                "severity": "WARNING" if freshness == "STALE" else "CRITICAL",
                "category": "DATA_FRESHNESS",
                "evidence": f"Temperature data is {freshness}.",
                "recommended_action": "Verify data ingestion pipeline connectivity.",
                "pipeline_run_id": pipeline_run_id
            })
            
        # 4. Integrate Changes
        for c in changes:
            if c.get("type") == "HIGH_RISK_INCREASE":
                alerts.append({
                    "event_type": "ALERT_CREATED",
                    "severity": "WATCH",
                    "category": "TREND",
                    "evidence": c.get("message"),
                    "recommended_action": "Monitor weather patterns. Ensure capacity is sufficient for upcoming days.",
                    "pipeline_run_id": pipeline_run_id
                })
                
        # Persist Alerts
        for a in alerts:
            self.alert_repo.add_event(**a)
            
        return alerts
