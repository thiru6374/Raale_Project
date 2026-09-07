"""
src/explainability/risk_explainer.py

Explains WHY a neighbourhood has a particular risk classification.
Uses actual feature values from the pipeline DataFrame.
"""
from typing import Dict, Any
import pandas as pd
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("risk_explainer")

# Thresholds for interpreting factor severity
_TEMP_HIGH = 38.0    # °C – above this is HIGH temperature risk
_TEMP_EXTREME = 40.0  # °C – EXTREME temperature risk
_SERVICE_DEFICIT_HIGH = 0.6   # normalised score
_VULN_HIGH = 0.6
_BUILT_ENV_HIGH = 0.6


def explain_risk(row: pd.Series) -> Dict[str, Any]:
    """
    Given a single row from the final pipeline DataFrame, produce a
    plain-language explanation of its risk classification.

    Returns:
        {
          "risk_category": "HIGH",
          "risk_score": 0.72,
          "top_factors": [...],
          "narrative": "This neighbourhood is classified as HIGH RISK because...",
          "factor_contributions": { "temperature": 0.35, "built_environment": 0.12, ... },
          "data_gaps": [...]    # fields that were missing and reduced confidence
        }
    """
    risk_cat  = row.get("multi_factor_risk_category", "UNKNOWN")
    risk_score = float(row.get("multi_factor_risk_score", 0.0))

    # ── Factor contributions ──────────────────────────────────────────────────
    temperature_contrib = float(row.get("baseline_risk_score", 0.0)) * settings.temperature_weight
    built_env_contrib   = float(row.get("built_environment_score", 0.0)) * settings.built_environment_weight
    service_contrib     = float(row.get("service_deficit_score", 0.0)) * settings.service_access_weight
    vuln_contrib        = float(row.get("vulnerability_index", 0.0)) * settings.vulnerability_weight

    factor_contributions = {
        "temperature_exposure": round(temperature_contrib, 3),
        "built_environment":    round(built_env_contrib, 3),
        "service_deficit":      round(service_contrib, 3),
        "vulnerability":        round(vuln_contrib, 3),
    }

    # ── Plain-language top factors ────────────────────────────────────────────
    sorted_factors = sorted(factor_contributions.items(), key=lambda x: x[1], reverse=True)
    top_factors = []

    temp_c   = row.get("temperature_c") or row.get("latest_temperature_c")
    svc_dist = row.get("healthcare_distance_km")
    vuln_idx = row.get("vulnerability_index")
    built    = row.get("built_density")

    if temp_c is not None:
        label = "ELEVATED" if temp_c >= _TEMP_HIGH else "MODERATE"
        if temp_c >= _TEMP_EXTREME:
            label = "EXTREME"
        top_factors.append(
            f"Temperature exposure is {label} ({temp_c:.1f} °C)"
        )
    if svc_dist is not None and float(svc_dist) >= 5.0:
        top_factors.append(
            f"Nearest healthcare facility is {svc_dist:.1f} km away (limited access)"
        )
    if vuln_idx is not None and float(vuln_idx) >= _VULN_HIGH:
        top_factors.append(
            f"Aggregate vulnerability index is HIGH ({vuln_idx:.2f})"
        )
    if built is not None and float(built) >= _BUILT_ENV_HIGH:
        top_factors.append(
            f"High built density ({built:.2f}) increases heat retention"
        )

    # Fall back to just naming the biggest contributors by weight
    if not top_factors:
        for f, v in sorted_factors[:2]:
            top_factors.append(f"{f.replace('_', ' ').title()} contributed {v:.2f} to the risk score")

    # ── Data gaps ─────────────────────────────────────────────────────────────
    data_gaps = []
    critical_fields = {
        "temperature_c": "Temperature reading",
        "healthcare_distance_km": "Healthcare distance",
        "vulnerability_index": "Vulnerability index",
        "built_density": "Built density",
    }
    for col, label in critical_fields.items():
        val = row.get(col)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            data_gaps.append(f"{label} was not available for this record")

    # ── Narrative ─────────────────────────────────────────────────────────────
    if top_factors:
        factor_text = "; ".join(top_factors[:3])
        narrative = (
            f"This neighbourhood is classified as {risk_cat} RISK "
            f"(score: {risk_score:.2f}) primarily because: {factor_text}."
        )
    else:
        narrative = (
            f"This neighbourhood is classified as {risk_cat} RISK "
            f"with a composite score of {risk_score:.2f}."
        )

    if data_gaps:
        narrative += f" Note: {len(data_gaps)} data field(s) were missing, which may have reduced accuracy."

    return {
        "risk_category":       risk_cat,
        "risk_score":          risk_score,
        "top_factors":         top_factors,
        "narrative":           narrative,
        "factor_contributions": factor_contributions,
        "data_gaps":           data_gaps,
    }
