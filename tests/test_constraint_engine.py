import pytest
import pandas as pd
from src.optimisation.constraint_engine import ConstraintEngine
from src.config.settings import settings

def test_feasible_plan():
    # Everything within limits
    settings.maximum_outreach_events_per_day = 50
    settings.number_of_teams = 5
    settings.maximum_visits_per_team = 10
    settings.maximum_travel_distance = 50.0
    settings.maximum_travel_time = 120
    settings.working_hours = 12.0
    
    df = pd.DataFrame({
        "selected_for_outreach": [True] * 40 + [False] * 10,
        "healthcare_distance_km": [1.0] * 50,
        "is_valid_geo": [True] * 50
    })
    
    engine = ConstraintEngine()
    result = engine.evaluate(df)
    
    assert result["is_feasible"] == True
    assert len(result["reasons"]) == 0
    assert len(result["table"]) > 0
    assert result["penalties"] == 0.0

def test_capacity_overflow():
    # Exceed total network capacity
    settings.maximum_outreach_events_per_day = 20
    settings.number_of_teams = 5
    settings.maximum_visits_per_team = 5
    
    df = pd.DataFrame({
        "selected_for_outreach": [True] * 25,
        "healthcare_distance_km": [1.0] * 25,
        "is_valid_geo": [True] * 25
    })
    
    engine = ConstraintEngine()
    result = engine.evaluate(df)
    
    assert result["is_feasible"] == False
    assert any("Exceeded maximum outreach events" in r for r in result["reasons"])

def test_excessive_travel():
    # Total distance per team exceeds limit
    settings.maximum_outreach_events_per_day = 50
    settings.number_of_teams = 1
    settings.maximum_visits_per_team = 10
    settings.maximum_travel_distance = 20.0
    settings.working_hours = 24.0
    
    df = pd.DataFrame({
        "selected_for_outreach": [True] * 5,
        "healthcare_distance_km": [5.0] * 5, # total distance = 25 km, team limit = 20
        "is_valid_geo": [True] * 5
    })
    
    engine = ConstraintEngine()
    result = engine.evaluate(df)
    
    # Travel distance is a SOFT/informational constraint — plan remains feasible
    assert result["is_feasible"] == True
    travel_row = next((r for r in result["table"] if r["Constraint"] == "Max Travel Dist/Team (km)"), None)
    assert travel_row is not None
    assert travel_row["Status"] == "WARN"

def test_invalid_coordinates():
    settings.maximum_outreach_events_per_day = 50
    settings.number_of_teams = 5
    settings.maximum_visits_per_team = 10
    
    df = pd.DataFrame({
        "selected_for_outreach": [True] * 5,
        "healthcare_distance_km": [1.0] * 5,
        "is_valid_geo": [False, True, True, True, True]
    })
    
    engine = ConstraintEngine()
    result = engine.evaluate(df)
    
    # GPS validity is a SOFT/informational constraint — scheduler assigns cluster-0 fallback
    assert result["is_feasible"] == True
    geo_row = next((r for r in result["table"] if r["Constraint"] == "Valid Geo Coordinates"), None)
    assert geo_row is not None
    assert geo_row["Status"] == "WARN"

def test_boundary_conditions():
    # Exactly on the limit should be feasible
    settings.maximum_outreach_events_per_day = 10
    settings.number_of_teams = 1
    settings.maximum_visits_per_team = 10
    settings.maximum_travel_distance = 10.0
    settings.maximum_travel_time = 20.0
    settings.working_hours = 10.0 + (20.0 / 60.0)
    
    df = pd.DataFrame({
        "selected_for_outreach": [True] * 10,
        "healthcare_distance_km": [1.0] * 10,
        "is_valid_geo": [True] * 10
    })
    
    engine = ConstraintEngine()
    result = engine.evaluate(df)
    
    assert result["is_feasible"] == True

def test_no_feasible_solution_fallback_in_planner():
    # Test that the planner correctly overrides the plan when constraint engine fails
    from src.optimisation.planner import OutreachPlanner
    
    # Force failure via max events
    settings.maximum_outreach_events_per_day = 0 
    settings.number_of_teams = 1
    
    df = pd.DataFrame({
        "neighbourhood_id": ["N1"],
        "multi_factor_risk_score": [1.0],
        "multi_factor_risk_category": ["EXTREME"],
        "healthcare_distance_km": [1.0],
        "is_valid_geo": [True],
        "is_spatially_schedulable": [True],
        "fallback_status": ["STANDARD"]
    })
    
    planner = OutreachPlanner()
    result = planner.plan_outreach(df)
    
    assert result["selected_for_outreach"].sum() == 0
    assert result["fallback_status"].iloc[0] == "FAILED"
    assert result["outreach_priority"].iloc[0] == "NO_ACTION"
