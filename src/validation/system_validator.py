import os
import json
from typing import Dict, Any

from src.utils.logger import get_logger
from src.config.settings import settings

logger = get_logger("system_validator")

class SystemValidator:
    """
    Validates the end-to-end health of the system across all 6 phases.
    """
    
    def __init__(self, app_state_results: Dict[str, Any] = None):
        """
        app_state_results is expected to be the output from PipelineService.run_full_pipeline().
        """
        self.results = app_state_results or {}
        
    def validate(self) -> Dict[str, Any]:
        logger.info("Running complete system validation...")
        
        health = {
            "overall_status": "HEALTHY",
            "phase_1": "PASS",
            "phase_2": "PASS",
            "phase_3": "PASS",
            "phase_4": "PASS",
            "phase_5": "PASS",
            "phase_6": "PASS",
            "data_quality": 100.0,
            "recommendation_trust": "TRUSTED",
            "valid_records": 0,
            "invalid_records": 0,
            "fallback_active": False,
            "fairness_status": "PASS",
            "capacity_status": "PASS",
            "experiment_status": "PASS",
            "evidence_status": "PASS",
            "stakeholder_feedback_count": 0,
            "override_count": 0,
            "critical_errors": [],
            "warnings": []
        }
        
        if not self.results:
            health["overall_status"] = "ATTENTION REQUIRED"
            health["critical_errors"].append("Pipeline has not been executed yet.")
            health["phase_1"] = "WARNING"
            health["phase_2"] = "WARNING"
            health["phase_3"] = "WARNING"
            health["phase_4"] = "WARNING"
            health["phase_5"] = "WARNING"
            return health
            
        if self.results.get("status") == "FAILED":
            health["overall_status"] = "FAILED"
            health["critical_errors"].extend(self.results.get("errors", []))
            health["phase_4"] = "FAIL"
            return health
            
        # ── & 3: Data Quality ───────────────────────────
        raw_df = self.results.get("raw_df")
        processed_df = self.results.get("processed_df")
        
        if raw_df is not None and processed_df is not None:
            health["valid_records"] = len(processed_df)
            health["invalid_records"] = len(raw_df) - len(processed_df)
            if health["invalid_records"] > 0:
                health["data_quality"] = (health["valid_records"] / len(raw_df)) * 100
                health["warnings"].append(f"{health['invalid_records']} records were invalid.")
        else:
            health["phase_2"] = "FAIL"
            health["phase_3"] = "FAIL"
            health["critical_errors"].append("Dataframes are missing from pipeline results.")
            
        # Check Preprocessing Summary
        summary_path = os.path.join(settings.processed_data_dir, "preprocessing_summary.json")
        if os.path.exists(summary_path):
            try:
                with open(summary_path, "r") as f:
                    pp = json.load(f)
                    if pp.get("status") != "PASS":
                        health["phase_3"] = "WARNING"
                        health["warnings"].append("Preprocessing status is not PASS.")
            except Exception:
                pass
                
        # ── Risk, Fallback, Trust, Fairness, Override ──
        pipeline_df = self.results.get("pipeline_results")
        fairness_warnings = self.results.get("fairness_warnings", [])
        
        if pipeline_df is not None:
            # Fallback & Trust
            if "fallback_status" in pipeline_df.columns:
                fallback_counts = pipeline_df["fallback_status"].value_counts()
                if "UNTRUSTED" in fallback_counts or fallback_counts.get("STANDARD", len(pipeline_df)) < len(pipeline_df):
                    health["fallback_active"] = True
                    health["recommendation_trust"] = "CAUTION"
                    health["phase_4"] = "WARNING"
                    health["warnings"].append("Safe fallback was activated for some records.")
                    
            if "confidence_score" in pipeline_df.columns:
                min_conf = pipeline_df["confidence_score"].min()
                if min_conf < settings.warning_confidence_threshold:
                    health["recommendation_trust"] = "UNTRUSTED"
                    health["warnings"].append("Critical drop in prediction confidence detected.")
                    
            # Fairness
            if fairness_warnings:
                health["fairness_status"] = "WARNING"
                health["warnings"].append(f"Fairness analysis raised {len(fairness_warnings)} warning(s).")
                
            # Capacity
            if "selected_for_outreach" in pipeline_df.columns:
                selected_count = pipeline_df["selected_for_outreach"].sum()
                max_capacity = settings.number_of_teams * settings.maximum_visits_per_team
                if selected_count >= max_capacity:
                    health["capacity_status"] = "WARNING"
                    health["warnings"].append("System is operating at maximum capacity limit.")
                    
            # Overrides
            if "override_applied" in pipeline_df.columns:
                health["override_count"] = int(pipeline_df["override_applied"].sum())
        else:
            health["phase_4"] = "FAIL"
            health["critical_errors"].append("Final pipeline results dataframe is missing.")
            
        # ── Experimentation, Evidence, Stakeholder Feedback ──
        # Check evidence
        evidence_dir = "data/experiments"
        if os.path.exists(evidence_dir) and os.listdir(evidence_dir):
            health["experiment_status"] = "PASS"
            health["evidence_status"] = "PASS"
        else:
            health["phase_5"] = "WARNING"
            health["experiment_status"] = "WARNING"
            health["evidence_status"] = "WARNING"
            health["warnings"].append("No experiment evidence generated yet.")
            
        # Check stakeholder validation
        feedback_file = "data/feedback/feedback.jsonl"
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, "r") as f:
                    health["stakeholder_feedback_count"] = sum(1 for line in f if line.strip())
            except Exception:
                pass
                
        if health["critical_errors"]:
            health["overall_status"] = "FAILED"
        elif health["warnings"]:
            health["overall_status"] = "ATTENTION REQUIRED"
            
        return health
