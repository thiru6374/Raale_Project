"""
src/services/release_readiness_service.py

Validates the environment for production deployment.
"""
import os
import sys

class ReleaseReadinessService:
    @staticmethod
    def check_readiness() -> dict:
        """
        Validates required components for production deployment.
        Returns overall status and detailed checks.
        """
        checks = []
        
        # 1. Directories exist
        required_dirs = ["data", "data/config", "data/intelligence", "data/reports", "src", "app"]
        for d in required_dirs:
            exists = os.path.isdir(d)
            checks.append({
                "check": f"Directory {d}",
                "status": "PASS" if exists else "FAIL",
                "reason": "" if exists else f"Missing directory: {d}"
            })
            
        # 2. Config available
        config_exists = os.path.isfile("src/config/settings.py")
        checks.append({
            "check": "Configuration",
            "status": "PASS" if config_exists else "FAIL",
            "reason": "" if config_exists else "Missing settings.py"
        })
        
        # 3. Streamlit Entry point
        entry_exists = os.path.isfile("app/main.py")
        checks.append({
            "check": "Streamlit Entry Point",
            "status": "PASS" if entry_exists else "FAIL",
            "reason": "" if entry_exists else "Missing app/main.py"
        })
        
        # 4. Pipeline Modules exist
        try:
            import src.risk.risk_engine
            import src.optimisation.planner
            import src.fairness.bias_detection
            checks.append({"check": "Pipeline Modules", "status": "PASS", "reason": ""})
        except ImportError as e:
            checks.append({"check": "Pipeline Modules", "status": "FAIL", "reason": f"Import error: {e}"})

        failed_checks = [c for c in checks if c["status"] == "FAIL"]
        
        overall = "READY"
        if len(failed_checks) > 0:
            overall = "NOT READY"
            
        return {
            "status": overall,
            "checks": checks,
            "failures": failed_checks
        }
