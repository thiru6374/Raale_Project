from typing import Dict, Any

from src.services.app_state import AppState
from src.validation.system_validator import SystemValidator

class SystemHealthService:
    """
    Central service to evaluate system health.
    Uses the currently loaded AppState.
    """
    
    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """
        Retrieves the complete health overview of the system.
        """
        if AppState.get_pipeline_status() == "UNINITIALIZED":
            # If system is not initialized, run validation on empty results
            validator = SystemValidator()
            return validator.validate()
            
        results = AppState.get_full_results()
        validator = SystemValidator(results)
        return validator.validate()
