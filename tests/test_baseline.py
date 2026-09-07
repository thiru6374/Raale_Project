import pytest
import pandas as pd
import numpy as np
import os
from unittest.mock import patch, MagicMock

from src.config.settings import settings
from src.risk.baseline import BaselinePrioritisationModel
from src.risk.baseline_contracts import BaselineRunStatus, BaselinePriority, BaselineRecordStatus
from src.data.loader import DataLoader
from src.risk.baseline_repository import BaselineRepository


@pytest.fixture
def sample_processed_dataset():
    """Provides a sample canonical dataset for testing."""
    return pd.DataFrame({
        "neighbourhood_id": ["N001", "N002", "N003", "N004", "N005"],
        "neighbourhood_name": ["North", "South", "East", "West", "Central"],
        "latest_temperature_c": [45.2, 43.9, 41.2, 39.5, 38.0],
        "group_mobile": [True, False, True, False, True]
    })


@pytest.fixture
def baseline_model():
    return BaselinePrioritisationModel()


def test_valid_temperature_ranking(sample_processed_dataset, baseline_model):
    """Test 1: Valid temperature ranking (highest temp gets rank 1)."""
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=sample_processed_dataset):
        settings.baseline_top_n = 3
        settings.baseline_selection_mode = "top_n"
        
        result = baseline_model.run()
        
        assert result.status == BaselineRunStatus.COMPLETED
        assert len(result.records) == 5
        
        # N001 should be rank 1
        top_record = next(r for r in result.records if r.baseline_rank == 1)
        assert top_record.neighbourhood_id == "N001"
        assert top_record.baseline_temperature_value == 45.2
        assert top_record.baseline_priority == BaselinePriority.HIGH


def test_temperature_tie(sample_processed_dataset, baseline_model):
    """Test 2: Temperature tie uses deterministic neighbourhood_id tie-break."""
    # N006 and N007 have same temp. Alphabetical tie-break means N006 wins.
    tie_dataset = pd.DataFrame({
        "neighbourhood_id": ["N007", "N006"],
        "latest_temperature_c": [40.0, 40.0]
    })
    
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=tie_dataset):
        settings.baseline_top_n = 2
        settings.baseline_selection_mode = "top_n"
        result = baseline_model.run()
        assert result.status == BaselineRunStatus.COMPLETED
        
        rank1 = next(r for r in result.records if r.baseline_rank == 1)
        rank2 = next(r for r in result.records if r.baseline_rank == 2)
        
        assert rank1.neighbourhood_id == "N006"
        assert rank2.neighbourhood_id == "N007"


def test_missing_temperature(sample_processed_dataset, baseline_model):
    """Test 3: Missing temperature results in DATA_INSUFFICIENT."""
    # Introduce NaN
    df = sample_processed_dataset.copy()
    df.loc[df["neighbourhood_id"] == "N003", "latest_temperature_c"] = np.nan
    
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=df):
        result = baseline_model.run()
        
        assert result.status == BaselineRunStatus.COMPLETED_WITH_WARNING
        assert result.summary.data_insufficient_neighbourhoods == 1
        
        missing_record = next(r for r in result.records if r.neighbourhood_id == "N003")
        assert missing_record.baseline_status == BaselineRecordStatus.DATA_INSUFFICIENT
        assert missing_record.baseline_priority == BaselinePriority.DATA_INSUFFICIENT
        assert missing_record.baseline_rank is None


def test_all_temperatures_missing(sample_processed_dataset, baseline_model):
    """Test 4: All temperatures missing results in FAILED."""
    df = sample_processed_dataset.copy()
    df["latest_temperature_c"] = np.nan
    
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=df):
        result = baseline_model.run()
        
        assert result.status == BaselineRunStatus.FAILED
        assert "All 5 records have missing" in result.errors[0]


def test_top_n_selection(sample_processed_dataset, baseline_model):
    """Test 5: Top N selection."""
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=sample_processed_dataset):
        settings.baseline_selection_mode = "top_n"
        settings.baseline_top_n = 2
        
        result = baseline_model.run()
        
        selected = [r for r in result.records if r.baseline_selected]
        assert len(selected) == 2
        assert selected[0].neighbourhood_id in ("N001", "N002")
        assert selected[1].neighbourhood_id in ("N001", "N002")


def test_threshold_selection(sample_processed_dataset, baseline_model):
    """Test 6: Threshold selection."""
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=sample_processed_dataset):
        settings.baseline_selection_mode = "threshold"
        settings.baseline_threshold_temperature = 40.0
        
        result = baseline_model.run()
        
        selected = [r for r in result.records if r.baseline_selected]
        assert len(selected) == 3 # 45.2, 43.9, 41.2
        assert all(r.baseline_temperature_value >= 40.0 for r in selected)


def test_reproducibility(sample_processed_dataset, baseline_model):
    """Test 7: Reproducibility (same input/config = same output)."""
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=sample_processed_dataset):
        result1 = baseline_model.run()
        result2 = baseline_model.run()
        
        # Check ranks match exactly
        ranks1 = [r.baseline_rank for r in result1.records]
        ranks2 = [r.baseline_rank for r in result2.records]
        assert ranks1 == ranks2


def test_invalid_input_schema(sample_processed_dataset, baseline_model):
    """Test 8: Invalid input schema (missing required columns)."""
    df = sample_processed_dataset.drop(columns=["latest_temperature_c"])
    
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=df):
        result = baseline_model.run()
        
        assert result.status == BaselineRunStatus.FAILED
        assert any("latest_temperature_c" in str(e) for e in result.errors)


def test_phase3_compatibility(baseline_model):
    """Test 9: Phase 3 compatibility (loading canonical dataset directly)."""
    # This just ensures we can call load_processed_dataset without blowing up
    # assuming we have valid processed data from previous pipeline steps.
    df = baseline_model.loader.load_processed_dataset()
    if df is not None and not df.empty:
        # Just check that it has our configured column
        assert settings.baseline_temperature_feature in df.columns


def test_experiment_compatibility(sample_processed_dataset, baseline_model):
    """Test 10: Future experiment compatibility."""
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=sample_processed_dataset):
        result = baseline_model.run()
        
        assert result.metadata is not None
        assert result.metadata.dataset_fingerprint is not None
        assert result.summary.highest_temperature_c == 45.2


def test_extreme_but_valid_temperature(sample_processed_dataset, baseline_model):
    """Case 4: Extreme but Valid Temperature."""
    df = sample_processed_dataset.copy()
    df.loc[df["neighbourhood_id"] == "N001", "latest_temperature_c"] = 48.0
    
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=df):
        result = baseline_model.run()
        
        top_record = next(r for r in result.records if r.baseline_rank == 1)
        assert top_record.neighbourhood_id == "N001"
        assert top_record.baseline_temperature_value == 48.0


def test_top_n_greater_than_available(sample_processed_dataset, baseline_model):
    """Case 6: Top N Greater Than Available Records."""
    with patch.object(baseline_model.loader, "load_processed_dataset", return_value=sample_processed_dataset):
        settings.baseline_selection_mode = "top_n"
        settings.baseline_top_n = 20 # Only 5 available
        
        result = baseline_model.run()
        
        selected = [r for r in result.records if r.baseline_selected]
        assert len(selected) == 5
        assert result.status == BaselineRunStatus.COMPLETED_WITH_WARNING
        assert any("exceeds available" in w for w in result.warnings)
