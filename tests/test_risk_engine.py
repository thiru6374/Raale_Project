import pandas as pd
import pytest
from src.risk.baseline import BaselineRiskModel
from src.risk.risk_engine import MultiFactorRiskModel
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
        'healthcare_capacity_normalized': [1.0, 0.0], # High cap -> 0 deficit, Low cap -> 1 deficit
        'healthcare_distance_km_normalized': [0.0, 1.0],
        'built_density_normalized': [0.1, 0.9],
        'impervious_surface_percent': [0.1, 0.9],
        'green_cover_percent': [0.8, 0.1]
    })
    
    engineer = FeatureEngineer()
    result = engineer.generate_features(data)
    
    # First row: excellent services and environment -> low risk scores
    assert result['service_deficit_score'].iloc[0] == 0.0
    assert result['built_environment_score'].iloc[0] < 0.2
    
    # Second row: poor services and environment -> high risk scores
    assert result['service_deficit_score'].iloc[1] == 1.0
    assert result['built_environment_score'].iloc[1] > 0.8

def test_multi_factor_risk_model():
    data = pd.DataFrame({
        'temperature_c': [30.0, 48.0],
        'built_environment_score': [0.0, 1.0],
        'service_deficit_score': [0.0, 1.0],
        'vulnerability_index': [0.0, 1.0]
    })
    
    model = MultiFactorRiskModel()
    result = model.calculate_risk(data)
    
    assert 'multi_factor_risk_score' in result.columns
    assert 'multi_factor_risk_category' in result.columns
    
    # First row has lowest possible risk
    assert result['multi_factor_risk_category'].iloc[0] == 'LOW'
    assert result['multi_factor_risk_score'].iloc[0] < 0.3
    
    # Second row has extreme risk across the board
    assert result['multi_factor_risk_category'].iloc[1] == 'EXTREME'
    assert result['multi_factor_risk_score'].iloc[1] > 0.8

