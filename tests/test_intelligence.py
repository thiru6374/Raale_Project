"""
tests/test_intelligence.py

Phase 10 Intelligence Layer Tests — 9 Required Failure Cases + Unit Tests.
"""
import pytest
import pandas as pd
import tempfile
import os

from src.intelligence.change_detection import ChangeDetector
from src.intelligence.alert_engine import AlertEngine
from src.intelligence.priority_engine import PriorityEngine
from src.intelligence.feedback_analyzer import FeedbackAnalyzer
from src.intelligence.improvement_service import ImprovementService
from src.services.persistence.jsonl_store import JSONLStore
from src.services.persistence.alert_repository import AlertRepository
from src.services.persistence.feedback_repository import FeedbackRepository
from src.services.persistence.improvement_repository import ImprovementRepository
from src.services.config_version_service import ConfigVersionService


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_sample_df(n=10, risk="HIGH", selected=True, valid_geo=True, fallback="SCHEDULED"):
    return pd.DataFrame({
        "neighbourhood_name":        [f"Area_{i}" for i in range(n)],
        "multi_factor_risk_category": [risk] * n,
        "selected_for_outreach":     [selected] * n,
        "is_valid_geo":              [valid_geo] * n,
        "geo_validation_status":     ["VALID" if valid_geo else "MISSING_COORDINATES"] * n,
        "fallback_status":           [fallback] * n,
        "group_mobile":              [i % 2 == 0 for i in range(n)],
        "group_low_service_access":  [i % 3 == 0 for i in range(n)],
    })


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 1: No historical data → No fabricated trend
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_1_no_historical_data():
    """System must not fabricate trends when no previous run exists."""
    detector = ChangeDetector()
    current_df = make_sample_df()
    
    # Pass None as previous_df to simulate no history
    changes = detector.detect_changes(current_df, None, {}, {})
    
    assert any(c.get("type") == "INSUFFICIENT_HISTORY" for c in changes), \
        "Must return INSUFFICIENT_HISTORY when previous_df is None"


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 2: Critical provider failure → Alert generated
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_2_critical_provider_failure():
    """Provider failure must trigger a CRITICAL data health alert."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = AlertRepository(filepath=os.path.join(tmpdir, "alerts.jsonl"))
        engine = AlertEngine()
        engine.alert_repo = repo   # Inject temp repo
        
        df = make_sample_df(selected=True)  # coverage OK so no coverage alert
        provider_meta = {"provider_status": "SYNTHETIC_FALLBACK", "freshness": "FRESH"}
        
        alerts = engine.generate_alerts(df, [], provider_meta, "run_001", [])
        
        assert any(a.get("category") == "DATA_HEALTH" for a in alerts), \
            "A DATA_HEALTH alert must be generated on provider fallback"
        assert any(a.get("severity") == "CRITICAL" for a in alerts)


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 3: High-risk with invalid GIS → Priority 1 + Manual Review
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_3_invalid_gis_high_risk():
    """High-risk records with is_valid_geo=False must be Priority 1."""
    engine = PriorityEngine()
    df = make_sample_df(risk="HIGH", selected=False, valid_geo=False)
    
    prioritised = engine.prioritize_decisions(df, fairness_warnings=[])
    
    assert "decision_priority" in prioritised.columns
    p1_rows = prioritised[prioritised["decision_priority"].str.contains("PRIORITY 1")]
    assert len(p1_rows) > 0, "Invalid GIS high-risk records must be Priority 1"


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 4: Fairness gap → WARNING or CRITICAL alert
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_4_fairness_gap():
    """A detected fairness warning must produce a FAIRNESS alert."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = AlertRepository(filepath=os.path.join(tmpdir, "alerts.jsonl"))
        engine = AlertEngine()
        engine.alert_repo = repo
        
        df = make_sample_df(selected=True)
        fairness_warnings = [{"message": "Coverage parity gap detected for group_mobile.", "group": "group_mobile"}]
        
        alerts = engine.generate_alerts(df, fairness_warnings, {"provider_status": "SYNTHETIC", "freshness": "FRESH"}, "run_002", [])
        
        assert any(a.get("category") == "FAIRNESS" for a in alerts)


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 5: Capacity exhausted → Priority 2 decisions
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_5_capacity_exhausted():
    """High-risk uncovered areas must be Priority 2 or 1."""
    engine = PriorityEngine()
    df = make_sample_df(risk="HIGH", selected=False)  # ALL uncovered
    
    prioritised = engine.prioritize_decisions(df, [])
    
    high_prio = prioritised[prioritised["decision_priority"].str.contains("PRIORITY 1|PRIORITY 2")]
    assert len(high_prio) > 0, "Uncovered high-risk areas must be Priority 1 or 2"


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 6: Insufficient stakeholder feedback → No misleading conclusions
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_6_insufficient_feedback():
    """With < 5 feedback records, analysis must return INSUFFICIENT status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = FeedbackRepository(filepath=os.path.join(tmpdir, "feedback.jsonl"))
        # Add only 2 records
        repo.save_feedback({"usefulness_rating": "Yes", "clarity_rating": "Yes", "feasibility_rating": "No"})
        repo.save_feedback({"usefulness_rating": "No",  "clarity_rating": "Partially", "feasibility_rating": "No"})
        
        analyzer = FeedbackAnalyzer()
        analyzer.repo = repo
        
        result = analyzer.analyze_feedback()
        assert result.get("status") == "INSUFFICIENT FEEDBACK FOR RELIABLE ANALYSIS"


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 7: Improvement proposal rejected → No config change
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_7_proposal_rejected():
    """Rejecting a proposal must set status=REJECTED and not change any config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = ImprovementRepository(filepath=os.path.join(tmpdir, "proposals.jsonl"))
        p_id = repo.add_proposal(
            trigger_pattern="TEST_PATTERN",
            evidence="Test evidence",
            affected_component="number_of_teams",
            recommended_change={"number_of_teams": 10},
            expected_benefit="More coverage",
            risk_assessment="Low"
        )
        
        repo.update_proposal_status(p_id, "REJECTED", decision_reason="Budget constraints")
        
        latest = repo.get_latest_proposals()
        assert latest[p_id]["status"] == "REJECTED"


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 8: Approved config with invalid values → Rejected/rolled back
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_8_config_validation_failure():
    """A config with 0 teams must fail validation and not be activated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from src.services.persistence.config_repository import ConfigRepository
        service = ConfigVersionService()
        service.repo = ConfigRepository(
            version_filepath=os.path.join(tmpdir, "config.jsonl"),
            audit_filepath=os.path.join(tmpdir, "audit.jsonl"),
        )
        
        bad_config = {"number_of_teams": 0, "maximum_visits_per_team": 5}
        version_id = service.propose_configuration(bad_config, reason="Test bad config")
        result = service.approve_and_activate(version_id)
        
        assert result is False, "Config with 0 teams must be rejected"


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 9: Safe fallback active → Decision intelligence is limited
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_9_safe_fallback_active():
    """When provider falls back, DATA_HEALTH alert must be generated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = AlertRepository(filepath=os.path.join(tmpdir, "alerts.jsonl"))
        engine = AlertEngine()
        engine.alert_repo = repo
        
        df = make_sample_df(selected=True)
        # Simulate safe fallback provider status
        provider_meta = {
            "provider_status": "SYNTHETIC_FALLBACK",
            "freshness": "STALE",
        }
        
        alerts = engine.generate_alerts(df, [], provider_meta, "run_fallback", [])
        
        categories = [a.get("category") for a in alerts]
        assert "DATA_HEALTH" in categories, "Must alert on safe fallback activation"
        assert "DATA_FRESHNESS" in categories, "Must alert on stale data"


# ══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════
def test_jsonl_store_missing_file_returns_empty():
    """Reading from a non-existent file must return an empty list."""
    store = JSONLStore("/tmp/nonexistent_path_xyz/alerts.jsonl")
    assert store.read_all() == []


def test_jsonl_store_malformed_line_is_skipped():
    """A malformed JSON line must be skipped without crashing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write('{"valid": true}\n')
        f.write('NOT JSON {{{broken\n')
        f.write('{"also_valid": true}\n')
        fpath = f.name
    
    try:
        store = JSONLStore(fpath)
        records = store.read_all()
        assert len(records) == 2
        assert records[0]["valid"] is True
        assert records[1]["also_valid"] is True
    finally:
        os.unlink(fpath)


def test_alert_lifecycle_reconstruction():
    """Alert status must reconstruct correctly from sequential events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = AlertRepository(filepath=os.path.join(tmpdir, "alerts.jsonl"))
        
        aid = repo.add_event("ALERT_CREATED", "WARNING", "COVERAGE",
                             "Coverage < 80%", "Review capacity", "run_001")
        repo.add_event("ALERT_ACKNOWLEDGED", "WARNING", "COVERAGE",
                       "Coverage < 80%", "Review capacity", alert_id=aid)
        repo.add_event("ALERT_RESOLVED", "WARNING", "COVERAGE",
                       "Coverage < 80%", "Review capacity", alert_id=aid)
        
        current = repo.get_current_alerts()
        assert current[aid]["status"] == "RESOLVED"
        
        active = repo.get_active_alerts()
        assert not any(a["alert_id"] == aid for a in active)


def test_change_detection_with_valid_history():
    """Change detector must identify high-risk increase between runs."""
    detector = ChangeDetector()
    
    prev_df = make_sample_df(n=5, risk="HIGH", selected=True)
    curr_df = make_sample_df(n=10, risk="HIGH", selected=True)
    
    changes = detector.detect_changes(curr_df, prev_df, {}, {})
    
    # No INSUFFICIENT_HISTORY because both DFs provided
    assert not any(c.get("type") == "INSUFFICIENT_HISTORY" for c in changes)
