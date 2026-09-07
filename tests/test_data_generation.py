"""
Phase 2 Unit Tests — Data Generation

Test Cases (per Phase 2 specification):
  TC-1  Normal dataset (40 neighbourhoods): valid structure, ranges, no duplicates
  TC-2  Missing temperature simulation: detected, classified, not silently treated as valid
  TC-3  Invalid coordinate simulation: latitude out-of-bounds caught by schema
  TC-4  Duplicate neighbourhood simulation: duplicate_id detected in quality report
  TC-5  Reproducibility: same seed → identical datasets; different seed → different dataset
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from src.data.generator import SyntheticDataGenerator
from src.data.ingestion import (
    DataIngestor,
    SyntheticDataProvider,
    CSVDataProvider,
    MockAPIDataProvider,
    load_synthetic_data,
)
from src.data.validation import DataQualityStatus


# ─────────────────────────────────────────────────────────────
#  TC-1  Normal dataset
# ─────────────────────────────────────────────────────────────

class TestNormalDataset:
    """TC-1: Generate 40 clean neighbourhoods and verify structural integrity."""

    def setup_method(self):
        self.generator = SyntheticDataGenerator(seed=42)
        self.df = self.generator.generate_data(num_records=40, missing_rate=0.0)

    def test_record_count(self):
        assert len(self.df) == 40

    def test_required_columns_present(self):
        required = [
            "neighbourhood_id", "neighbourhood_name", "district",
            "latitude", "longitude", "observation_date",
            "temperature_c", "heat_index", "humidity_percent",
            "built_density", "green_cover_percent", "impervious_surface_percent",
            "urban_heat_exposure_score",
            "healthcare_distance_km", "healthcare_capacity", "transport_access_score",
            "estimated_people_reachable", "travel_time_minutes", "service_time_minutes",
            "vulnerability_index", "elderly_population_percent", "low_income_indicator",
            "total_population", "mobile_population", "mobile_population_percent",
            "group_mobile", "group_low_service_access",
            "data_source", "generated_at", "dataset_version", "synthetic_data",
        ]
        for col in required:
            assert col in self.df.columns, f"Missing column: {col}"

    def test_latitude_valid_range(self):
        assert self.df["latitude"].between(-90, 90).all()

    def test_longitude_valid_range(self):
        assert self.df["longitude"].between(-180, 180).all()

    def test_temperature_valid_range(self):
        assert (self.df["temperature_c"] >= 0).all()
        assert (self.df["temperature_c"] <= 60).all()

    def test_humidity_valid_range(self):
        assert (self.df["humidity_percent"] >= 0).all()
        assert (self.df["humidity_percent"] <= 100).all()

    def test_green_cover_valid_range(self):
        assert (self.df["green_cover_percent"] >= 0).all()
        assert (self.df["green_cover_percent"] <= 100).all()

    def test_impervious_surface_valid_range(self):
        assert (self.df["impervious_surface_percent"] >= 0).all()
        assert (self.df["impervious_surface_percent"] <= 100).all()

    def test_mobile_population_not_exceeding_total(self):
        assert (self.df["mobile_population"] <= self.df["total_population"]).all()

    def test_no_duplicate_neighbourhood_ids(self):
        assert self.df["neighbourhood_id"].nunique() == 40

    def test_fairness_groups_present(self):
        assert "group_mobile" in self.df.columns
        assert "group_low_service_access" in self.df.columns
        # Both groups should have at least some True and some False for meaningful fairness testing
        assert self.df["group_mobile"].any()
        assert self.df["group_low_service_access"].any()

    def test_synthetic_data_flag(self):
        assert self.df["synthetic_data"].all()

    def test_validation_passes_on_clean_data(self):
        provider = SyntheticDataProvider(num_records=40, missing_rate=0.0)
        ingestor = DataIngestor(provider)
        valid_df, report = ingestor.load_and_validate()
        assert report.status == DataQualityStatus.APPROVED
        assert report.total_records == 40
        assert report.valid_records == 40
        assert report.invalid_records == 0
        assert report.duplicate_records == 0


# ─────────────────────────────────────────────────────────────
#  TC-2  Missing temperature simulation
# ─────────────────────────────────────────────────────────────

class TestMissingTemperatureSimulation:
    """TC-2: Enabling simulate_missing_temperature injects NaN into temperature_c.
    The validation layer must detect this and not silently pass the records."""

    def test_missing_temperature_detected(self):
        with patch("src.data.generator.settings") as mock_settings:
            mock_settings.synthetic_neighbourhood_count = 20
            mock_settings.default_district_name = "Chennai"
            mock_settings.simulate_missing_temperature = True
            mock_settings.simulate_invalid_coordinates = False
            mock_settings.simulate_duplicate_neighbourhood = False
            mock_settings.simulate_extreme_temperature = False

            generator = SyntheticDataGenerator(seed=42)
            # missing_rate=0.5 guarantees at least some NaN values
            df = generator.generate_data(num_records=20, missing_rate=0.5)

            missing_count = df["temperature_c"].isna().sum()
            assert missing_count > 0, "Expected missing temperature values but found none"

    def test_missing_temperature_causes_validation_warning_or_failure(self):
        """Records with missing temperature_c (a required field) must fail Pydantic validation."""
        with patch("src.data.generator.settings") as mock_settings:
            mock_settings.synthetic_neighbourhood_count = 20
            mock_settings.default_district_name = "Chennai"
            mock_settings.simulate_missing_temperature = True
            mock_settings.simulate_invalid_coordinates = False
            mock_settings.simulate_duplicate_neighbourhood = False
            mock_settings.simulate_extreme_temperature = False

            generator = SyntheticDataGenerator(seed=42)
            df = generator.generate_data(num_records=20, missing_rate=0.5)

        ingestor = DataIngestor.__new__(DataIngestor)
        valid_df, report = ingestor.validate_dataframe(df)

        assert report.status in (
            DataQualityStatus.WARNING,
            DataQualityStatus.MANUAL_REVIEW,
            DataQualityStatus.FAILED,
        ), f"Expected non-APPROVED status but got {report.status}"
        assert report.invalid_records > 0, "Expected some invalid records"

    def test_missing_temperature_not_silently_valid(self):
        """The valid DataFrame must not contain rows where temperature_c is NaN."""
        with patch("src.data.generator.settings") as mock_settings:
            mock_settings.synthetic_neighbourhood_count = 10
            mock_settings.default_district_name = "Chennai"
            mock_settings.simulate_missing_temperature = True
            mock_settings.simulate_invalid_coordinates = False
            mock_settings.simulate_duplicate_neighbourhood = False
            mock_settings.simulate_extreme_temperature = False

            generator = SyntheticDataGenerator(seed=42)
            df = generator.generate_data(num_records=10, missing_rate=0.8)

        ingestor = DataIngestor.__new__(DataIngestor)
        valid_df, report = ingestor.validate_dataframe(df)

        if not valid_df.empty:
            assert not valid_df["temperature_c"].isna().any(), \
                "Valid records must not contain NaN temperature_c"


# ─────────────────────────────────────────────────────────────
#  TC-3  Invalid coordinate simulation
# ─────────────────────────────────────────────────────────────

class TestInvalidCoordinateSimulation:
    """TC-3: Enabling simulate_invalid_coordinates produces lat > 90.
    The Pydantic schema must catch this and exclude the record from valid set."""

    def test_invalid_latitude_generated(self):
        with patch("src.data.generator.settings") as mock_settings:
            mock_settings.synthetic_neighbourhood_count = 10
            mock_settings.default_district_name = "Chennai"
            mock_settings.simulate_missing_temperature = False
            mock_settings.simulate_invalid_coordinates = True
            mock_settings.simulate_duplicate_neighbourhood = False
            mock_settings.simulate_extreme_temperature = False

            generator = SyntheticDataGenerator(seed=42)
            df = generator.generate_data(num_records=10, missing_rate=0.0)

        # The first record should have an invalid latitude (100.0)
        assert df.iloc[0]["latitude"] == 100.0, \
            "Expected first record to have invalid latitude=100.0"

    def test_invalid_coordinate_caught_by_validation(self):
        with patch("src.data.generator.settings") as mock_settings:
            mock_settings.synthetic_neighbourhood_count = 10
            mock_settings.default_district_name = "Chennai"
            mock_settings.simulate_missing_temperature = False
            mock_settings.simulate_invalid_coordinates = True
            mock_settings.simulate_duplicate_neighbourhood = False
            mock_settings.simulate_extreme_temperature = False

            generator = SyntheticDataGenerator(seed=42)
            df = generator.generate_data(num_records=10, missing_rate=0.0)

        ingestor = DataIngestor.__new__(DataIngestor)
        valid_df, report = ingestor.validate_dataframe(df)

        assert report.invalid_records >= 1, \
            "Expected at least 1 invalid record due to out-of-range latitude"
        assert report.status != DataQualityStatus.APPROVED

    def test_invalid_coordinate_record_excluded_from_valid_set(self):
        with patch("src.data.generator.settings") as mock_settings:
            mock_settings.synthetic_neighbourhood_count = 10
            mock_settings.default_district_name = "Chennai"
            mock_settings.simulate_missing_temperature = False
            mock_settings.simulate_invalid_coordinates = True
            mock_settings.simulate_duplicate_neighbourhood = False
            mock_settings.simulate_extreme_temperature = False

            generator = SyntheticDataGenerator(seed=42)
            df = generator.generate_data(num_records=10, missing_rate=0.0)

        ingestor = DataIngestor.__new__(DataIngestor)
        valid_df, report = ingestor.validate_dataframe(df)

        if not valid_df.empty:
            assert (valid_df["latitude"] >= -90).all() and (valid_df["latitude"] <= 90).all(), \
                "All latitudes in valid DataFrame must be within -90 to 90"


# ─────────────────────────────────────────────────────────────
#  TC-4  Duplicate neighbourhood simulation
# ─────────────────────────────────────────────────────────────

class TestDuplicateNeighbourhoodSimulation:
    """TC-4: Enabling simulate_duplicate_neighbourhood creates a record with a repeated
    neighbourhood_id. The ingestion layer must detect and report it."""

    def test_duplicate_id_generated(self):
        with patch("src.data.generator.settings") as mock_settings:
            mock_settings.synthetic_neighbourhood_count = 10
            mock_settings.default_district_name = "Chennai"
            mock_settings.simulate_missing_temperature = False
            mock_settings.simulate_invalid_coordinates = False
            mock_settings.simulate_duplicate_neighbourhood = True
            mock_settings.simulate_extreme_temperature = False

            generator = SyntheticDataGenerator(seed=42)
            df = generator.generate_data(num_records=10, missing_rate=0.0)

        id_counts = df["neighbourhood_id"].value_counts()
        assert (id_counts > 1).any(), \
            "Expected at least one duplicated neighbourhood_id"

    def test_duplicate_detected_in_quality_report(self):
        with patch("src.data.generator.settings") as mock_settings:
            mock_settings.synthetic_neighbourhood_count = 10
            mock_settings.default_district_name = "Chennai"
            mock_settings.simulate_missing_temperature = False
            mock_settings.simulate_invalid_coordinates = False
            mock_settings.simulate_duplicate_neighbourhood = True
            mock_settings.simulate_extreme_temperature = False

            generator = SyntheticDataGenerator(seed=42)
            df = generator.generate_data(num_records=10, missing_rate=0.0)

        ingestor = DataIngestor.__new__(DataIngestor)
        valid_df, report = ingestor.validate_dataframe(df)

        assert report.duplicate_records >= 1, \
            "Expected duplicate_records >= 1 in DataQualityReport"
        assert report.status != DataQualityStatus.APPROVED

    def test_duplicate_present_in_error_details(self):
        with patch("src.data.generator.settings") as mock_settings:
            mock_settings.synthetic_neighbourhood_count = 10
            mock_settings.default_district_name = "Chennai"
            mock_settings.simulate_missing_temperature = False
            mock_settings.simulate_invalid_coordinates = False
            mock_settings.simulate_duplicate_neighbourhood = True
            mock_settings.simulate_extreme_temperature = False

            generator = SyntheticDataGenerator(seed=42)
            df = generator.generate_data(num_records=10, missing_rate=0.0)

        ingestor = DataIngestor.__new__(DataIngestor)
        valid_df, report = ingestor.validate_dataframe(df)

        duplicate_errors = [d for d in report.details if d.get("error_type") == "duplicate_id"]
        assert len(duplicate_errors) >= 1, \
            "Expected at least one 'duplicate_id' entry in report details"


# ─────────────────────────────────────────────────────────────
#  TC-5  Reproducibility
# ─────────────────────────────────────────────────────────────

class TestReproducibility:
    """TC-5: Verify deterministic generation.
    Same seed → identical datasets. Different seed → different (but valid) dataset.
    """

    def test_same_seed_produces_identical_datasets(self):
        gen_a = SyntheticDataGenerator(seed=42)
        df_a = gen_a.generate_data(num_records=30, missing_rate=0.0)

        gen_b = SyntheticDataGenerator(seed=42)
        df_b = gen_b.generate_data(num_records=30, missing_rate=0.0)

        # Exclude wall-clock metadata column which will always differ between runs
        exclude_cols = ["generated_at"]
        cols = [c for c in df_a.columns if c not in exclude_cols]

        pd.testing.assert_frame_equal(
            df_a[cols].reset_index(drop=True),
            df_b[cols].reset_index(drop=True),
            check_like=False,
        )

    def test_different_seed_produces_different_dataset(self):
        gen_a = SyntheticDataGenerator(seed=42)
        df_a = gen_a.generate_data(num_records=30, missing_rate=0.0)

        gen_b = SyntheticDataGenerator(seed=99)
        df_b = gen_b.generate_data(num_records=30, missing_rate=0.0)

        # At least one temperature value should differ
        assert not (df_a["temperature_c"].values == df_b["temperature_c"].values).all(), \
            "Datasets with different seeds should differ in temperature_c"

    def test_different_seed_dataset_is_still_valid(self):
        """The alternative seed dataset must still pass schema validation."""
        provider = SyntheticDataProvider(num_records=30, missing_rate=0.0)
        # Override the internal generator seed
        with patch("src.data.generator.SyntheticDataGenerator") as MockGen:
            real_gen = SyntheticDataGenerator(seed=99)
            MockGen.return_value = real_gen
            df = provider.fetch_data()

        ingestor = DataIngestor.__new__(DataIngestor)
        valid_df, report = ingestor.validate_dataframe(df)

        assert report.status == DataQualityStatus.APPROVED
        assert report.valid_records == 30


# ─────────────────────────────────────────────────────────────
#  Additional: MockAPIDataProvider
# ─────────────────────────────────────────────────────────────

class TestMockAPIDataProvider:
    """Verify MockAPIDataProvider returns schema-compatible data."""

    def test_mock_api_returns_dataframe(self):
        provider = MockAPIDataProvider(num_records=10, seed=42)
        df = provider.fetch_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10

    def test_mock_api_data_source_label(self):
        provider = MockAPIDataProvider(num_records=5, seed=42, mock_type="temperature")
        df = provider.fetch_data()
        assert (df["data_source"] == "mock_api_temperature").all()

    def test_mock_api_data_validates_cleanly(self):
        provider = MockAPIDataProvider(num_records=15, seed=42)
        ingestor = DataIngestor(provider)
        valid_df, report = ingestor.load_and_validate()
        assert report.status == DataQualityStatus.APPROVED
        assert report.valid_records == 15

    def test_mock_api_is_reproducible(self):
        df_a = MockAPIDataProvider(num_records=10, seed=7).fetch_data()
        df_b = MockAPIDataProvider(num_records=10, seed=7).fetch_data()
        pd.testing.assert_frame_equal(
            df_a[["neighbourhood_id", "temperature_c"]].reset_index(drop=True),
            df_b[["neighbourhood_id", "temperature_c"]].reset_index(drop=True),
        )


# ─────────────────────────────────────────────────────────────
#  Additional: CSVDataProvider round-trip
# ─────────────────────────────────────────────────────────────

class TestCSVDataProvider:
    """Verify that data saved to CSV and re-read produces identical valid records."""

    def test_csv_roundtrip(self, tmp_path):
        generator = SyntheticDataGenerator(seed=42)
        raw_df = generator.generate_data(num_records=20, missing_rate=0.0)
        csv_file = tmp_path / "test_raw.csv"
        raw_df.to_csv(csv_file, index=False)

        provider = CSVDataProvider(file_path=str(csv_file))
        ingestor = DataIngestor(provider)
        valid_df, report = ingestor.load_and_validate()

        assert report.status == DataQualityStatus.APPROVED
        assert report.total_records == 20
        assert report.valid_records == 20

    def test_missing_csv_raises_error(self, tmp_path):
        provider = CSVDataProvider(file_path=str(tmp_path / "nonexistent.csv"))
        with pytest.raises(FileNotFoundError):
            provider.fetch_data()
