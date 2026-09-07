"""
src/utils/helpers.py

Shared utility functions used across the + data pipeline.
All functions are pure, stateless, and importable without side effects.
"""

import os
import json
import hashlib
import pandas as pd
from datetime import datetime
from typing import Any, Dict, Optional, List


# ─────────────────────────────────────────────────────────────
#  File & path utilities
# ─────────────────────────────────────────────────────────────

def ensure_dir(path: str) -> str:
    """Create directory (and parents) if it does not exist. Returns the path."""
    os.makedirs(path, exist_ok=True)
    return path


def safe_read_csv(path: str, **kwargs) -> Optional[pd.DataFrame]:
    """
    Read a CSV file safely.  Returns None and logs a warning instead of raising
    if the file does not exist or cannot be parsed.
    """
    from src.utils.logger import get_logger
    logger = get_logger("helpers")
    if not os.path.isfile(path):
        logger.warning(f"safe_read_csv: file not found — {path}")
        return None
    try:
        return pd.read_csv(path, **kwargs)
    except Exception as exc:
        logger.warning(f"safe_read_csv: could not read {path}: {exc}")
        return None


def safe_write_json(data: Dict[str, Any], path: str) -> bool:
    """
    Write *data* to *path* as pretty-printed JSON.
    Returns True on success, False on failure (logs the error).
    """
    from src.utils.logger import get_logger
    logger = get_logger("helpers")
    try:
        ensure_dir(os.path.dirname(path) or ".")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4, default=str)
        return True
    except Exception as exc:
        logger.error(f"safe_write_json: could not write {path}: {exc}")
        return False


def safe_read_json(path: str) -> Optional[Dict[str, Any]]:
    """
    Read a JSON file safely.  Returns None on failure.
    """
    from src.utils.logger import get_logger
    logger = get_logger("helpers")
    if not os.path.isfile(path):
        logger.warning(f"safe_read_json: file not found — {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning(f"safe_read_json: could not read {path}: {exc}")
        return None


# ─────────────────────────────────────────────────────────────
#  Data quality utilities
# ─────────────────────────────────────────────────────────────

def missing_value_summary(df: pd.DataFrame) -> Dict[str, int]:
    """
    Return a dict mapping each column with missing values to its missing count.
    Only columns that have at least one missing value are included.
    """
    counts = df.isna().sum()
    return {col: int(count) for col, count in counts.items() if count > 0}


def classify_missing_severity(
    missing_count: int,
    total_records: int,
    warning_threshold: float = 0.05,
    critical_threshold: float = 0.20,
) -> str:
    """
    Classify the severity of missing data for a single field.

    Returns:
        'acceptable'  — < warning_threshold
        'warning'     — warning_threshold to critical_threshold
        'critical'    — >= critical_threshold
    """
    if total_records == 0:
        return "critical"
    rate = missing_count / total_records
    if rate < warning_threshold:
        return "acceptable"
    if rate < critical_threshold:
        return "warning"
    return "critical"


def duplicate_id_summary(df: pd.DataFrame, id_col: str = "neighbourhood_id") -> List[str]:
    """
    Return a list of neighbourhood_id values that appear more than once.
    Returns an empty list if the column is absent or has no duplicates.
    """
    if id_col not in df.columns:
        return []
    counts = df[id_col].value_counts()
    return list(counts[counts > 1].index)


# ─────────────────────────────────────────────────────────────
#  Provenance / reproducibility utilities
# ─────────────────────────────────────────────────────────────

def build_metadata(
    dataset_name: str,
    source_type: str,
    source_name: str,
    random_seed: int,
    record_count: int,
    synthetic_data: bool = True,
    dataset_version: str = "1.0.0",
    schema_version: str = "1.0",
) -> Dict[str, Any]:
    """
    Build a structured provenance metadata dict suitable for serialisation
    to ``data/raw/metadata.json``.

    This dict is consumed by (Confidence) and (Experiment)
    to trace where the data came from and with which seed.
    """
    return {
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
        "source_type": source_type,
        "source_name": source_name,
        "synthetic_data": synthetic_data,
        "generated_at": datetime.now().isoformat(),
        "random_seed": random_seed,
        "record_count": record_count,
        "schema_version": schema_version,
    }


def dataframe_fingerprint(df: pd.DataFrame, exclude_cols: Optional[List[str]] = None) -> str:
    """
    Return a short SHA-256 fingerprint of a DataFrame's numeric content,
    useful for reproducibility checks without storing the full dataset.

    exclude_cols: column names to skip (e.g. wall-clock timestamps).
    """
    exclude_cols = exclude_cols or ["generated_at"]
    cols = [c for c in df.select_dtypes(include="number").columns if c not in exclude_cols]
    data_bytes = df[cols].to_csv(index=False).encode("utf-8")
    return hashlib.sha256(data_bytes).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────
#  DataFrame utility helpers
# ─────────────────────────────────────────────────────────────

def coerce_bool_columns(df: pd.DataFrame, bool_cols: List[str]) -> pd.DataFrame:
    """
    Safely coerce object-dtype bool columns back to actual Python bool.
    Handles None, 'True', 'False', 1, 0.
    """
    df = df.copy()
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map(
                lambda v: True if str(v).lower() in ("true", "1") else False
            )
    return df


def safe_numeric(series: pd.Series, fill: float = 0.0) -> pd.Series:
    """Convert a series to numeric, replacing non-parseable values with *fill*."""
    return pd.to_numeric(series, errors="coerce").fillna(fill)
