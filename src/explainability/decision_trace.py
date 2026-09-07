"""
src/explainability/decision_trace.py

Creates a structured, auditable Decision Trace for every final recommendation.
Connects: Input → Validation → Features → Risk → Baseline → Optimization
          → Fairness → Constraints → Trust → Fallback → Override → Final Action.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("decision_trace")


def create_decision_trace(
    row: pd.Series,
    dataset_id: str = "UNKNOWN",
    strategy: str = "COVERAGE_FOCUSED",
    fairness_warnings: Optional[List[Dict]] = None,
    audit_logs: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Builds a full decision trace for one neighbourhood row.

    Parameters:
        row             : single pipeline DataFrame row
        dataset_id      : identifier of the source dataset used
        strategy        : optimization strategy used
        fairness_warnings: list from FairnessAuditor
        audit_logs      : list from AuditLogger.read_logs()

    Returns:
        Structured dict with a unique Decision ID and full traceability.
    """
    fairness_warnings = fairness_warnings or []
    audit_logs        = audit_logs or []

    n_id     = row.get("neighbourhood_id", "UNKNOWN")
    risk_cat = row.get("multi_factor_risk_category", "UNKNOWN")
    risk_scr = float(row.get("multi_factor_risk_score", 0.0))
    conf_scr = float(row.get("confidence_score", 1.0))
    fallback = row.get("fallback_status", "UNKNOWN")
    selected = bool(row.get("selected_for_outreach", False))
    priority = row.get("outreach_priority", "UNKNOWN")
    action   = row.get("recommended_action", "N/A")

    # ── Risk factors ──────────────────────────────────────────────────────────
    major_risk_factors = []
    for col, label in [
        ("baseline_risk_score",     "Temperature Exposure"),
        ("built_environment_score", "Built Environment"),
        ("service_deficit_score",   "Service Deficit"),
        ("vulnerability_index",     "Vulnerability"),
    ]:
        val = row.get(col)
        if val is not None:
            major_risk_factors.append({"factor": label, "value": round(float(val), 3)})

    # ── Baseline vs optimized ─────────────────────────────────────────────────
    baseline_selected = row.get("baseline_selected", None)
    if baseline_selected is None:
        baseline_decision = "NOT_IN_BASELINE_DF (see baseline_results object)"
    else:
        baseline_decision = "SELECTED" if baseline_selected else "NOT_SELECTED"

    # ── Override history ──────────────────────────────────────────────────────
    override_records = [
        lg for lg in audit_logs
        if lg.get("neighbourhood_id") == n_id
    ]
    override_status = "NO_OVERRIDE"
    if override_records:
        latest = override_records[-1]
        override_status = (
            f"OVERRIDE APPLIED by {latest.get('user_id')} at {latest.get('timestamp')} "
            f"— Reason: {latest.get('reason')}"
        )

    # ── Fairness check ───────────────────────────────────────────────────────
    fairness_impact = (
        "No fairness warnings recorded."
        if not fairness_warnings
        else f"{len(fairness_warnings)} fairness warning(s) raised at system level."
    )

    trace = {
        "decision_id":          str(uuid.uuid4()),
        "timestamp":            datetime.utcnow().isoformat() + "Z",
        "neighbourhood_id":     n_id,
        "neighbourhood_name":   row.get("neighbourhood_name", ""),
        "district":             row.get("district", ""),
        "dataset_id":           dataset_id,
        # ── Risk layer ────────────────────────────────────────────────────────
        "risk_score":           round(risk_scr, 4),
        "risk_classification":  risk_cat,
        "major_risk_factors":   major_risk_factors,
        # ── Baseline layer ────────────────────────────────────────────────────
        "baseline_decision":    baseline_decision,
        # ── Optimization layer ────────────────────────────────────────────────
        "optimization_strategy": strategy,
        "coverage_weight":      settings.temperature_weight,   # proxy: temperature is core
        "fairness_weight":      settings.maximum_coverage_gap,
        # ── Constraint layer ──────────────────────────────────────────────────
        "capacity_limit":       settings.number_of_teams * settings.maximum_visits_per_team,
        "fairness_constraint":  f"Max group coverage gap: {settings.maximum_coverage_gap * 100:.0f}%",
        # ── Fairness layer ────────────────────────────────────────────────────
        "fairness_impact":      fairness_impact,
        # ── Trust / fallback layer ────────────────────────────────────────────
        "confidence_score":     round(conf_scr, 3),
        "trust_status":         fallback,
        # ── Override layer ────────────────────────────────────────────────────
        "override_status":      override_status,
        # ── Final layer ───────────────────────────────────────────────────────
        "final_selected":       selected,
        "outreach_priority":    priority,
        "recommended_action":   action,
    }

    logger.debug("Decision trace created for %s — ID: %s", n_id, trace["decision_id"])
    return trace


def create_batch_traces(
    df: pd.DataFrame,
    dataset_id: str = "UNKNOWN",
    strategy: str = "COVERAGE_FOCUSED",
    fairness_warnings: Optional[List[Dict]] = None,
    audit_logs: Optional[List[Dict]] = None,
) -> List[Dict[str, Any]]:
    """Creates decision traces for every row in the pipeline DataFrame."""
    traces = []
    for _, row in df.iterrows():
        try:
            traces.append(
                create_decision_trace(
                    row, dataset_id=dataset_id, strategy=strategy,
                    fairness_warnings=fairness_warnings, audit_logs=audit_logs
                )
            )
        except Exception as exc:
            logger.warning("Could not create trace for row: %s", exc)
    return traces
