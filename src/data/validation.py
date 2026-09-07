from typing import Optional, List, Dict
from datetime import date, datetime
from pydantic import BaseModel, Field, model_validator
from enum import Enum

class DataQualityStatus(str, Enum):
    APPROVED = "APPROVED"
    WARNING = "WARNING"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FAILED = "FAILED"

class DataQualityReport(BaseModel):
    dataset_name: str
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    missing_values: int
    out_of_range_values: int = 0
    warnings: int
    critical_failures: int
    status: DataQualityStatus
    details: List[Dict] = Field(default_factory=list)

class NeighbourhoodData(BaseModel):
    # Identity
    neighbourhood_id: str
    neighbourhood_name: str
    district: str
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    # Temperature
    observation_date: date
    temperature_c: float = Field(..., ge=0, le=60) # realistic bounds for hot district
    heat_index: Optional[float] = None
    humidity_percent: Optional[float] = Field(None, ge=0, le=100)

    # Built Environment
    built_density: Optional[float] = None
    green_cover_percent: Optional[float] = Field(None, ge=0, le=100)
    impervious_surface_percent: Optional[float] = Field(None, ge=0, le=100)
    urban_heat_exposure_score: Optional[float] = None

    # Service Access
    healthcare_distance_km: Optional[float] = Field(None, ge=0)
    healthcare_capacity: Optional[int] = Field(None, ge=0)
    transport_access_score: Optional[float] = None
    estimated_people_reachable: Optional[int] = None
    travel_time_minutes: Optional[float] = Field(None, ge=0)
    service_time_minutes: Optional[float] = Field(None, ge=0)

    # Vulnerability
    vulnerability_index: Optional[float] = None
    elderly_population_percent: Optional[float] = Field(None, ge=0, le=1) # Note user said percent, assuming 0-1 or 0-100? Pydantic can handle limits
    low_income_indicator: Optional[bool] = None

    # Population
    total_population: Optional[int] = Field(None, ge=0)
    mobile_population: Optional[int] = Field(None, ge=0)
    mobile_population_percent: Optional[float] = Field(None, ge=0, le=1) # 0 to 1

    # Fairness Groups
    group_mobile: Optional[bool] = None
    group_low_service_access: Optional[bool] = None

    # Metadata
    data_source: str
    generated_at: Optional[datetime] = None
    dataset_version: Optional[str] = None
    synthetic_data: Optional[bool] = None

    @model_validator(mode='after')
    def check_logical_relationships(self):
        # elderly_population_percent logic (if 0-100 scale then limit is 100, if 0-1 limit is 1. We assume 0-1 for percentage properties here)
        if self.mobile_population is not None and self.total_population is not None:
            if self.mobile_population > self.total_population:
                raise ValueError("mobile_population cannot exceed total_population")
        
        # green cover + impervious surface could logically be > 1.0 (100%) if overlapping, but typically we cap them at a reasonable amount if they represent distinct land uses.
        # we'll leave it loosely checked or just rely on individual bounds for now to avoid false failures, as requested not to strictly rule it out unless justified.
        
        return self

