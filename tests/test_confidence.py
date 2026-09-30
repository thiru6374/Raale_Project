"""
tests/test_confidence.py

Updated to match the enhanced ConfidenceEvaluator (Phase 7/8).
The new evaluator applies multi-factor penalties beyond simple missingness.
"""
import pandas as pd
import numpy as np
from src.risk.confidence import ConfidenceEvaluator


def test_confidence_evaluation():
    """ConfidenceEvaluator produces expected levels for varying data quality."""
    # Raw data with varying degrees of missing critical fields
    raw_df = pd.DataFrame({
        'temperature_c': [35.0, 35.0, np.nan],
        'heat_index':    [38.0, np.nan, np.nan],
        'built_density': [0.5,  0.5,   np.nan],
        'healthcare_capacity':  [1000, np.nan, np.nan],
        'vulnerability_index':  [0.8,  np.nan, np.nan],
        'latitude':  [13.0, 13.0, 13.0],
        'longitude': [80.0, 80.0, 80.0],
    })

    processed_df = pd.DataFrame({
        'neighbourhood_id':       ['N1', 'N2', 'N3'],
        'multi_factor_risk_score': [0.9,  0.8,  0.7],
    })

    evaluator = ConfidenceEvaluator()
    result_df = evaluator.evaluate(raw_df, processed_df)

    assert 'confidence_score' in result_df.columns
    assert 'fallback_status'  in result_df.columns
    assert 'confidence_level' in result_df.columns
    assert 'confidence_reason' in result_df.columns

    # N1: all 5 fields present, valid GPS -> score should be close to 1.0 (HIGH CONFIDENCE)
    assert result_df['confidence_level'].iloc[0] == "HIGH CONFIDENCE"
    assert result_df['fallback_status'].iloc[0] == "STANDARD"

    # N2: several missing fields -> degraded score, MEDIUM or LOW
    assert result_df['confidence_level'].iloc[1] in ("MEDIUM CONFIDENCE", "LOW CONFIDENCE")

    # N3: temperature_c missing (worst case) -> LOW CONFIDENCE, MANUAL_REVIEW
    assert result_df['confidence_level'].iloc[2] == "LOW CONFIDENCE"
    assert result_df['fallback_status'].iloc[2] == "MANUAL_REVIEW"
