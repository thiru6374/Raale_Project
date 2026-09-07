"""
tests/test_phase12_intelligence.py

Tests for Phase 12 Final Decision Intelligence, Adaptive Communication,
and Outcome Tracking.
"""
import pytest
import os
import tempfile
from src.services.communication_intelligence_service import CommunicationIntelligenceService
from src.services.decision_intelligence_service import DecisionIntelligenceService
from src.services.outcome_tracking_service import OutcomeTrackingService
from src.services.kpi_service import KPIService

def test_communication_intelligence_high_risk():
    nbhd = {
        "neighbourhood_id": "NH_001",
        "multi_factor_risk_category": "HIGH",
        "selected_for_outreach": True,
        "mobile_population_density": 0.8
    }
    
    rec = CommunicationIntelligenceService.generate_recommendation(
        nbhd, "run1", "v12", "trace1"
    )
    
    assert rec["priority"] == "CRITICAL"
    assert "CRITICAL:" in rec["communication_message"]["action"]
    assert "mobile" in rec["communication_message"]["action"].lower()
    
def test_communication_intelligence_low_risk():
    nbhd = {
        "neighbourhood_id": "NH_002",
        "multi_factor_risk_category": "LOW",
        "selected_for_outreach": False
    }
    
    rec = CommunicationIntelligenceService.generate_recommendation(
        nbhd, "run1", "v12", "trace2"
    )
    
    assert rec["priority"] == "LOW"
    assert "Stay safe during hot weather" in rec["communication_message"]["action"]

def test_decision_intelligence_fallback_activation():
    nbhds = [{"neighbourhood_id": "NH_001", "multi_factor_risk_category": "HIGH", "fallback_status": "NORMAL"}]
    
    decisions = DecisionIntelligenceService.generate_final_decisions(
        nbhds,
        system_health_status="CRITICAL",
        alerts=[],
        pipeline_run_id="r1",
        config_version="v12"
    )
    
    assert len(decisions) == 1
    assert decisions[0]["fallback_status"] == "FALLBACK_ACTIVATED"
    assert decisions[0]["priority"] == "MANUAL_REVIEW_REQUIRED"

def test_decision_intelligence_critical_alerts():
    nbhds = [{"neighbourhood_id": "NH_001", "multi_factor_risk_category": "HIGH", "fallback_status": "NORMAL"}]
    alerts = [{"severity": "CRITICAL", "status": "OPEN"}]
    
    decisions = DecisionIntelligenceService.generate_final_decisions(
        nbhds,
        system_health_status="HEALTHY",
        alerts=alerts,
        pipeline_run_id="r1",
        config_version="v12"
    )
    
    assert decisions[0]["fallback_status"] == "FALLBACK_ACTIVATED"

def test_outcome_tracking_lifecycle():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        fpath = f.name
        
    try:
        tracker = OutcomeTrackingService(filepath=fpath)
        
        rec = {
            "recommendation_id": "rec1",
            "neighbourhood_id": "NH_001",
            "priority": "HIGH",
            "pipeline_run_id": "run1"
        }
        
        tracker.log_recommendation_generated(rec)
        tracker.update_status("rec1", "PLANNED")
        tracker.update_status("rec1", "COMPLETED")
        
        status_map = tracker.get_latest_status_map()
        assert status_map["rec1"] == "COMPLETED"
    finally:
        os.unlink(fpath)

def test_kpi_calculation():
    recs = [
        {"risk_level": "HIGH", "priority": "CRITICAL", "fallback_status": "NORMAL"},
        {"risk_level": "HIGH", "priority": "LOW", "fallback_status": "FALLBACK_ACTIVATED"},
        {"risk_level": "LOW", "priority": "LOW", "fallback_status": "NORMAL"}
    ]
    
    outcome_map = {
        "r1": "COMPLETED",
        "r2": "PLANNED"
    }
    
    fairness = {"disparity": 0.05}
    
    kpis = KPIService.calculate_kpis(
        recommendations=recs,
        outcome_status_map=outcome_map,
        fairness_results=fairness,
        system_health="HEALTHY",
        capacity_used=1,
        capacity_total=2
    )
    
    assert kpis["risk_coverage_rate"] == 0.5  # 1 out of 2 HIGH risk areas reached
    assert kpis["capacity_utilization"] == 0.5
    assert kpis["action_completion_rate"] == 0.5 # 1 completed out of 2 planned/completed
    assert kpis["system_trust_rate"] == pytest.approx(0.666, 0.01) # 2/3 trusted
    assert kpis["fallback_rate"] == pytest.approx(0.333, 0.01)
    assert kpis["fairness_gap"] == 0.05
    assert kpis["missed_high_risk_areas"] == 1
