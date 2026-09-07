import pytest
import pandas as pd
import numpy as np
from src.data.preprocessing import DataPreprocessor
from src.data.validation import DataQualityStatus
from src.data.contracts import PreprocessingResult
import os
import tempfile
from unittest.mock import patch

@pytest.fixture
def mock_settings():
    with patch("src.config.settings.settings.raw_data_dir", "tests/data/raw"), \
         patch("src.config.settings.settings.processed_data_dir", "tests/data/processed"):
        yield

@pytest.fixture
def sample_domain_dfs():
    # Construct a minimal example of the domain CSVs with at least 5 rows to trigger outlier detection
    df_temp = pd.DataFrame({
        "neighbourhood_id": ["NH-001", "NH-002", "NH-001", "NH-003", "NH-004", "NH-005"],
        "observation_date": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-01", "2026-01-01", "2026-01-01"],
        "temperature_c": [35.0, 36.0, 36.5, 34.0, 35.5, 36.0],
        "heat_index": [38.0, 39.0, 39.5, 37.0, 38.5, 39.0],
        "humidity_percent": [60.0, 55.0, 62.0, 65.0, 58.0, 56.0]
    })
    
    df_built = pd.DataFrame({
        "neighbourhood_id": ["NH-001", "NH-002", "NH-003", "NH-004", "NH-005"],
        "built_density": [0.8, 0.4, 0.5, 0.6, 0.7],
        "green_cover_percent": [20.0, 60.0, 50.0, 40.0, 30.0],
        "impervious_surface_percent": [80.0, 40.0, 50.0, 60.0, 70.0],
        "urban_heat_exposure_score": [0.7, 0.3, 0.4, 0.5, 0.6]
    })
    
    df_service = pd.DataFrame({
        "neighbourhood_id": ["NH-001", "NH-002", "NH-003", "NH-004", "NH-005"],
        "healthcare_distance_km": [2.5, 5.0, 3.0, 4.0, 2.0],
        "healthcare_capacity": [1000, 500, 800, 600, 1200],
        "transport_access_score": [0.8, 0.4, 0.6, 0.5, 0.7],
        "estimated_people_reachable": [800, 300, 600, 400, 1000],
        "travel_time_minutes": [10.0, 25.0, 15.0, 20.0, 12.0],
        "service_time_minutes": [15.0, 20.0, 18.0, 16.0, 14.0]
    })
    
    df_vuln = pd.DataFrame({
        "neighbourhood_id": ["NH-001", "NH-002", "NH-003", "NH-004", "NH-005"],
        "vulnerability_index": [0.6, 0.3, 0.4, 0.5, 0.7],
        "elderly_population_percent": [15.0, 5.0, 10.0, 8.0, 12.0],
        "low_income_indicator": [True, False, False, True, True],
        "total_population": [50000, 20000, 30000, 25000, 40000],
        "mobile_population": [2000, 500, 1000, 800, 1500],
        "mobile_population_percent": [4.0, 2.5, 3.3, 3.2, 3.75],
        "group_mobile": [False, False, False, False, False],
        "group_low_service_access": [False, True, False, False, False]
    })
    
    return {
        "temperature": df_temp,
        "built_environment": df_built,
        "service_access": df_service,
        "vulnerability": df_vuln
    }

def test_preprocessing_integration_and_aggregation(sample_domain_dfs):
    preprocessor = DataPreprocessor()
    
    # Mock loader
    with patch("src.data.loader.DataLoader.load_raw_domain_files", return_value=sample_domain_dfs), \
         patch("src.data.loader.DataLoader.load_raw_unified", return_value=None), \
         patch("src.data.loader.DataLoader.save_processed_dataset"):
         
        result = preprocessor.run_pipeline()
        
        # Test basic success
        assert result.status == DataQualityStatus.APPROVED
        assert result.records_output == 5
        
        df_out = result.dataset
        assert "latest_temperature_c" in df_out.columns
        assert "temperature_c" not in df_out.columns
        
        # NH-001 should have the temperature from 2026-01-02 (36.5)
        nh_001 = df_out[df_out["neighbourhood_id"] == "NH-001"].iloc[0]
        assert nh_001["latest_temperature_c"] == 36.5
        
        # Percentages standardisation
        assert nh_001["green_cover_percent"] == 0.20 # 20.0 / 100

def test_preprocessing_missing_temperature_strategy(sample_domain_dfs):
    preprocessor = DataPreprocessor()
    
    # Let's remove NH-002 temperature completely to test missing strategy.
    sample_domain_dfs["temperature"] = sample_domain_dfs["temperature"][sample_domain_dfs["temperature"]["neighbourhood_id"] != "NH-002"]

    with patch("src.data.loader.DataLoader.load_raw_domain_files", return_value=sample_domain_dfs), \
         patch("src.data.loader.DataLoader.load_raw_unified", return_value=None), \
         patch("src.data.loader.DataLoader.save_processed_dataset"):
         
        result = preprocessor.run_pipeline()
        df_out = result.dataset
        
        # Status should be MANUAL_REVIEW due to critical missing temp
        assert result.status == DataQualityStatus.MANUAL_REVIEW
        
        nh_002 = df_out[df_out["neighbourhood_id"] == "NH-002"].iloc[0]
        assert pd.isna(nh_002["latest_temperature_c"])
        assert nh_002["latest_temperature_c_was_missing"] == True
        
def test_preprocessing_outlier_detection(sample_domain_dfs):
    # Inject impossible distance and extreme temperature
    sample_domain_dfs["service_access"].loc[0, "healthcare_distance_km"] = -5.0
    sample_domain_dfs["temperature"].loc[1, "temperature_c"] = -20.0 # Invalid
    
    preprocessor = DataPreprocessor()
    
    with patch("src.data.loader.DataLoader.load_raw_domain_files", return_value=sample_domain_dfs), \
         patch("src.data.loader.DataLoader.load_raw_unified", return_value=None), \
         patch("src.data.loader.DataLoader.save_processed_dataset"):
         
        result = preprocessor.run_pipeline()
        
        # Due to invalid outliers, status should be MANUAL_REVIEW or WARNING
        assert result.status in [DataQualityStatus.MANUAL_REVIEW, DataQualityStatus.WARNING]
        
        df_out = result.dataset
        nh_001 = df_out[df_out["neighbourhood_id"] == "NH-001"].iloc[0]
        # Invalid distance should have been clipped to NaN
        assert pd.isna(nh_001["healthcare_distance_km"])
        
        nh_002 = df_out[df_out["neighbourhood_id"] == "NH-002"].iloc[0]
        # Invalid temp should have been clipped to NaN
        assert pd.isna(nh_002["latest_temperature_c"])
