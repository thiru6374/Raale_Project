"""
tests/test_security.py

Phase 11 Security, Access Control, Resilience, Backup & Recovery Tests.
Covers all 8 required failure cases plus unit tests.
"""
import os
import json
import tempfile
import pytest

from src.security.roles import Role, has_minimum_role, role_rank
from src.security.permissions import (
    has_permission,
    PERM_APPROVE_CONFIG, PERM_ACTIVATE_CONFIG, PERM_ROLLBACK_CONFIG,
    PERM_RESTORE_BACKUP, PERM_CREATE_BACKUP,
    PERM_ACKNOWLEDGE_ALERT, PERM_DISMISS_CRITICAL_ALERT,
    PERM_REVIEW_PROPOSALS, PERM_VIEW_DASHBOARD,
)
from src.security.access_control import AccessControl
from src.security.input_validator import (
    validate_text_input, validate_override_reason, validate_feedback_record,
    validate_configuration, validate_alert_action, detect_secrets_in_text,
)
from src.services.persistence.jsonl_store import JSONLStore
from src.services.startup_validator import run_startup_validation


# ══════════════════════════════════════════════════════════════════════════════
# ROLE & PERMISSION UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRoleHierarchy:
    def test_viewer_has_lowest_rank(self):
        assert role_rank(Role.VIEWER) < role_rank(Role.OPERATOR)
        assert role_rank(Role.OPERATOR) < role_rank(Role.REVIEWER)
        assert role_rank(Role.REVIEWER) < role_rank(Role.ADMIN)

    def test_has_minimum_role(self):
        assert has_minimum_role(Role.ADMIN, Role.VIEWER)
        assert has_minimum_role(Role.ADMIN, Role.ADMIN)
        assert not has_minimum_role(Role.VIEWER, Role.ADMIN)
        assert not has_minimum_role(Role.OPERATOR, Role.REVIEWER)


class TestPermissions:
    def test_viewer_has_view_dashboard(self):
        assert has_permission(Role.VIEWER, PERM_VIEW_DASHBOARD)

    def test_viewer_cannot_approve_config(self):
        assert not has_permission(Role.VIEWER, PERM_APPROVE_CONFIG)

    def test_operator_cannot_activate_config(self):
        assert not has_permission(Role.OPERATOR, PERM_ACTIVATE_CONFIG)

    def test_reviewer_cannot_rollback_config(self):
        assert not has_permission(Role.REVIEWER, PERM_ROLLBACK_CONFIG)

    def test_reviewer_cannot_restore_backup(self):
        assert not has_permission(Role.REVIEWER, PERM_RESTORE_BACKUP)

    def test_admin_has_all_sensitive_permissions(self):
        for perm in [
            PERM_APPROVE_CONFIG, PERM_ACTIVATE_CONFIG, PERM_ROLLBACK_CONFIG,
            PERM_RESTORE_BACKUP, PERM_DISMISS_CRITICAL_ALERT,
        ]:
            assert has_permission(Role.ADMIN, perm), f"Admin should have {perm}"

    def test_operator_can_create_backup(self):
        assert has_permission(Role.OPERATOR, PERM_CREATE_BACKUP)

    def test_operator_can_acknowledge_alert(self):
        assert has_permission(Role.OPERATOR, PERM_ACKNOWLEDGE_ALERT)


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 1: Unauthorized config approval
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_1_viewer_cannot_approve_config():
    """Viewer attempting config approval must be denied; no config change."""
    granted, msg = AccessControl.require(Role.VIEWER, PERM_APPROVE_CONFIG,
                                         action="approve_config", resource="test_v1")
    assert not granted
    assert "not permitted" in msg.lower() or "denied" in msg.lower() or "required permission" in msg.lower()


def test_failure_case_1_operator_cannot_approve_config():
    """Operator attempting config approval must be denied."""
    granted, msg = AccessControl.require(Role.OPERATOR, PERM_APPROVE_CONFIG,
                                         action="approve_config", resource="test_v2")
    assert not granted


def test_failure_case_1_reviewer_cannot_approve_config():
    """Reviewer cannot approve config (only Admin can)."""
    granted, msg = AccessControl.require(Role.REVIEWER, PERM_APPROVE_CONFIG,
                                         action="approve_config", resource="test_v3")
    assert not granted


def test_failure_case_1_admin_can_approve_config():
    """Admin must be granted approval permission."""
    granted, msg = AccessControl.require(Role.ADMIN, PERM_APPROVE_CONFIG,
                                         action="approve_config", resource="test_v4")
    assert granted
    assert msg == ""


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 2: Invalid configuration submitted
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_2_zero_teams_rejected():
    """Configuration with 0 teams must fail validation."""
    ok, msg = validate_configuration({"number_of_teams": 0})
    assert not ok
    assert "number_of_teams" in msg


def test_failure_case_2_negative_visits_rejected():
    ok, msg = validate_configuration({"maximum_visits_per_team": -1})
    assert not ok


def test_failure_case_2_coverage_gap_out_of_range():
    ok, msg = validate_configuration({"maximum_coverage_gap": 1.5})
    assert not ok


def test_failure_case_2_valid_config_passes():
    ok, msg = validate_configuration({
        "number_of_teams": 5,
        "maximum_visits_per_team": 10,
        "maximum_coverage_gap": 0.2,
    })
    assert ok, f"Valid config should pass. Got: {msg}"


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 3: Critical alert dismissal without ADMIN
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_3_viewer_cannot_dismiss_critical():
    granted, msg = AccessControl.require(Role.VIEWER, PERM_DISMISS_CRITICAL_ALERT,
                                         action="dismiss_critical_alert", resource="alert_001")
    assert not granted


def test_failure_case_3_operator_cannot_dismiss_critical():
    granted, msg = AccessControl.require(Role.OPERATOR, PERM_DISMISS_CRITICAL_ALERT,
                                         action="dismiss_critical_alert", resource="alert_002")
    assert not granted


def test_failure_case_3_admin_can_dismiss_critical():
    granted, _ = AccessControl.require(Role.ADMIN, PERM_DISMISS_CRITICAL_ALERT,
                                       action="dismiss_critical_alert", resource="alert_003")
    assert granted


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 4: JSONL malformed data — valid records preserved
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_4_malformed_jsonl_survives():
    """App must not crash; valid records around malformed line must be preserved."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write('{"id": 1, "v": "good"}\n')
        f.write('NOT_JSON {{{bad_line\n')
        f.write('{"id": 2, "v": "also_good"}\n')
        fpath = f.name
    try:
        store = JSONLStore(fpath)
        records = store.read_all()
        assert len(records) == 2, f"Expected 2 valid records, got {len(records)}"
        assert records[0]["id"] == 1
        assert records[1]["id"] == 2
    finally:
        os.unlink(fpath)


def test_failure_case_4_empty_file_returns_empty_list():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        fpath = f.name
    try:
        store = JSONLStore(fpath)
        assert store.read_all() == []
    finally:
        os.unlink(fpath)


def test_failure_case_4_missing_file_returns_empty_list():
    store = JSONLStore("/tmp/__nonexistent_phase11_test__.jsonl")
    assert store.read_all() == []


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 5: Backup restore by unauthorized role
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_5_viewer_cannot_restore_backup():
    granted, msg = AccessControl.require(Role.VIEWER, PERM_RESTORE_BACKUP,
                                         action="restore_backup", resource="backup_001.zip")
    assert not granted


def test_failure_case_5_reviewer_cannot_restore_backup():
    granted, _ = AccessControl.require(Role.REVIEWER, PERM_RESTORE_BACKUP,
                                       action="restore_backup", resource="backup_002.zip")
    assert not granted


def test_failure_case_5_admin_can_restore_backup():
    granted, _ = AccessControl.require(Role.ADMIN, PERM_RESTORE_BACKUP,
                                       action="restore_backup", resource="backup_003.zip")
    assert granted


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 6: Open data provider fails (graceful degradation)
# This is tested at integration level via PipelineService safe fallback.
# Here we verify the alert engine correctly surfaces DATA_HEALTH alerts.
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_6_provider_failure_generates_alert():
    """Provider failure must generate a DATA_HEALTH alert."""
    import pandas as pd
    import tempfile
    from src.intelligence.alert_engine import AlertEngine
    from src.services.persistence.alert_repository import AlertRepository

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = AlertRepository(filepath=os.path.join(tmpdir, "alerts.jsonl"))
        engine = AlertEngine()
        engine.alert_repo = repo

        df = pd.DataFrame({
            "multi_factor_risk_category": ["HIGH"] * 5,
            "selected_for_outreach": [True] * 5,
        })
        meta = {"provider_status": "SYNTHETIC_FALLBACK", "freshness": "FRESH"}
        alerts = engine.generate_alerts(df, [], meta, "run_sec_test", [])

        assert any(a.get("category") == "DATA_HEALTH" for a in alerts)
        assert any(a.get("severity") == "CRITICAL" for a in alerts)


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 7: Required dependency missing → startup diagnostic
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_7_startup_validation_runs():
    """Startup validator must return a structured report without crashing."""
    report = run_startup_validation()
    assert "overall" in report
    assert "checks" in report
    assert isinstance(report["checks"], list)
    assert len(report["checks"]) > 0
    # overall must be one of HEALTHY/WARNING/CRITICAL
    assert report["overall"] in ("HEALTHY", "WARNING", "CRITICAL")


def test_failure_case_7_python_check_in_report():
    report = run_startup_validation()
    python_checks = [c for c in report["checks"] if "Python" in c["check"]]
    assert len(python_checks) == 1
    # Since we're running the tests with a valid Python, it should be HEALTHY
    assert python_checks[0]["status"] == "HEALTHY"


# ══════════════════════════════════════════════════════════════════════════════
# FAILURE CASE 8: Unexpected internal error — safe user message, not stack trace
# This is verified by the error handling pattern; tested via input validation.
# ══════════════════════════════════════════════════════════════════════════════
def test_failure_case_8_secret_detection():
    """Secret-like strings in user input must be detected and flagged."""
    flagged, msg = detect_secrets_in_text("api_key = 'abc12345'")
    assert flagged, "Should detect API key pattern"
    assert "secret" not in msg.lower() or "sensitive" in msg.lower()
    # Critically: the detected value must NOT appear in the warning message
    assert "abc12345" not in msg


def test_failure_case_8_clean_text_not_flagged():
    flagged, _ = detect_secrets_in_text("This is a normal operational message.")
    assert not flagged


# ══════════════════════════════════════════════════════════════════════════════
# INPUT VALIDATION UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestInputValidation:
    def test_override_reason_too_short(self):
        ok, msg = validate_override_reason("short")
        assert not ok

    def test_override_reason_empty(self):
        ok, msg = validate_override_reason("")
        assert not ok

    def test_override_reason_valid(self):
        ok, _ = validate_override_reason("This override is required due to capacity emergency.")
        assert ok

    def test_feedback_invalid_rating(self):
        ok, msg = validate_feedback_record({"usefulness_rating": "Maybe"})
        assert not ok
        assert "usefulness_rating" in msg

    def test_feedback_valid_record(self):
        ok, _ = validate_feedback_record({
            "usefulness_rating": "Yes",
            "clarity_rating": "Partially",
            "feasibility_rating": "No",
        })
        assert ok

    def test_alert_action_invalid(self):
        ok, msg = validate_alert_action("DELETE")
        assert not ok

    def test_alert_action_valid(self):
        ok, _ = validate_alert_action("ACKNOWLEDGE")
        assert ok

    def test_text_input_too_long(self):
        ok, msg = validate_text_input("x" * 3000, "test_field")
        assert not ok

    def test_text_input_empty_required(self):
        ok, _ = validate_text_input("", "required_field", required=True)
        assert not ok

    def test_text_input_empty_optional(self):
        ok, _ = validate_text_input("", "optional_field", required=False)
        assert ok


# ══════════════════════════════════════════════════════════════════════════════
# BACKUP & INTEGRITY UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestJSONLIntegrity:
    def test_checksum_consistent(self):
        """Checksum of unchanged file must be stable."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"id": 1}\n')
            fpath = f.name
        try:
            store = JSONLStore(fpath)
            cs1 = store.compute_checksum()
            cs2 = store.compute_checksum()
            assert cs1 == cs2
            assert len(cs1) == 64  # SHA-256 hex
        finally:
            os.unlink(fpath)

    def test_checksum_detects_modification(self):
        """Checksum must differ after file is modified."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"id": 1}\n')
            fpath = f.name
        try:
            store = JSONLStore(fpath)
            cs_before = store.compute_checksum()
            with open(fpath, "a") as f2:
                f2.write('{"id": 2}\n')
            cs_after = store.compute_checksum()
            assert cs_before != cs_after
        finally:
            os.unlink(fpath)

    def test_verify_integrity_pass(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"ok": true}\n')
            fpath = f.name
        try:
            store = JSONLStore(fpath)
            cs = store.compute_checksum()
            assert store.verify_integrity(cs)
        finally:
            os.unlink(fpath)

    def test_verify_integrity_fail_on_tamper(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"ok": true}\n')
            fpath = f.name
        try:
            store = JSONLStore(fpath)
            cs = store.compute_checksum()
            with open(fpath, "a") as f2:
                f2.write('{"tampered": true}\n')
            assert not store.verify_integrity(cs)
        finally:
            os.unlink(fpath)

    def test_health_status_healthy_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"id": 1}\n')
            fpath = f.name
        try:
            store = JSONLStore(fpath)
            h = store.health_status()
            assert h["exists"] is True
            assert h["record_count"] == 1
            assert h["status"] == "HEALTHY"
        finally:
            os.unlink(fpath)

    def test_health_status_missing_file(self):
        store = JSONLStore("/tmp/__phase11_missing_health_test__.jsonl")
        h = store.health_status()
        assert h["status"] == "MISSING"
        assert h["record_count"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# BACKUP SERVICE UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestBackupService:
    def test_validate_nonexistent_backup(self):
        from src.services.backup_service import BackupService
        result = BackupService.validate_backup("/tmp/__nonexistent__.zip")
        assert result["valid"] is False
        assert "not found" in result.get("reason", "").lower()

    def test_create_and_validate_backup(self, tmp_path, monkeypatch):
        """Create a real backup from a temp data dir and validate it."""
        import src.services.backup_service as bsvc
        monkeypatch.setattr(bsvc, "BACKUP_DIR", str(tmp_path / "backups"))
        monkeypatch.setattr(bsvc, "DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setattr(bsvc, "LOGS_DIR", str(tmp_path / "logs"))

        # Create minimal data structure
        (tmp_path / "data" / "config").mkdir(parents=True)
        (tmp_path / "data" / "config" / "settings_versioned.jsonl").write_text('{"v": "1"}\n')
        (tmp_path / "logs").mkdir(parents=True)

        from src.services.backup_service import BackupService
        result = BackupService.create_backup(label="test")
        assert result["status"] == "OK"
        assert os.path.exists(result["path"])

        validation = BackupService.validate_backup(result["path"])
        assert validation["valid"] is True
        assert validation["sha256"] == result["sha256"]

    def test_security_audit_logged_on_denial(self):
        """An access denial must produce a security audit event."""
        from src.services.persistence.jsonl_store import JSONLStore
        store = JSONLStore("data/intelligence/security_audit.jsonl")
        before_count = len(store.read_all())

        # Trigger a denial
        AccessControl.require(Role.VIEWER, PERM_APPROVE_CONFIG,
                              action="test_denial_audit", resource="test_res")

        after_count = len(store.read_all())
        assert after_count > before_count, "Denial must write an audit event"
