"""
tests/test_overrides.py

Phase 8: Tests for the authorized human-override workflow.
Verifies: authorized override, unauthorized override, missing reason,
          audit persistence, and original decision preservation.
"""
import pandas as pd
import pytest
from src.governance.overrides import OverrideManager
from src.governance.audit_logger import AuditLogger
from src.security.roles import Role


@pytest.fixture
def override_manager(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(str(audit_path))
    return OverrideManager(logger)


def _sample_df():
    return pd.DataFrame({
        "neighbourhood_id": ["N1", "N2"],
        "selected_for_outreach": [False, True],
        "confidence_score": [0.9, 0.8]
    })


# ── 1. Authorized Override ────────────────────────────────────────────────────
def test_authorized_override(override_manager):
    """ADMIN role can override; original decision is preserved; audit is written."""
    result = override_manager.apply_override(
        df=_sample_df(),
        neighbourhood_id="N1",
        force_select=True,
        actor="admin_user",
        role=Role.ADMIN,
        reason="High-risk cluster identified by field team",
        comment="Confirmed by district manager",
    )

    # Final decision changed
    assert result.loc[0, "selected_for_outreach"] == True
    # Original decision preserved — never overwritten
    assert result.loc[0, "original_selected_for_outreach"] == False
    assert result.loc[0, "override_status"] == "MANUAL_OVERRIDE"
    assert result.loc[0, "outreach_priority"] == "HUMAN_MANDATED"

    # Audit persisted
    logs = override_manager.audit.read_logs()
    assert len(logs) == 1
    assert logs[0]["neighbourhood_id"] == "N1"
    assert logs[0]["actor"] == "admin_user"
    assert logs[0]["auth_status"] == "AUTHORIZED"
    assert logs[0]["original_decision"] is False
    assert logs[0]["new_decision"] is True


# ── 2. Unauthorized Override ──────────────────────────────────────────────────
def test_unauthorized_override(override_manager):
    """OPERATOR role lacks override_decision permission; raises PermissionError; denial logged."""
    with pytest.raises(PermissionError, match="Unauthorized"):
        override_manager.apply_override(
            df=_sample_df(),
            neighbourhood_id="N1",
            force_select=True,
            actor="operator_user",
            role=Role.OPERATOR,
            reason="Attempting unauthorized override",
            comment="",
        )

    # Denial still audited
    logs = override_manager.audit.read_logs()
    assert len(logs) == 1
    assert logs[0]["auth_status"] == "DENIED"
    assert logs[0]["actor"] == "operator_user"


# ── 3. Missing Reason ─────────────────────────────────────────────────────────
def test_missing_reason_override_raises(override_manager):
    """Override without a valid reason raises ValueError before any auth check."""
    with pytest.raises(ValueError, match="reason"):
        override_manager.apply_override(
            df=_sample_df(),
            neighbourhood_id="N1",
            force_select=True,
            actor="admin_user",
            role=Role.ADMIN,
            reason="   ",  # whitespace-only — invalid
            comment="",
        )


# ── 4. Audit Persistence ──────────────────────────────────────────────────────
def test_audit_persists_across_overrides(override_manager):
    """Multiple overrides accumulate distinct audit entries."""
    df = _sample_df()

    override_manager.apply_override(
        df=df,
        neighbourhood_id="N1",
        force_select=True,
        actor="admin_user",
        role=Role.ADMIN,
        reason="First override reason",
        comment="",
    )
    override_manager.apply_override(
        df=df,
        neighbourhood_id="N2",
        force_select=False,
        actor="admin_user",
        role=Role.ADMIN,
        reason="Second override reason",
        comment="deprioritised",
    )

    logs = override_manager.audit.read_logs()
    assert len(logs) == 2
    assert logs[0]["neighbourhood_id"] == "N1"
    assert logs[1]["neighbourhood_id"] == "N2"
    # Each event gets a unique ID
    assert logs[0]["event_id"] != logs[1]["event_id"]


# ── 5. Original Decision Preservation ────────────────────────────────────────
def test_original_decision_column_not_mutated_on_second_override(override_manager):
    """original_selected_for_outreach must reflect the very first automated decision."""
    df = _sample_df()

    # First override: N1 False → True
    df_v1 = override_manager.apply_override(
        df=df,
        neighbourhood_id="N1",
        force_select=True,
        actor="admin_user",
        role=Role.ADMIN,
        reason="First override",
        comment="",
    )
    assert df_v1.loc[0, "original_selected_for_outreach"] == False

    # Second override on the already-overridden df: True → False
    df_v2 = override_manager.apply_override(
        df=df_v1,
        neighbourhood_id="N1",
        force_select=False,
        actor="admin_user",
        role=Role.ADMIN,
        reason="Reverting override",
        comment="",
    )
    # Final decision changed again
    assert df_v2.loc[0, "selected_for_outreach"] == False
    # Original automated decision still preserved from the very first run
    assert df_v2.loc[0, "original_selected_for_outreach"] == False
