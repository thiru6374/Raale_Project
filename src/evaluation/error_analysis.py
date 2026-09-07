import pandas as pd
import numpy as np
from typing import Dict, List
from src.utils.logger import get_logger

logger = get_logger("error_analysis")

def find_high_confidence_errors(df: pd.DataFrame, score_col: str = 'multi_factor_risk_score') -> pd.DataFrame:
    """
    Finds rows where the model predicted LOW risk with HIGH confidence,
    but the true oracle label is HIGH/EXTREME (False Negatives with high confidence).
    These are the most dangerous errors.
    """
    if score_col not in df.columns:
        return pd.DataFrame()

    # Ground truth oracle (same as evaluation metrics module)
    if 'heat_index' in df.columns and 'vulnerability_index' in df.columns:
        truly_high_risk = (df['heat_index'].fillna(0) >= 39) & (df['vulnerability_index'].fillna(0) >= 0.5)
    else:
        truly_high_risk = df[score_col] >= 0.6

    predicted_low_risk = df[score_col] < 0.5
    high_confidence    = df.get('confidence_score', pd.Series(np.ones(len(df)))) >= 0.85

    dangerous_fn_mask = predicted_low_risk & truly_high_risk & high_confidence

    error_df = df[dangerous_fn_mask].copy()
    error_df['error_type'] = 'HIGH_CONFIDENCE_FALSE_NEGATIVE'
    logger.info(f"Found {len(error_df)} high-confidence false negatives.")
    return error_df


def summarise_errors_by_district(error_df: pd.DataFrame) -> pd.DataFrame:
    """Groups dangerous false negatives by district for stakeholder briefing."""
    if error_df.empty or 'district' not in error_df.columns:
        return pd.DataFrame()
    return error_df.groupby('district').size().reset_index(name='error_count').sort_values('error_count', ascending=False)
