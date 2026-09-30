import pandas as pd
import pytest
from src.risk.confidence import ConfidenceEvaluator

def test_confidence_evaluator_high_confidence():
    raw_df = pd.DataFrame({
        "temperature_c": [30.0],
        "heat_index": [32.0],
        "built_density": [0.5],
        "green_cover_percent": [20.0],
        "impervious_surface_percent": [50.0],
        "healthcare_capacity": [1.0],
        "healthcare_distance_km": [2.0],
        "vulnerability_index": [0.3],
        "elderly_population_percent": [15.0],
        "low_income_indicator": [0],
        "latitude": [40.0],
        "longitude": [-75.0]
    })
    processed_df = pd.DataFrame({"id": [1]})
    
    evaluator = ConfidenceEvaluator()
    result = evaluator.evaluate(raw_df, processed_df)
    
    assert result.loc[0, "confidence_level"] == "HIGH CONFIDENCE"
    assert result.loc[0, "fallback_status"] == "STANDARD"

def test_confidence_evaluator_missing_data():
    raw_df = pd.DataFrame({
        "temperature_c": [30.0],
        "heat_index": [None], # missing
        "built_density": [0.5],
        "green_cover_percent": [None], # missing
        "impervious_surface_percent": [50.0],
        "healthcare_capacity": [1.0],
        "healthcare_distance_km": [2.0],
        "vulnerability_index": [None], # missing
        "elderly_population_percent": [15.0],
        "low_income_indicator": [None], # missing
        "latitude": [40.0],
        "longitude": [-75.0]
    })
    processed_df = pd.DataFrame({"id": [1]})
    
    evaluator = ConfidenceEvaluator()
    result = evaluator.evaluate(raw_df, processed_df)
    
    assert result.loc[0, "confidence_level"] in ["LOW CONFIDENCE", "MEDIUM CONFIDENCE"]
    assert "Missing" in result.loc[0, "confidence_reason"]

def test_confidence_evaluator_invalid_gps():
    raw_df = pd.DataFrame({
        "temperature_c": [30.0],
        "heat_index": [32.0],
        "built_density": [0.5],
        "green_cover_percent": [20.0],
        "impervious_surface_percent": [50.0],
        "healthcare_capacity": [1.0],
        "healthcare_distance_km": [2.0],
        "vulnerability_index": [0.3],
        "elderly_population_percent": [15.0],
        "low_income_indicator": [0],
        "latitude": [100.0], # invalid
        "longitude": [-75.0]
    })
    processed_df = pd.DataFrame({"id": [1]})
    
    evaluator = ConfidenceEvaluator()
    result = evaluator.evaluate(raw_df, processed_df)
    
    # 0.4 penalty takes base 1.0 to 0.6 -> MEDIUM CONFIDENCE
    assert result.loc[0, "confidence_level"] == "MEDIUM CONFIDENCE"
    assert "Invalid/Missing GPS" in result.loc[0, "confidence_reason"]

def test_confidence_evaluator_abnormal_temp():
    raw_df = pd.DataFrame({
        "temperature_c": [70.0], # abnormal (> 60)
        "heat_index": [32.0],
        "built_density": [0.5],
        "green_cover_percent": [20.0],
        "impervious_surface_percent": [50.0],
        "healthcare_capacity": [1.0],
        "healthcare_distance_km": [2.0],
        "vulnerability_index": [0.3],
        "elderly_population_percent": [15.0],
        "low_income_indicator": [0],
        "latitude": [40.0],
        "longitude": [-75.0]
    })
    processed_df = pd.DataFrame({"id": [1]})
    
    evaluator = ConfidenceEvaluator()
    result = evaluator.evaluate(raw_df, processed_df)
    
    # 0.5 penalty takes base 1.0 to 0.5 -> MEDIUM CONFIDENCE or LOW
    assert result.loc[0, "confidence_level"] in ["MEDIUM CONFIDENCE", "LOW CONFIDENCE"]
    assert "Abnormal temp" in result.loc[0, "confidence_reason"]

def test_confidence_evaluator_empty_schema():
    raw_df = pd.DataFrame({"some_other_col": [1, 2]})
    processed_df = pd.DataFrame({"id": [1, 2]})
    
    evaluator = ConfidenceEvaluator()
    result = evaluator.evaluate(raw_df, processed_df)
    
    assert result.loc[0, "confidence_level"] == "HIGH CONFIDENCE"
    assert "No schema fields" in result.loc[0, "confidence_reason"]
