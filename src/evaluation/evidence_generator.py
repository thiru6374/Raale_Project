import os
import json
from datetime import datetime
from typing import Dict, Any
from src.utils.logger import get_logger

logger = get_logger("evidence_generator")

class EvidenceGenerator:
    """
    Generates structured, defensible evidence comparing strategies.
    """
    
    def __init__(self, evidence_dir: str = "data/experiments"):
        self.evidence_dir = evidence_dir
        self._ensure_directory()
        
    def _ensure_directory(self):
        if not os.path.exists(self.evidence_dir):
            os.makedirs(self.evidence_dir)
            
    def generate_report(self, experiment_results: Dict[str, Any]) -> str:
        """
        Creates a structured evidence report from experiment results.
        Returns the path to the saved report.
        """
        timestamp = datetime.now().isoformat()
        experiment_id = f"EXP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        report = {
            "experiment_id": experiment_id,
            "timestamp": timestamp,
            "status": experiment_results.get("status", "UNKNOWN"),
        }
        
        if report["status"] != "SUCCESS":
            report["errors"] = experiment_results.get("errors", [])
            return self._save_report(report, experiment_id)
            
        # Extract metrics
        cov_metrics = experiment_results["coverage_focused"]["metrics"]
        fair_metrics = experiment_results["fairness_aware"]["metrics"]
        
        base_comparison = cov_metrics.get("baseline_comparison", {})
        
        report["data_summary"] = {
            "total_analyzed": cov_metrics["total_analyzed"],
            "high_risk_identified": cov_metrics["high_risk_identified"],
        }
        
        report["baseline_performance"] = {
            "high_risk_reached": base_comparison.get("baseline_high_risk_reached", 0),
            "high_risk_coverage_pct": base_comparison.get("baseline_high_risk_coverage_pct", 0.0),
        }
        
        report["optimized_coverage_focused"] = {
            "high_risk_reached": cov_metrics["high_risk_reached"],
            "high_risk_coverage_pct": cov_metrics["high_risk_coverage_pct"],
            "capacity_utilization_pct": cov_metrics["capacity_utilization_pct"],
            "fairness_metrics": cov_metrics["fairness"],
            "improvement_over_baseline_pct": base_comparison.get("coverage_improvement_pct", 0.0)
        }
        
        report["optimized_fairness_aware"] = {
            "high_risk_reached": fair_metrics["high_risk_reached"],
            "high_risk_coverage_pct": fair_metrics["high_risk_coverage_pct"],
            "capacity_utilization_pct": fair_metrics["capacity_utilization_pct"],
            "fairness_metrics": fair_metrics["fairness"],
        }
        
        return self._save_report(report, experiment_id)
        
    def _save_report(self, report: Dict[str, Any], experiment_id: str) -> str:
        filepath = os.path.join(self.evidence_dir, f"{experiment_id}.json")
        try:
            with open(filepath, "w") as f:
                json.dump(report, f, indent=4)
            logger.info(f"Evidence report saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save evidence report: {e}")
            return ""
