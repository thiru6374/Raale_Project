"""
tests/test_geo_validator.py
"""
import pytest
import pandas as pd
import numpy as np
from src.geo.spatial_validator import validate_spatial_data

def test_spatial_validator_valid():
    df = pd.DataFrame({
        "neighbourhood_id": ["N1", "N2"],
        "latitude": [13.0, 13.1],
        "longitude": [80.1, 80.2]
    })
    df_val = validate_spatial_data(df)
    assert df_val["is_valid_geo"].all()
    assert df_val["is_spatially_schedulable"].all()
    
def test_spatial_validator_missing_lat():
    df = pd.DataFrame({
        "neighbourhood_id": ["N1", "N2"],
        "latitude": [np.nan, 13.1],
        "longitude": [80.1, 80.2]
    })
    df_val = validate_spatial_data(df)
    assert not df_val.loc[0, "is_valid_geo"]
    assert df_val.loc[0, "geo_validation_status"] == "MISSING_LATITUDE"
    assert not df_val.loc[0, "is_spatially_schedulable"]
    assert df_val.loc[1, "is_valid_geo"]

def test_spatial_validator_invalid_range():
    df = pd.DataFrame({
        "neighbourhood_id": ["N1"],
        "latitude": [95.0],
        "longitude": [80.1]
    })
    df_val = validate_spatial_data(df)
    assert not df_val.loc[0, "is_valid_geo"]
    assert df_val.loc[0, "geo_validation_status"] == "INVALID_LATITUDE_RANGE"

def test_spatial_validator_outside_region():
    df = pd.DataFrame({
        "neighbourhood_id": ["N1"],
        "latitude": [5.0], # Outside Chennai
        "longitude": [80.1]
    })
    df_val = validate_spatial_data(df)
    assert not df_val.loc[0, "is_valid_geo"]
    assert df_val.loc[0, "geo_validation_status"] == "OUTSIDE_STUDY_REGION"
