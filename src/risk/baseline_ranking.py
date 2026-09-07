"""
src/risk/baseline_ranking.py

Pure, stateless ranking functions for the Temperature-Only Baseline.

All functions are deterministic and side-effect-free.
They operate on pandas DataFrames and return new DataFrames — no mutation.

Design rules enforced here:
  - Only the configured temperature feature drives ranking.
  - Tie-breaking uses only neighbourhood_id (alphabetical), never vulnerability
    or fairness indicators.
  - Priority categories are derived purely from configurable percentile bounds.
  - Missing temperature rows are partitioned out BEFORE ranking, never silently
    assigned a low rank.
"""

from __future__ import annotations

import pandas as pd
from typing import List, Tuple

from src.utils.logger import get_logger

logger = get_logger("baseline_ranking")


# ─────────────────────────────────────────────────────────────
#  1.  Input validation
# ─────────────────────────────────────────────────────────────

def validate_baseline_input(
    df: pd.DataFrame,
    temperature_feature: str,
    id_col: str = "neighbourhood_id",
) -> List[str]:
    """
    Validate the processed dataset before ranking.
    Returns a list of validation error strings (empty = valid).
    """
    errors: List[str] = []

    if df is None or len(df) == 0:
        errors.append("Input dataset is empty or None.")
        return errors

    if id_col not in df.columns:
        errors.append(f"Required column '{id_col}' is missing from the dataset.")

    if temperature_feature not in df.columns:
        errors.append(
            f"Configured temperature feature '{temperature_feature}' is not present "
            f"in the dataset. Available numeric columns: "
            f"{list(df.select_dtypes(include='number').columns)}"
        )

    return errors


# ─────────────────────────────────────────────────────────────
#  2.  Partition valid vs missing records
# ─────────────────────────────────────────────────────────────

def partition_by_temperature(
    df: pd.DataFrame,
    temperature_feature: str,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split the dataset into:
      valid_df   — rows where temperature_feature is not NaN
      missing_df — rows where temperature_feature IS NaN

    Missing rows are never ranked and never receive a silent low priority.

    Returns: (valid_df, missing_df)
    """
    has_temp = df[temperature_feature].notna()
    valid_df   = df[has_temp].copy()
    missing_df = df[~has_temp].copy()

    if len(missing_df) > 0:
        logger.warning(
            f"partition_by_temperature: {len(missing_df)} record(s) have missing "
            f"'{temperature_feature}' and will be marked DATA_INSUFFICIENT."
        )

    return valid_df, missing_df


# ─────────────────────────────────────────────────────────────
#  3.  Deterministic sort & rank
# ─────────────────────────────────────────────────────────────

def rank_by_temperature(
    valid_df: pd.DataFrame,
    temperature_feature: str,
    tie_break_column: str = "neighbourhood_id",
) -> pd.DataFrame:
    """
    Sort valid records descending by temperature, then ascending by
    tie_break_column (alphabetical for string IDs) to guarantee determinism.

    Assigns integer column 'baseline_rank' starting at 1.

    IMPORTANT: Only the temperature feature and the tie_break_column influence
    ordering.  Vulnerability, fairness, or service-access columns MUST NOT be
    added here.
    """
    if len(valid_df) == 0:
        ranked = valid_df.copy()
        ranked["baseline_rank"] = pd.Series(dtype="Int64")
        return ranked

    sort_cols = [temperature_feature]
    sort_asc   = [False]   # descending temperature

    if tie_break_column in valid_df.columns:
        sort_cols.append(tie_break_column)
        sort_asc.append(True)   # ascending neighbourhood_id for determinism
    else:
        logger.warning(
            f"Tie-break column '{tie_break_column}' not found — "
            "ranking may be non-deterministic on ties."
        )

    ranked = valid_df.sort_values(by=sort_cols, ascending=sort_asc).copy()
    ranked["baseline_rank"] = range(1, len(ranked) + 1)

    logger.info(
        f"rank_by_temperature: ranked {len(ranked)} records. "
        f"Top: {ranked.iloc[0][temperature_feature]:.2f}°C "
        f"({ranked.iloc[0].get(tie_break_column, 'n/a')})"
    )

    return ranked


# ─────────────────────────────────────────────────────────────
#  4.  Priority category assignment
# ─────────────────────────────────────────────────────────────

def assign_priority_categories(
    ranked_df: pd.DataFrame,
    high_percentile: float = 0.25,
    medium_percentile: float = 0.60,
) -> pd.DataFrame:
    """
    Assign priority category based on rank percentile among valid records.

    Categories:
      HIGH   — rank falls within top high_percentile of valid records
      MEDIUM — rank falls between high_percentile and medium_percentile
      LOW    — remaining valid records

    Parameters high_percentile and medium_percentile are proportions (0–1).
    Category logic is fully documented and contains no hidden factors.
    """
    df = ranked_df.copy()
    n = len(df)

    if n == 0:
        df["baseline_priority"] = pd.Series(dtype=str)
        return df

    high_cutoff   = max(1, round(n * high_percentile))
    medium_cutoff = max(high_cutoff, round(n * medium_percentile))

    conditions = [
        df["baseline_rank"] <= high_cutoff,
        df["baseline_rank"] <= medium_cutoff,
    ]
    choices = ["HIGH", "MEDIUM"]

    import numpy as np
    df["baseline_priority"] = np.select(conditions, choices, default="LOW")

    logger.info(
        f"assign_priority_categories: HIGH<={high_cutoff}, "
        f"MEDIUM<={medium_cutoff}, LOW=rest  (n={n})"
    )

    return df


# ─────────────────────────────────────────────────────────────
#  5.  Selection (top-N or threshold)
# ─────────────────────────────────────────────────────────────

def select_top_n(
    ranked_df: pd.DataFrame,
    top_n: int,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Select the top-N ranked records.

    If top_n > available ranked records, select all and record a warning.
    Returns (df_with_selected_flag, warnings_list).
    """
    warnings: List[str] = []
    df = ranked_df.copy()
    available = len(df)

    if top_n > available:
        warnings.append(
            f"Configured top_n={top_n} exceeds available ranked records ({available}). "
            f"All {available} ranked records selected."
        )
        actual_n = available
    else:
        actual_n = top_n

    df["baseline_selected"] = df["baseline_rank"] <= actual_n
    selected_count = int(df["baseline_selected"].sum())
    logger.info(f"select_top_n: selected {selected_count} of {available} ranked records.")

    return df, warnings


def select_by_threshold(
    ranked_df: pd.DataFrame,
    temperature_feature: str,
    threshold_c: float,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Select records whose temperature is >= threshold_c.

    Returns (df_with_selected_flag, warnings_list).
    """
    warnings: List[str] = []
    df = ranked_df.copy()

    df["baseline_selected"] = df[temperature_feature] >= threshold_c
    selected_count = int(df["baseline_selected"].sum())

    if selected_count == 0:
        warnings.append(
            f"Threshold mode: no records have temperature >= {threshold_c}°C. "
            "Consider lowering baseline_threshold_temperature in settings."
        )

    logger.info(
        f"select_by_threshold: {selected_count} records selected "
        f"above {threshold_c}°C threshold."
    )

    return df, warnings
