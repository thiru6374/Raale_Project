"""
src/monitoring/data_monitor.py

Monitors data quality and basic distribution of the current pipeline run.
Does NOT fake historical trends — only shows real current-run data.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("data_monitor")

# Columns considered critical for risk scoring
CRITICAL_COLUMNS = [
    "temperature_c",
    "healthcare_distance_km",
    "vulnerability_index",
    "built_density",
    "green_cover_percent",
]


def monitor_data_quality(
    raw_df: pd.DataFrame,
    processed_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Analyses data quality from the raw ingested dataframe.

    Returns structured metrics including:
    - missing value rates per critical field
    - overall quality score
    - status: PASS / WARNING / CRITICAL
    """
    if raw_df is None or raw_df.empty:
        return {
            "status": "CRITICAL",
            "total_records": 0,
            "message": "No data available for monitoring.",
            "field_missing_rates": {},
        }

    total = len(raw_df)
    valid = len(processed_df) if processed_df is not None else total
    invalid = total - valid
    quality_pct = (valid / total * 100) if total > 0 else 0

    field_missing = {}
    for col in CRITICAL_COLUMNS:
        if col in raw_df.columns:
            missing_count = raw_df[col].isna().sum()
            field_missing[col] = {
                "missing_count": int(missing_count),
                "missing_rate_pct": round(missing_count / total * 100, 1),
            }

    # Overall status
    if quality_pct >= 95 and all(v["missing_rate_pct"] < 10 for v in field_missing.values()):
        status = "PASS"
    elif quality_pct >= 80:
        status = "WARNING"
    else:
        status = "CRITICAL"

    duplicate_count = int(raw_df.duplicated(subset=["neighbourhood_id"]).sum()) \
        if "neighbourhood_id" in raw_df.columns else 0

    return {
        "status":              status,
        "total_records":       total,
        "valid_records":       valid,
        "invalid_records":     invalid,
        "duplicate_records":   duplicate_count,
        "quality_pct":         round(quality_pct, 1),
        "field_missing_rates": field_missing,
    }


def monitor_data_distribution(raw_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes basic descriptive statistics for numeric indicator columns.
    No drift detection — only current-run statistics.
    """
    if raw_df is None or raw_df.empty:
        return {"status": "NO_DATA", "distributions": {}}

    numeric_cols = [
        "temperature_c", "healthcare_distance_km",
        "vulnerability_index", "built_density",
        "green_cover_percent",
    ]
    distributions = {}
    for col in numeric_cols:
        if col in raw_df.columns:
            series = pd.to_numeric(raw_df[col], errors="coerce").dropna()
            if not series.empty:
                distributions[col] = {
                    "mean":   round(float(series.mean()), 3),
                    "median": round(float(series.median()), 3),
                    "min":    round(float(series.min()), 3),
                    "max":    round(float(series.max()), 3),
                    "std":    round(float(series.std()), 3),
                }

    return {"status": "AVAILABLE", "distributions": distributions}
