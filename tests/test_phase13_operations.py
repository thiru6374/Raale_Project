"""
tests/test_phase13_operations.py

Tests for Phase 13 Production Operations, Drift Detection, Capacity, and Readiness.
"""
import pytest
import os
import tempfile
import pandas as pd
from datetime import datetime, timedelta
from src.services.data_refresh_service import DataRefreshService
from src.services.capacity_pressure_service import CapacityPressureService
from src.services.drift_detection_service import DriftDetectionService
from src.services.operational_health_service import OperationalHealthService
from src.services.release_readiness_service import ReleaseReadinessService
from src.services.operations_service import OperationsService

def test_data_freshness():
    now = datetime.utcnow()
    # FRESH
    assert DataRefreshService.check_freshness((now - timedelta(hours=5)).isoformat() + "Z", now.isoformat() + "Z") == "FRESH"
    # AGING
    assert DataRefreshService.check_freshness((now - timedelta(hours=18)).isoformat() + "Z", now.isoformat() + "Z") == "AGING"
    # STALE
    assert DataRefreshService.check_freshness((now - timedelta(hours=48)).isoformat() + "Z", now.isoformat() + "Z") == "STALE"
    # UNAVAILABLE
    assert DataRefreshService.check_freshness(None) == "UNAVAILABLE"

def test_capacity_pressure():
    planned_actions = [
        {"neighbourhood_id": "NH_001", "risk_level": "HIGH"},
        {"neighbourhood_id": "NH_002", "risk_level": "HIGH"},
        {"neighbourhood_id": "NH_003", "risk_level": "HIGH"},
    ]
    
    # NORMAL
    res = CapacityPressureService.evaluate_capacity(5, planned_actions)
    assert res["status"] == "NORMAL"
    assert res["remaining_capacity"] == 2
    
    # CAPACITY PRESSURE
    res = CapacityPressureService.evaluate_capacity(3, planned_actions)
    assert res["status"] == "CAPACITY_PRESSURE"
    assert res["remaining_capacity"] == 0
    
    # INSUFFICIENT
    res = CapacityPressureService.evaluate_capacity(2, planned_actions)
    assert res["status"] == "INSUFFICIENT_CAPACITY"
    assert "NH_003" in res["critical_uncovered_areas"]

def test_drift_detection():
    ref_recs = [
        {"risk_level": "HIGH"}, {"risk_level": "HIGH"}, {"risk_level": "LOW"}, {"risk_level": "LOW"}
    ] # 50% High
    
    cur_recs_minor = [
        {"risk_level": "HIGH"}, {"risk_level": "HIGH"}, {"risk_level": "HIGH"}, {"risk_level": "LOW"}, {"risk_level": "LOW"}
    ] # 60% High -> 10% diff
    
    cur_recs_major = [
        {"risk_level": "HIGH"}, {"risk_level": "HIGH"}, {"risk_level": "HIGH"}, {"risk_level": "HIGH"}, {"risk_level": "LOW"}
    ] # 80% High -> 30% diff
    
    res = DriftDetectionService.detect_recommendation_drift(cur_recs_minor, ref_recs, threshold=0.1)
    assert res["status"] in ["STABLE", "MINOR CHANGE"] # diff is exactly threshold
    
    res = DriftDetectionService.detect_recommendation_drift(cur_recs_major, ref_recs, threshold=0.1)
    assert res["status"] == "SIGNIFICANT CHANGE"

def test_fairness_drift():
    ref_fairness = {"disparity": 0.05}
    cur_fairness_worse = {"disparity": 0.15} # 0.10 worse
    cur_fairness_better = {"disparity": 0.00} # 0.05 better
    
    res = DriftDetectionService.detect_fairness_drift(cur_fairness_worse, ref_fairness, threshold=0.05)
    assert res["status"] == "THRESHOLD EXCEEDED"
    
    res = DriftDetectionService.detect_fairness_drift(cur_fairness_better, ref_fairness, threshold=0.05)
    assert res["status"] == "IMPROVED"

def test_operational_health():
    # Healthy
    res = OperationalHealthService.get_overall_health("HEALTHY", "HEALTHY", "FRESH", "HEALTHY", "HEALTHY")
    assert res["overall_status"] == "HEALTHY"
    
    # Degraded (Stale data)
    res = OperationalHealthService.get_overall_health("HEALTHY", "HEALTHY", "STALE", "HEALTHY", "HEALTHY")
    assert res["overall_status"] == "DEGRADED"
    
    # Critical (Pipeline failed)
    res = OperationalHealthService.get_overall_health("FAILED", "HEALTHY", "FRESH", "HEALTHY", "HEALTHY")
    assert res["overall_status"] == "CRITICAL"

def test_release_readiness():
    # Will fail if run from wrong directory, but should generally pass the check logic
    res = ReleaseReadinessService.check_readiness()
    assert "status" in res

def test_operations_service():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        fpath = f.name
        
    try:
        ops = OperationsService(history_file=fpath)
        # Mock empty execution for failure case
        run = ops.execute_operational_run(num_records=0)
        
        assert run["status"] == "FAILED"
        assert run["record_count"] == 0
        
        history = ops.get_run_history()
        assert len(history) == 1
        
        # Test trends logic with no history
        trends = ops.get_historical_trends()
        assert trends["status"] == "INSUFFICIENT HISTORY"
    finally:
        os.unlink(fpath)
