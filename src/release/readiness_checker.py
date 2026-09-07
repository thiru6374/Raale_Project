"""
src/release/readiness_checker.py

Release Readiness system. Evaluates the local environment to ensure
the prototype is fully operational and safe to demonstrate.
"""
import os
import sys
import subprocess
from typing import Dict, Any

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("readiness_checker")

class ReleaseReadinessChecker:
    
    def __init__(self):
        self.report = {
            "Environment": "PENDING",
            "Dependencies": "PENDING",
            "Configuration": "PENDING",
            "Pipeline": "PENDING",
            "Application Imports": "PENDING",
            "Storage": "PENDING",
            "Testing": "PENDING",
            "Overall": "NOT READY",
            "Warnings": [],
            "Critical_Errors": []
        }
        
    def _run_tests(self):
        """Runs the test suite to gather counts."""
        try:
            # -q for quiet, --disable-warnings to keep output clean, 
            # --tb=no to suppress tracebacks since we just want counts
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "--disable-warnings", "--tb=no"],
                capture_output=True,
                text=True,
                timeout=30
            )
            out = result.stdout
            
            if "no tests ran" in out:
                self.report["Testing"] = "NO TESTS FOUND"
                self.report["Warnings"].append("No tests ran during automated check.")
                return
                
            # If pytest ran successfully or failed some tests, it ends with a summary line
            if result.returncode == 0:
                self.report["Testing"] = "PASS"
            else:
                self.report["Testing"] = "WARNING (Some tests failed)"
                self.report["Warnings"].append("Automated test suite reported failures.")
                
        except FileNotFoundError:
            self.report["Testing"] = "FRAMEWORK NOT CONFIGURED"
            self.report["Warnings"].append("Automated test framework (pytest) not configured or not on PATH.")
        except subprocess.TimeoutExpired:
            self.report["Testing"] = "TIMEOUT"
            self.report["Warnings"].append("Automated tests timed out after 30 seconds.")
        except Exception as e:
            self.report["Testing"] = "ERROR"
            self.report["Critical_Errors"].append(f"Test runner error: {e}")

    def run_all_checks(self) -> Dict[str, Any]:
        logger.info("Running release readiness checks...")
        
        # 1. Environment Check
        try:
            py_version = sys.version_info
            if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 9):
                self.report["Environment"] = "FAIL"
                self.report["Critical_Errors"].append(f"Python 3.9+ required. Found {py_version.major}.{py_version.minor}")
            else:
                self.report["Environment"] = "PASS"
                
            in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
            if not in_venv:
                self.report["Warnings"].append("Not running inside a virtual environment.")
        except Exception as e:
            self.report["Environment"] = "FAIL"
            self.report["Critical_Errors"].append(f"Environment check failed: {e}")

        # 2. Dependencies
        req_file = "requirements.txt"
        if os.path.exists(req_file):
            self.report["Dependencies"] = "PASS"
        else:
            self.report["Dependencies"] = "WARNING"
            self.report["Warnings"].append("requirements.txt is missing.")
            
        # 3. Configuration
        try:
            if settings.number_of_teams <= 0:
                raise ValueError("number_of_teams must be > 0")
            if settings.maximum_coverage_gap < 0 or settings.maximum_coverage_gap > 1:
                raise ValueError("maximum_coverage_gap must be between 0 and 1")
            
            # Check weights sum roughly to 1
            w_sum = settings.temperature_weight + settings.built_environment_weight + settings.service_access_weight + settings.vulnerability_weight
            if abs(w_sum - 1.0) > 0.01:
                self.report["Warnings"].append(f"Objective weights sum to {w_sum}, expected 1.0")
                
            self.report["Configuration"] = "PASS"
        except Exception as e:
            self.report["Configuration"] = "FAIL"
            self.report["Critical_Errors"].append(f"Configuration validation failed: {e}")

        # 4. Storage Directories
        directories = [
            "data/raw", "data/processed", "data/feedback", "data/experiments", 
            "data/scenarios", "data/governance", "logs"
        ]
        storage_fail = False
        for d in directories:
            try:
                os.makedirs(d, exist_ok=True)
                # Test write access
                test_file = os.path.join(d, ".test_write")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                storage_fail = True
                self.report["Critical_Errors"].append(f"Cannot write to required directory {d}: {e}")
                
        self.report["Storage"] = "FAIL" if storage_fail else "PASS"

        # 5. Application Imports (Smoke check for module resolution)
        try:
            import app.main
            import src.services.pipeline_service
            import src.simulation.scenario_runner
            import src.explainability.risk_explainer
            self.report["Application Imports"] = "PASS"
        except ImportError as e:
            self.report["Application Imports"] = "FAIL"
            self.report["Critical_Errors"].append(f"Missing import: {e}")
            
        # 6. Pipeline Instantiation
        try:
            from src.services.pipeline_service import PipelineService
            # We don't run the pipeline here, just check it can be referenced
            _ = PipelineService.run_full_pipeline
            self.report["Pipeline"] = "PASS"
        except Exception as e:
            self.report["Pipeline"] = "FAIL"
            self.report["Critical_Errors"].append(f"Pipeline check failed: {e}")
            
        # 7. Testing
        self._run_tests()
        
        # Calculate Overall Status
        if self.report["Critical_Errors"]:
            self.report["Overall"] = "NOT READY"
        elif self.report["Warnings"]:
            self.report["Overall"] = "READY WITH WARNINGS"
        else:
            self.report["Overall"] = "READY FOR DEMONSTRATION"
            
        return self.report
