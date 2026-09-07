from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from src.data.validation import DataQualityStatus

class OutlierDetail(BaseModel):
    field_name: str
    outlier_count: int
    plausible_extremes_count: int = 0
    invalid_count: int = 0
    strategy_applied: str

class OutlierReport(BaseModel):
    total_outliers_detected: int = 0
    total_plausible_extremes: int = 0
    total_invalid_values: int = 0
    field_details: Dict[str, OutlierDetail] = Field(default_factory=dict)

class MissingDataDetail(BaseModel):
    field_name: str
    missing_count: int
    missing_percentage: float
    severity: str # "ACCEPTABLE", "WARNING", "CRITICAL"
    imputation_strategy: str
    affected_neighbourhoods: List[str] = Field(default_factory=list)

class MissingDataReport(BaseModel):
    total_missing_values: int = 0
    fields_with_missing_data: int = 0
    critical_missing_fields: int = 0
    warning_missing_fields: int = 0
    field_details: Dict[str, MissingDataDetail] = Field(default_factory=dict)

class PreprocessingMetadata(BaseModel):
    dataset_version: str
    preprocessing_version: str
    processed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    
class PreprocessingResult(BaseModel):
    status: DataQualityStatus
    records_input: int
    records_output: int
    records_removed: int
    missing_values_handled: int
    outliers_detected: int
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    missing_data_report: MissingDataReport
    outlier_report: OutlierReport
    metadata: PreprocessingMetadata
    dataset: Optional[Any] = None # Will hold the pandas DataFrame
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
