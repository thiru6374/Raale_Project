import pandas as pd
from src.optimisation.planner import OutreachPlanner
from src.config.settings import settings

def test_planner_capacity_constraint():
    # Create 100 neighbourhoods, all extreme risk, all highly populated
    data = pd.DataFrame({
        'neighbourhood_id': [f"N{i}" for i in range(100)],
        'multi_factor_risk_score': [0.9] * 100,
        'mobile_population': [1000] * 100,
        'fallback_status': ['APPROVED'] * 100,
        'multi_factor_risk_category': ['EXTREME'] * 100
    })
    
    # Force low capacity
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 5
    settings.maximum_outreach_events_per_day = 1000
    settings.maximum_travel_distance = 1000.0
    settings.maximum_travel_time = 2000
    settings.working_hours = 24.0
    # Total capacity = 10
    
    planner = OutreachPlanner()
    result = planner.plan_outreach(data)
    
    selected_count = result['selected_for_outreach'].sum()
    
    assert selected_count == 10
    assert (result['outreach_priority'] == "PRIMARY_OUTREACH").sum() == 10
    assert (result['outreach_priority'] == "WAITLIST_HIGH_RISK").sum() == 90

def test_planner_fallback_block():
    # Only 10 neighbourhoods, capacity is 10, but 5 are MANUAL_REVIEW
    data = pd.DataFrame({
        'neighbourhood_id': [f"N{i}" for i in range(10)],
        'multi_factor_risk_score': [0.9] * 10,
        'mobile_population': [1000] * 10,
        'fallback_status': ['APPROVED']*5 + ['MANUAL_REVIEW']*5,
        'multi_factor_risk_category': ['EXTREME'] * 10
    })
    
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 5
    settings.maximum_outreach_events_per_day = 1000
    settings.maximum_travel_distance = 1000.0
    settings.maximum_travel_time = 2000
    settings.working_hours = 24.0
    
    planner = OutreachPlanner()
    result = planner.plan_outreach(data)
    
    selected_count = result['selected_for_outreach'].sum()
    
    # It should only select the 5 approved ones, ignoring the capacity available
    assert selected_count == 5
    assert (result.loc[result['fallback_status'] == 'MANUAL_REVIEW', 'selected_for_outreach'] == False).all()
