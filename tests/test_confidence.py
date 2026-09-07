import pandas as pd
import numpy as np
from src.risk.confidence import ConfidenceEvaluator

def test_confidence_evaluation():
    # Raw data with varying degrees of missing critical fields
    raw_df = pd.DataFrame({
        'temperature_c': [35.0, 35.0, np.nan],
        'heat_index': [38.0, np.nan, np.nan],
        'built_density': [0.5, 0.5, np.nan],
        'healthcare_capacity': [1000, np.nan, np.nan],
        'vulnerability_index': [0.8, np.nan, np.nan]
    })
    
    # Processed data (simulating that imputation already happened)
    processed_df = pd.DataFrame({
        'neighbourhood_id': ['N1', 'N2', 'N3'],
        'multi_factor_risk_score': [0.9, 0.8, 0.7]
    })
    
    evaluator = ConfidenceEvaluator()
    # Note: ConfidenceEvaluator only checks the CRITICAL_FIELDS present in raw_df.
    # In this test, all 5 columns are critical fields.
    result_df = evaluator.evaluate(raw_df, processed_df)
    
    assert 'confidence_score' in result_df.columns
    assert 'fallback_status' in result_df.columns
    
    # N1 has 0 missing out of 5 -> 1.0 (APPROVED)
    assert result_df['confidence_score'].iloc[0] == 1.0
    assert result_df['fallback_status'].iloc[0] == 'APPROVED'
    
    # N2 has 3 missing out of 5 -> 0.4 (MANUAL_REVIEW)
    assert result_df['confidence_score'].iloc[1] == 0.4
    assert result_df['fallback_status'].iloc[1] == 'MANUAL_REVIEW'
    
    # N3 has 5 missing out of 5 -> 0.0 (FAILED or MANUAL_REVIEW depending on thresholds)
    assert result_df['confidence_score'].iloc[2] == 0.0
    assert result_df['fallback_status'].iloc[2] in ['MANUAL_REVIEW', 'FAILED']
