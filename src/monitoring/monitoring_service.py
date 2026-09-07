"""
src/monitoring/monitoring_service.py

Central monitoring service. Aggregates data quality, fairness, and
pipeline health into a single structured result for the UI.
"""
import os
import time
from typing import Dict, Any, Optional, List
import pandas as pd

from src.monitoring.data_monitor   import monitor_data_quality, monitor_data_distribution
from src.monitoring.fairness_monitor import monitor_fairness
from src.utils.logger import get_logger

logger = get_logger("monitoring_service")


class MonitoringService:
    """
    Aggregates all monitoring signals from the current pipeline session.
    Reads exclusively from application-state data — no pipeline re-run.
    """

    def __init__(
        self,
        raw_df: Optional[pd.DataFrame] = None,
        processed_df: Optional[pd.DataFrame] = None,
        pipeline_df: Optional[pd.DataFrame] = None,
        fairness_warnings: Optional[List[Dict]] = None,
        pipeline_status: str = "UNKNOWN",
        pipeline_duration_s: float = 0.0,
    ):
        self.raw_df             = raw_df
        self.processed_df       = processed_df
        self.pipeline_df        = pipeline_df
        self.fairness_warnings  = fairness_warnings or []
        self.pipeline_status    = pipeline_status
        self.pipeline_duration_s = pipeline_duration_s

    def get_full_monitoring_report(self) -> Dict[str, Any]:
        """Returns a complete monitoring snapshot using real data."""
        logger.info("Generating full monitoring report...")

        dq  = monitor_data_quality(self.raw_df, self.processed_df)
        dist = monitor_data_distribution(self.raw_df)
        fair = monitor_fairness(self.pipeline_df, self.fairness_warnings)

        # Audit log status
        audit_path  = "logs/audit.jsonl"
        audit_status = "AVAILABLE" if os.path.exists(audit_path) else "NOT_FOUND"

        # Feedback status
        fb_path   = "data/feedback/feedback.jsonl"
        fb_status = "AVAILABLE" if os.path.exists(fb_path) else "NOT_FOUND"
        fb_count  = 0
        if os.path.exists(fb_path):
            with open(fb_path) as f:
                fb_count = sum(1 for line in f if line.strip())

        # Experiment status
        exp_dir    = "data/experiments"
        exp_status = "AVAILABLE" if (os.path.exists(exp_dir) and os.listdir(exp_dir)) else "NONE"

        # Fallback / trust counts
        fallback_count = 0
        untrusted_count = 0
        if self.pipeline_df is not None and "fallback_status" in self.pipeline_df.columns:
            fallback_count  = int((self.pipeline_df["fallback_status"] == "MANUAL_REVIEW").sum())
            untrusted_count = int((self.pipeline_df["fallback_status"] == "UNTRUSTED").sum())

        # Pipeline overall health
        if self.pipeline_status == "SUCCESS" and dq["status"] == "PASS" and fair["overall_status"] == "PASS":
            pipeline_health = "HEALTHY"
        elif self.pipeline_status == "FAILED":
            pipeline_health = "DEGRADED"
        else:
            pipeline_health = "ATTENTION REQUIRED"

        return {
            "pipeline_health":       pipeline_health,
            "pipeline_status":       self.pipeline_status,
            "pipeline_duration_s":   round(self.pipeline_duration_s, 2),
            "data_quality":          dq,
            "data_distribution":     dist,
            "fairness":              fair,
            "fallback_count":        fallback_count,
            "untrusted_count":       untrusted_count,
            "audit_logging_status":  audit_status,
            "feedback_storage_status": fb_status,
            "feedback_response_count": fb_count,
            "experiment_status":     exp_status,
        }
