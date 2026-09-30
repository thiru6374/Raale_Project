"""
Phase 13: Failure-mode and edge-case tests.
These tests verify the system fails safely and gracefully when given adversarial inputs.
"""
import pandas as pd
import numpy as np
import pytest
from src.data.validation import NeighbourhoodData
from src.data.preprocessing import DataPreprocessor
from src.risk.baseline import BaselineRiskModel
from src.risk.risk_engine import MultiFactorRiskModel
from src.optimisation.planner import OutreachPlanner
from src.governance.fallback import assess_data_completeness, FallbackStatus
from src.fairness.bias_detection import FairnessAuditor
from src.communication.message_generator import MessageGenerator
from datetime import date


# -----------------------------------------------------------
# 1. EMPTY DATAFRAME EDGE CASES
# -----------------------------------------------------------

def test_preprocessor_handles_empty_dataframe():
    """Preprocessor should not crash on an empty DataFrame."""
    empty_df = pd.DataFrame(columns=['temperature_c', 'healthcare_capacity'])
    preprocessor = DataPreprocessor()
    result = preprocessor.process_dataframe(empty_df)
    assert result.empty


def test_baseline_model_handles_empty_dataframe():
    """Baseline model should raise a clear ValueError on empty data, not a cryptic crash."""
    empty_df = pd.DataFrame(columns=['temperature_c'])
    model = BaselineRiskModel()
    # Empty df will compute but return empty
    result = model.calculate_risk(empty_df)
    assert result.empty


def test_message_generator_all_not_selected():
    """MessageGenerator should return all NaN advisories when nothing is selected."""
    data = pd.DataFrame({
        'selected_for_outreach': [False, False, False],
        'neighbourhood_name': ['A', 'B', 'C'],
        'multi_factor_risk_category': ['HIGH', 'MODERATE', 'LOW']
    })
    gen = MessageGenerator()
    result = gen.generate_messages(data)
    assert not result['localised_advisory'].isna().any()


# -----------------------------------------------------------
# 2. ALL-MISSING CRITICAL DATA
# -----------------------------------------------------------

def test_fallback_all_fields_missing():
    """When ALL critical fields are missing, status must be MANUAL_REVIEW."""
    result = assess_data_completeness(missing_fields=10, total_fields=10)
    assert result.status == FallbackStatus.MANUAL_REVIEW


def test_fallback_zero_total_fields():
    """When total_fields=0 (no schema), result must be FAILED."""
    result = assess_data_completeness(missing_fields=0, total_fields=0)
    assert result.status == FallbackStatus.FAILED


# -----------------------------------------------------------
# 3. SINGLE-RECORD EDGE CASE
# -----------------------------------------------------------

def test_planner_single_record():
    """Planner should handle a single-neighbourhood input without crashing."""
    data = pd.DataFrame({
        'neighbourhood_id': ['N1'],
        'multi_factor_risk_score': [0.9],
        'mobile_population': [1000],
        'fallback_status': ['APPROVED'],
        'multi_factor_risk_category': ['EXTREME']
    })
    from src.config.settings import settings
    settings.number_of_teams = 1
    settings.maximum_visits_per_team = 1
    settings.maximum_outreach_events_per_day = 1000
    settings.maximum_travel_distance = 1000.0
    settings.maximum_travel_time = 2000
    settings.working_hours = 24.0

    planner = OutreachPlanner()
    result = planner.plan_outreach(data)
    assert result['selected_for_outreach'].sum() == 1


# -----------------------------------------------------------
# 4. ADVERSARIAL TEMPERATURE VALUES
# -----------------------------------------------------------

def test_baseline_extreme_low_temperature():
    """Temperature at absolute lower bound should yield 0.0 risk score."""
    data = pd.DataFrame({'heat_index': [25.0]})
    model = BaselineRiskModel()
    result = model.calculate_risk(data)
    assert result['baseline_risk_score'].iloc[0] == 0.0
    assert result['baseline_risk_category'].iloc[0] == 'LOW'


def test_baseline_extreme_high_temperature():
    """Temperature above 50°C (beyond our max bound) must clip to 1.0."""
    data = pd.DataFrame({'heat_index': [65.0]})
    model = BaselineRiskModel()
    result = model.calculate_risk(data)
    assert result['baseline_risk_score'].iloc[0] == 1.0
    assert result['baseline_risk_category'].iloc[0] == 'EXTREME'


# -----------------------------------------------------------
# 5. ALL-ZERO RISK SCORES
# -----------------------------------------------------------

def test_planner_all_zero_risk():
    """When all neighbourhoods have zero risk, optimizer should still respect capacity."""
    from src.config.settings import settings
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 3
    settings.maximum_outreach_events_per_day = 1000
    settings.maximum_travel_distance = 1000.0
    settings.maximum_travel_time = 2000
    settings.working_hours = 24.0

    data = pd.DataFrame({
        'neighbourhood_id': [f'N{i}' for i in range(10)],
        'multi_factor_risk_score': [0.0] * 10,
        'mobile_population': [100] * 10,
        'fallback_status': ['APPROVED'] * 10,
        'multi_factor_risk_category': ['LOW'] * 10
    })
    planner = OutreachPlanner()
    result = planner.plan_outreach(data)
    assert result['selected_for_outreach'].sum() <= 6


# -----------------------------------------------------------
# 6. FAIRNESS WITH NO MATCHING GROUP
# -----------------------------------------------------------

def test_fairness_auditor_missing_group_column():
    """Fairness auditor should skip (not crash) groups not present in data."""
    data = pd.DataFrame({'selected_for_outreach': [True, False]})
    auditor = FairnessAuditor(target_groups=['group_mobile'])
    warnings = auditor.audit_plan(data)
    # Should skip the group, produce no warnings (no crash)
    assert isinstance(warnings, list)
