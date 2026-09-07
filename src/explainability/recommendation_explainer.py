"""
src/explainability/recommendation_explainer.py

Explains WHY a neighbourhood was selected (or not) for outreach,
using the actual pipeline row data.
"""
from typing import Dict, Any, List
import pandas as pd
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("recommendation_explainer")


def explain_recommendation(row: pd.Series, fairness_warnings: List[Dict] = None) -> Dict[str, Any]:
    """
    Produces a human-readable explanation for why a neighbourhood was
    selected (or not) for outreach, and which constraints affected the decision.

    Parameters:
        row: a single row from the final pipeline DataFrame
        fairness_warnings: list of fairness warning dicts from FairnessAuditor

    Returns a structured explanation dictionary.
    """
    fairness_warnings = fairness_warnings or []
    is_selected   = bool(row.get("selected_for_outreach", False))
    priority      = row.get("outreach_priority", "UNKNOWN")
    trust_status  = row.get("fallback_status", "UNKNOWN")
    risk_cat      = row.get("multi_factor_risk_category", "UNKNOWN")
    risk_score    = float(row.get("multi_factor_risk_score", 0.0))
    conf_score    = float(row.get("confidence_score", 1.0))
    n_id          = row.get("neighbourhood_id", "UNKNOWN")

    max_capacity  = settings.number_of_teams * settings.maximum_visits_per_team

    # ── Why selected / not selected ──────────────────────────────────────────
    selection_reasons: List[str] = []
    not_selected_reasons: List[str] = []

    if is_selected:
        if risk_cat in ("EXTREME", "HIGH"):
            selection_reasons.append(f"Risk classification is {risk_cat} (score: {risk_score:.2f})")
        svc_dist = row.get("healthcare_distance_km")
        if svc_dist is not None and float(svc_dist) >= 5.0:
            selection_reasons.append(f"Limited healthcare access ({svc_dist:.1f} km to nearest facility)")
        vuln = row.get("vulnerability_index")
        if vuln is not None and float(vuln) >= 0.5:
            selection_reasons.append(f"High aggregate vulnerability index ({vuln:.2f})")
        mobile = row.get("group_mobile")
        if mobile:
            selection_reasons.append("Contains mobile worker population — additional outreach priority")
        low_svc = row.get("group_low_service_access")
        if low_svc:
            selection_reasons.append("Part of low-service-access population group — fairness-aware selection")
        if not selection_reasons:
            selection_reasons.append(f"Ranked in top selections by the multi-objective optimizer (score: {risk_score:.2f})")
    else:
        if risk_cat not in ("EXTREME", "HIGH"):
            not_selected_reasons.append(f"Risk level is {risk_cat} — below the high-risk threshold for outreach")
        if trust_status in ("UNTRUSTED", "MANUAL_REVIEW"):
            not_selected_reasons.append(
                f"Recommendation trust status is {trust_status} — safe fallback applies; "
                "manual review recommended before outreach"
            )
        if priority == "WAITLIST_HIGH_RISK":
            not_selected_reasons.append(
                f"Operational capacity limited to {max_capacity} outreach slots; "
                "this neighbourhood was waitlisted despite being high risk"
            )
        if not not_selected_reasons:
            not_selected_reasons.append("Not prioritised by the multi-objective optimizer given current capacity")

    # ── Constraint context ────────────────────────────────────────────────────
    constraints: List[str] = [
        f"Outreach capacity is capped at {max_capacity} neighbourhoods "
        f"({settings.number_of_teams} teams × {settings.maximum_visits_per_team} visits each)",
        f"Fairness constraint: maximum allowed coverage gap between groups is "
        f"{settings.maximum_coverage_gap * 100:.0f}%",
    ]

    # ── Fairness context ──────────────────────────────────────────────────────
    fairness_context = "No fairness warnings affecting this neighbourhood."
    if fairness_warnings:
        affected = [w for w in fairness_warnings if n_id in str(w)]
        if affected:
            fairness_context = (
                f"{len(affected)} fairness warning(s) were raised that may involve this neighbourhood."
            )
        else:
            fairness_context = (
                f"{len(fairness_warnings)} system-wide fairness warning(s) exist "
                "(check Fairness Analysis page for details)."
            )

    # ── Trust & fallback ──────────────────────────────────────────────────────
    trust_label = "TRUSTED"
    if trust_status == "MANUAL_REVIEW":
        trust_label = "CAUTION — manual review required"
    elif trust_status == "UNTRUSTED":
        trust_label = "UNTRUSTED — do not rely on this recommendation without review"

    trust_explanation = (
        f"Data completeness score: {conf_score:.0%}. "
        f"Recommendation trust: {trust_label}."
    )

    # ── Timing ───────────────────────────────────────────────────────────────
    timing = row.get("recommended_timing") or "Within current operational cycle"

    # ── Narrative ─────────────────────────────────────────────────────────────
    if is_selected:
        narrative = (
            f"Neighbourhood {n_id} was SELECTED for outreach. "
            + " ".join(selection_reasons[:2]) + "."
        )
    elif priority == "WAITLIST_HIGH_RISK":
        narrative = (
            f"Neighbourhood {n_id} is HIGH RISK but could NOT be reached due to "
            f"capacity constraints (limit: {max_capacity}). It is on the waitlist."
        )
    else:
        narrative = (
            f"Neighbourhood {n_id} was NOT selected. "
            + " ".join(not_selected_reasons[:2]) + "."
        )

    return {
        "neighbourhood_id":        n_id,
        "is_selected":             is_selected,
        "priority":                priority,
        "selection_reasons":       selection_reasons,
        "not_selected_reasons":    not_selected_reasons,
        "constraints":             constraints,
        "fairness_context":        fairness_context,
        "trust_explanation":       trust_explanation,
        "timing":                  timing,
        "narrative":               narrative,
    }
