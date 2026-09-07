"""
Phase 2 Unit Tests — Data Validation Schema

Tests the NeighbourhoodData Pydantic schema, DataQualityReport,
and DataQualityStatus including:
  - Valid records accepted
  - Required field enforcement
  - Numeric range bounds
  - Logical relationship validator (mobile_population <= total_population)
  - DataQualityReport structure
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from src.data.validation import (
    NeighbourhoodData,
    DataQualityReport,
    DataQualityStatus,
)


# ─────────────────────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────────────────────

def _valid_base_record(**overrides) -> dict:
    """Return a minimal valid record dict, with optional field overrides."""
    base = dict(
        neighbourhood_id="NH-001",
        neighbourhood_name="Chennai North Zone 1",
        district="Chennai",
        latitude=13.05,
        longitude=80.20,
        observation_date=date.today(),
        temperature_c=37.5,
        data_source="synthetic_generator",
    )
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────
#  Valid record acceptance
# ─────────────────────────────────────────────────────────────

class TestValidRecord:
    def test_minimal_valid_record(self):
        record = NeighbourhoodData(**_valid_base_record())
        assert record.neighbourhood_id == "NH-001"
        assert record.temperature_c == 37.5

    def test_full_valid_record(self):
        record = NeighbourhoodData(**_valid_base_record(
            heat_index=42.0,
            humidity_percent=65.0,
            built_density=0.75,
            green_cover_percent=20.0,
            impervious_surface_percent=70.0,
            urban_heat_exposure_score=0.8,
            healthcare_distance_km=2.5,
            healthcare_capacity=1500,
            transport_access_score=0.6,
            estimated_people_reachable=900,
            travel_time_minutes=18.0,
            service_time_minutes=20.0,
            vulnerability_index=0.65,
            elderly_population_percent=0.18,
            low_income_indicator=True,
            total_population=50000,
            mobile_population=2000,
            mobile_population_percent=0.04,
            group_mobile=False,
            group_low_service_access=False,
            generated_at=datetime.now(),
            dataset_version="1.0.0",
            synthetic_data=True,
        ))
        assert record.total_population == 50000
        assert record.mobile_population == 2000


# ─────────────────────────────────────────────────────────────
#  Required field enforcement
# ─────────────────────────────────────────────────────────────

class TestRequiredFields:
    def test_missing_neighbourhood_id_raises(self):
        data = _valid_base_record()
        del data["neighbourhood_id"]
        with pytest.raises(ValidationError) as exc_info:
            NeighbourhoodData(**data)
        assert any(e["loc"] == ("neighbourhood_id",) for e in exc_info.value.errors())

    def test_missing_temperature_c_raises(self):
        data = _valid_base_record()
        del data["temperature_c"]
        with pytest.raises(ValidationError):
            NeighbourhoodData(**data)

    def test_missing_data_source_raises(self):
        data = _valid_base_record()
        del data["data_source"]
        with pytest.raises(ValidationError):
            NeighbourhoodData(**data)

    def test_missing_district_raises(self):
        data = _valid_base_record()
        del data["district"]
        with pytest.raises(ValidationError):
            NeighbourhoodData(**data)

    def test_missing_observation_date_raises(self):
        data = _valid_base_record()
        del data["observation_date"]
        with pytest.raises(ValidationError):
            NeighbourhoodData(**data)


# ─────────────────────────────────────────────────────────────
#  Numeric range validation
# ─────────────────────────────────────────────────────────────

class TestNumericRanges:
    def test_temperature_above_max_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(temperature_c=61.0))

    def test_temperature_below_min_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(temperature_c=-1.0))

    def test_temperature_at_max_boundary_accepted(self):
        record = NeighbourhoodData(**_valid_base_record(temperature_c=60.0))
        assert record.temperature_c == 60.0

    def test_temperature_at_min_boundary_accepted(self):
        record = NeighbourhoodData(**_valid_base_record(temperature_c=0.0))
        assert record.temperature_c == 0.0

    def test_latitude_above_90_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(latitude=100.0))

    def test_latitude_below_minus_90_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(latitude=-91.0))

    def test_longitude_above_180_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(longitude=181.0))

    def test_longitude_below_minus_180_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(longitude=-181.0))

    def test_humidity_above_100_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(humidity_percent=101.0))

    def test_humidity_below_zero_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(humidity_percent=-1.0))

    def test_green_cover_above_100_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(green_cover_percent=101.0))

    def test_impervious_surface_above_100_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(impervious_surface_percent=101.0))

    def test_healthcare_distance_negative_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(healthcare_distance_km=-0.1))

    def test_travel_time_negative_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(travel_time_minutes=-5.0))

    def test_service_time_negative_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(service_time_minutes=-1.0))

    def test_healthcare_capacity_negative_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(healthcare_capacity=-1))

    def test_total_population_negative_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(total_population=-100))

    def test_mobile_population_negative_raises(self):
        with pytest.raises(ValidationError):
            NeighbourhoodData(**_valid_base_record(mobile_population=-1))


# ─────────────────────────────────────────────────────────────
#  Logical relationship validation
# ─────────────────────────────────────────────────────────────

class TestLogicalRelationships:
    def test_mobile_exceeding_total_population_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            NeighbourhoodData(**_valid_base_record(
                total_population=1000,
                mobile_population=2000,  # Invalid: 2000 > 1000
            ))
        assert "mobile_population cannot exceed total_population" in str(exc_info.value)

    def test_mobile_equal_to_total_population_accepted(self):
        record = NeighbourhoodData(**_valid_base_record(
            total_population=5000,
            mobile_population=5000,
        ))
        assert record.mobile_population == record.total_population

    def test_mobile_less_than_total_population_accepted(self):
        record = NeighbourhoodData(**_valid_base_record(
            total_population=50000,
            mobile_population=2500,
        ))
        assert record.mobile_population < record.total_population

    def test_no_population_fields_accepted(self):
        """Records without population fields should still pass."""
        record = NeighbourhoodData(**_valid_base_record())
        assert record.mobile_population is None
        assert record.total_population is None


# ─────────────────────────────────────────────────────────────
#  DataQualityReport model
# ─────────────────────────────────────────────────────────────

class TestDataQualityReport:
    def test_approved_report_creation(self):
        report = DataQualityReport(
            dataset_name="test",
            total_records=40, valid_records=40, invalid_records=0,
            duplicate_records=0, missing_values=0, out_of_range_values=0,
            warnings=0, critical_failures=0, status=DataQualityStatus.APPROVED
        )
        assert report.status == DataQualityStatus.APPROVED

    def test_warning_report_creation(self):
        report = DataQualityReport(
            dataset_name="test",
            total_records=40, valid_records=38, invalid_records=1,
            duplicate_records=1, missing_values=3, out_of_range_values=0,
            warnings=1, critical_failures=0, status=DataQualityStatus.WARNING
        )
        assert report.status == DataQualityStatus.WARNING
        assert report.missing_values == 3

    def test_failed_report_creation(self):
        report = DataQualityReport(
            dataset_name="test",
            total_records=10, valid_records=0, invalid_records=10,
            duplicate_records=0, missing_values=10, out_of_range_values=0,
            warnings=0, critical_failures=10, status=DataQualityStatus.FAILED
        )
        assert report.status == DataQualityStatus.FAILED

    def test_report_details_default_empty(self):
        report = DataQualityReport(
            dataset_name="test",
            total_records=5, valid_records=5, invalid_records=0,
            duplicate_records=0, missing_values=0, out_of_range_values=0,
            warnings=0, critical_failures=0, status=DataQualityStatus.APPROVED
        )
        assert report.details == []

    def test_all_statuses_accessible(self):
        statuses = list(DataQualityStatus)
        assert DataQualityStatus.APPROVED in statuses
        assert DataQualityStatus.WARNING in statuses
        assert DataQualityStatus.MANUAL_REVIEW in statuses
        assert DataQualityStatus.FAILED in statuses
