"""
src/geo/spatial_validator.py

Provides geographic validation logic for the GIS intelligence upgrade.
Ensures that missing or invalid coordinates do not crash the pipeline,
while safely removing them from spatial optimization and map visualization.
"""
import pandas as pd
import numpy as np
from src.utils.logger import get_logger

logger = get_logger("spatial_validator")

# Approximate Bounding Box for Chennai (configurable)
# Used to detect if coordinates are wildly out of the expected region
STUDY_REGION = {
    "LAT_MIN": 12.5,
    "LAT_MAX": 13.5,
    "LON_MIN": 79.8,
    "LON_MAX": 80.5
}

def validate_spatial_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates latitude and longitude columns.
    Adds `is_valid_geo`, `geo_validation_status`, `is_spatially_schedulable`.
    """
    if "latitude" not in df.columns or "longitude" not in df.columns:
        logger.warning("Geographic columns missing entirely from dataset.")
        df["is_valid_geo"] = False
        df["geo_validation_status"] = "MISSING_COLUMNS"
        df["is_spatially_schedulable"] = False
        # All records remain risk_eligible by default if other data exists
        df["is_risk_eligible"] = True 
        return df

    df_out = df.copy()
    
    # Initialize defaults
    df_out["is_valid_geo"] = True
    df_out["geo_validation_status"] = "VALID"
    df_out["is_spatially_schedulable"] = True
    df_out["is_risk_eligible"] = True
    
    # Check for missing values
    missing_lat = df_out["latitude"].isna()
    missing_lon = df_out["longitude"].isna()
    
    df_out.loc[missing_lat, "is_valid_geo"] = False
    df_out.loc[missing_lat, "geo_validation_status"] = "MISSING_LATITUDE"
    df_out.loc[missing_lat, "is_spatially_schedulable"] = False

    df_out.loc[missing_lon & ~missing_lat, "is_valid_geo"] = False
    df_out.loc[missing_lon & ~missing_lat, "geo_validation_status"] = "MISSING_LONGITUDE"
    df_out.loc[missing_lon & ~missing_lat, "is_spatially_schedulable"] = False

    # Check for invalid ranges (Global coordinates)
    invalid_lat_range = (df_out["latitude"] < -90) | (df_out["latitude"] > 90)
    invalid_lon_range = (df_out["longitude"] < -180) | (df_out["longitude"] > 180)
    
    df_out.loc[invalid_lat_range, "is_valid_geo"] = False
    df_out.loc[invalid_lat_range, "geo_validation_status"] = "INVALID_LATITUDE_RANGE"
    df_out.loc[invalid_lat_range, "is_spatially_schedulable"] = False
    
    df_out.loc[invalid_lon_range & ~invalid_lat_range, "is_valid_geo"] = False
    df_out.loc[invalid_lon_range & ~invalid_lat_range, "geo_validation_status"] = "INVALID_LONGITUDE_RANGE"
    df_out.loc[invalid_lon_range & ~invalid_lat_range, "is_spatially_schedulable"] = False

    # Check if outside study region
    outside_region = (
        (df_out["latitude"] < STUDY_REGION["LAT_MIN"]) |
        (df_out["latitude"] > STUDY_REGION["LAT_MAX"]) |
        (df_out["longitude"] < STUDY_REGION["LON_MIN"]) |
        (df_out["longitude"] > STUDY_REGION["LON_MAX"])
    )
    
    # Only flag outside region if it hasn't already failed a more severe check
    region_mask = outside_region & df_out["is_valid_geo"]
    df_out.loc[region_mask, "is_valid_geo"] = False
    df_out.loc[region_mask, "geo_validation_status"] = "OUTSIDE_STUDY_REGION"
    df_out.loc[region_mask, "is_spatially_schedulable"] = False
    
    # Check for exact duplicates
    if "neighbourhood_id" in df_out.columns:
        # If two different neighbourhoods have the exact same lat/lon, it's highly suspicious
        # But for now, we just flag them if they share coordinates but have different IDs
        # Actually, simpler duplicate coordinate check:
        dup_coords = df_out.duplicated(subset=["latitude", "longitude"], keep=False)
        dup_mask = dup_coords & df_out["is_valid_geo"]
        # In a real system, duplicates might be fine (e.g. apartment buildings), 
        # but the spec asks to flag DUPLICATE_COORDINATES
        df_out.loc[dup_mask, "is_valid_geo"] = False
        df_out.loc[dup_mask, "geo_validation_status"] = "DUPLICATE_COORDINATES"
        # We might still consider them spatially schedulable if they are real places, 
        # but to be safe, let's say False to force manual review.
        df_out.loc[dup_mask, "is_spatially_schedulable"] = False

    invalid_count = (~df_out["is_valid_geo"]).sum()
    if invalid_count > 0:
        logger.warning(f"Spatial validation found {invalid_count} records with missing/invalid GIS coordinates.")
        
    return df_out
