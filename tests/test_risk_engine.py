import pandas as pd
import numpy as np
import pytest
import json
from src.risk.baseline import BaselineRiskModel
from src.risk.risk_engine import MultiFactorRiskModel, RiskModelWeights
from src.features.engineering import FeatureEngineer

def test_baseline_risk_calculation():
    # Test typical values
    data = pd.DataFrame({
        'neighbourhood_id': ['N1', 'N2', 'N3', 'N4'],
        'heat_index': [30.0, 35.0, 41.0, 48.0]
    })
    
    model = BaselineRiskModel()
    result = model.calculate_risk(data)
    
    assert 'baseline_risk_score' in result.columns
    assert 'baseline_risk_category' in result.columns
    
    # Check categorization based on thresholds
    assert result.loc[result['neighbourhood_id'] == 'N1', 'baseline_risk_category'].iloc[0] == 'LOW'       # < 32
    assert result.loc[result['neighbourhood_id'] == 'N2', 'baseline_risk_category'].iloc[0] == 'MODERATE'  # >= 32, < 39
    assert result.loc[result['neighbourhood_id'] == 'N3', 'baseline_risk_category'].iloc[0] == 'HIGH'      # >= 39, < 45
    assert result.loc[result['neighbourhood_id'] == 'N4', 'baseline_risk_category'].iloc[0] == 'EXTREME'   # >= 45

    # Check bounds clipping [0, 1] for scores
    assert result['baseline_risk_score'].max() <= 1.0
    assert result['baseline_risk_score'].min() >= 0.0

def test_baseline_risk_fallback_to_temperature():
    # Test behavior when heat_index is missing
    data = pd.DataFrame({
        'neighbourhood_id': ['N1'],
        'temperature_c': [40.0]
    })
    
    model = BaselineRiskModel()
    result = model.calculate_risk(data)
    
    assert result.loc[result['neighbourhood_id'] == 'N1', 'baseline_risk_category'].iloc[0] == 'HIGH'
    
def test_baseline_risk_missing_required_data():
    data = pd.DataFrame({
        'neighbourhood_id': ['N1'],
        'population': [1000] # Missing temp entirely
    })
    
    model = BaselineRiskModel()
    with pytest.raises(ValueError):
        model.calculate_risk(data)

def test_feature_engineer():
    data = pd.DataFrame({
        'healthcare_capacity_normalized': [1.0, 0.0],
        'healthcare_distance_km_normalized': [0.0, 1.0],
        'built_density_normalized': [0.1, 0.9],
        'impervious_surface_percent': [0.1, 0.9],
        'green_cover_percent': [0.8, 0.1]
    })
    
    engineer = FeatureEngineer()
    result = engineer.generate_features(data)
    
    assert result['service_deficit_score'].iloc[0] == 0.0
    assert result['built_environment_score'].iloc[0] < 0.2
    
    assert result['service_deficit_score'].iloc[1] == 1.0
    assert result['built_environment_score'].iloc[1] > 0.8

def test_formal_multi_factor_risk_model_normalization_and_score():
    data = pd.DataFrame({
        'temperature_c': [30.0, 48.0],
        'built_density': [0.1, 0.9],
        'impervious_surface_percent': [0.1, 0.9],
        'green_cover_percent': [0.8, 0.1],
        'vulnerability_index': [0.1, 0.9],
        'healthcare_distance_km': [1.0, 10.0],
        'transport_access_score': [0.9, 0.1],
        'mobile_population': [0.1, 0.9]
    })
    
    # Use exact known weights for test
    weights = {
        "temperature": 0.2,
        "environmental": 0.2,
        "vulnerability": 0.2,
        "service_access": 0.2,
        "mobility": 0.2
    }
    
    model = MultiFactorRiskModel(weights_dict=weights)
    result = model.calculate_risk(data)
    
    assert 'multi_factor_risk_score' in result.columns
    assert 'multi_factor_risk_category' in result.columns
    assert 'risk_explainability' in result.columns
    
    # First row has lowest possible risk, so normalized values should be 0 across board
    # meaning final score is 0.0 -> LOW
    assert result['multi_factor_risk_category'].iloc[0] == 'LOW'
    assert np.isclose(result['multi_factor_risk_score'].iloc[0], 0.0)
    
    # Second row has extreme risk across the board, so normalized values should be 1
    # meaning final score is 1.0 -> VERY HIGH
    assert result['multi_factor_risk_category'].iloc[1] == 'VERY HIGH'
    assert np.isclose(result['multi_factor_risk_score'].iloc[1], 1.0)
    
    expl = json.loads(result['risk_explainability'].iloc[1])
    assert expl['final_score'] == 1.0
    assert expl['risk_level'] == 'VERY HIGH'
    assert expl['model_version'] == '2.0.0'
    assert expl['factors']['temperature']['normalized'] == 1.0
    assert expl['factors']['environmental']['weight'] == 0.2

def test_formal_multi_factor_weights_validation():
    # Valid
    valid_weights = {
        "temperature": 0.5,
        "environmental": 0.2,
        "vulnerability": 0.1,
        "service_access": 0.1,
        "mobility": 0.1
    }
    model = MultiFactorRiskModel(weights_dict=valid_weights)
    assert model.weights.temperature == 0.5
    
    # Sum != 1.0
    invalid_sum = {
        "temperature": 0.5,
        "environmental": 0.5,
        "vulnerability": 0.5,
        "service_access": 0.1,
        "mobility": 0.1
    }
    with pytest.raises(ValueError, match="Weights must sum to 1.0"):
        MultiFactorRiskModel(weights_dict=invalid_sum)
        
    # Weight out of bounds
    invalid_bounds = {
        "temperature": 1.2,
        "environmental": -0.1,
        "vulnerability": 0.0,
        "service_access": -0.1,
        "mobility": 0.0
    }
    with pytest.raises(ValueError):
        MultiFactorRiskModel(weights_dict=invalid_bounds)

def test_formal_multi_factor_missing_values():
    data = pd.DataFrame({
        'temperature_c': [30.0, np.nan, 40.0],
        'vulnerability_index': [np.nan, np.nan, np.nan]
    })
    
    model = MultiFactorRiskModel()
    result = model.calculate_risk(data)
    
    # Missing columns should default to 0 for normalization and their contribution is 0
    # The middle row has no temp, so it gets 0. The max temp is 40 (gets 1), min is 30 (gets 0).
    assert not result['multi_factor_risk_score'].isna().any()
