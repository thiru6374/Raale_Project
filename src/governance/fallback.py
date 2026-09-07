from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel

class FallbackStatus(str, Enum):
    APPROVED = "APPROVED"
    WARNING = "WARNING"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FAILED = "FAILED"

class FallbackResult(BaseModel):
    status: FallbackStatus
    message: str
    context: Optional[Dict[str, Any]] = None

def assess_data_completeness(missing_fields: int, total_fields: int) -> FallbackResult:
    """Assess if data is complete enough to proceed."""
    if total_fields == 0:
         return FallbackResult(status=FallbackStatus.FAILED, message="No fields provided.")
         
    completeness = (total_fields - missing_fields) / total_fields
    
    if completeness >= 0.9:
        return FallbackResult(status=FallbackStatus.APPROVED, message="Data complete.")
    elif completeness >= 0.7:
        return FallbackResult(status=FallbackStatus.WARNING, message="Partial data missing.")
    else:
        return FallbackResult(status=FallbackStatus.MANUAL_REVIEW, message="Data completeness extremely low.")
