"""
src/simulation/scenario_definitions.py

Defines the configuration parameters for the 7 standard operational scenarios.
These dictate how the Scenario Runner alters inputs and configurations before running the pipeline.
"""

SCENARIOS = {
    "normal_conditions": {
        "id": "normal_conditions",
        "name": "Normal Conditions",
        "description": "Baseline operational conditions with balanced risk and normal capacity.",
        "input_changes": {},
        "capacity_settings": {
            "number_of_teams": 5,
            "maximum_visits_per_team": 3
        },
        "data_quality_conditions": {
            "missing_rate": 0.05
        },
        "strategy": "BALANCED",
        "expected_behaviour": "Standard operational baseline. Recommendations trusted.",
    },
    
    "extreme_heat": {
        "id": "extreme_heat",
        "name": "Extreme Heat Event",
        "description": "Increases temperatures universally to simulate an extreme heatwave.",
        "input_changes": {
            "temperature_boost": 3.0  # Add 3 degrees to all locations
        },
        "capacity_settings": {
            "number_of_teams": 5,
            "maximum_visits_per_team": 3
        },
        "data_quality_conditions": {
            "missing_rate": 0.05
        },
        "strategy": "COVERAGE_FOCUSED",
        "expected_behaviour": "More neighbourhoods become HIGH risk. Outreach demand exceeds capacity.",
    },
    
    "low_capacity": {
        "id": "low_capacity",
        "name": "Low Outreach Capacity",
        "description": "Simulates an operational shortage (e.g. staff sickness or budget cuts).",
        "input_changes": {},
        "capacity_settings": {
            "number_of_teams": 2,
            "maximum_visits_per_team": 2
        },
        "data_quality_conditions": {
            "missing_rate": 0.05
        },
        "strategy": "FAIRNESS_AWARE",
        "expected_behaviour": "Optimization must prioritize heavily. High-risk areas remain uncovered.",
    },
    
    "data_quality_degradation": {
        "id": "data_quality_degradation",
        "name": "Data Quality Degradation",
        "description": "Simulates sensor network failure or upstream data ingestion issues.",
        "input_changes": {},
        "capacity_settings": {
            "number_of_teams": 5,
            "maximum_visits_per_team": 3
        },
        "data_quality_conditions": {
            "missing_rate": 0.35  # 35% missing data
        },
        "strategy": "BALANCED",
        "expected_behaviour": "Data quality drops, trust is affected, safe fallback activates.",
    },
    
    "fairness_stress_test": {
        "id": "fairness_stress_test",
        "name": "Fairness Stress Test",
        "description": "Artificially concentrates high risk in groups that are hard to reach.",
        "input_changes": {
            "concentrate_risk_in_group": "group_low_service_access"
        },
        "capacity_settings": {
            "number_of_teams": 4,
            "maximum_visits_per_team": 2
        },
        "data_quality_conditions": {
            "missing_rate": 0.05
        },
        "strategy": "FAIRNESS_AWARE",
        "expected_behaviour": "Fairness gap widens, triggering mitigation from fairness-aware optimizer.",
    },
    
    "pipeline_failure": {
        "id": "pipeline_failure",
        "name": "Pipeline Failure",
        "description": "Simulates an unexpected crash during data preprocessing.",
        "input_changes": {
            "trigger_crash_at": "preprocessing"
        },
        "capacity_settings": {
            "number_of_teams": 5,
            "maximum_visits_per_team": 3
        },
        "data_quality_conditions": {
            "missing_rate": 0.05
        },
        "strategy": "COVERAGE_FOCUSED",
        "expected_behaviour": "System health degrades, raw traceback is caught, previous results protected.",
    },
    
    "safe_fallback": {
        "id": "safe_fallback",
        "name": "Safe Fallback Activation",
        "description": "Forces recommendations into an UNTRUSTED state to test fallback protocols.",
        "input_changes": {
            "force_untrusted": True
        },
        "capacity_settings": {
            "number_of_teams": 5,
            "maximum_visits_per_team": 3
        },
        "data_quality_conditions": {
            "missing_rate": 0.05
        },
        "strategy": "BALANCED",
        "expected_behaviour": "Fallback activates, overriding optimization output. Manual review required.",
    }
}

def get_scenario_definition(scenario_id: str) -> dict:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unknown scenario ID: {scenario_id}")
    return SCENARIOS[scenario_id]
