"""
src/explainability/risk_explainer.py

Explains WHY a neighbourhood has a particular risk classification.
Uses the rich risk_explainability JSON field produced by the formal
MultiFactorRiskModel v2.0.0, with a legacy fallback for older data.
"""
import json
from typing import Dict, Any
import pandas as pd
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("risk_explainer")

# Thresholds for interpreting factor severity (for legacy & narrative)
_TEMP_HIGH = 38.0
_TEMP_EXTREME = 40.0
_SERVICE_DEFICIT_HIGH = 0.6
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
          "model_version": "2.0.0",
          "top_factors": [...],
          "narrative": "This neighbourhood is classified as HIGH RISK because...",
          "factor_contributions": { "temperature": 0.30, ... },
          "factor_table": [{"factor": ..., "raw": ..., "normalized": ..., "weight": ..., "contribution": ...}, ...],
          "data_gaps": [...]
        }
    """
    risk_cat  = row.get("multi_factor_risk_category", "UNKNOWN")
    risk_score = float(row.get("multi_factor_risk_score", 0.0))

    # ── Try to load rich formal model explainability ──────────────────────────
    factor_table = []
    factor_contributions = {}
    model_version = "legacy"

    expl_raw = row.get("risk_explainability")
    if expl_raw and isinstance(expl_raw, str):
        try:
            expl = json.loads(expl_raw)
            model_version = expl.get("model_version", "2.0.0")
            factors = expl.get("factors", {})

            for fname, fdata in factors.items():
                contrib = fdata.get("contribution", 0.0)
                factor_contributions[fname] = round(contrib, 4)
                factor_table.append({
                    "Factor": fname.replace("_", " ").title(),
                    "Raw Value": round(fdata.get("raw", fdata.get("normalized", 0.0)), 4),
                    "Normalized (0–1)": round(fdata.get("normalized", 0.0), 4),
                    "Weight": fdata.get("weight", 0.0),
                    "Contribution": round(contrib, 4),
                })
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Could not parse risk_explainability JSON: %s", e)

    # ── Legacy fallback factor contributions if formal model data unavailable ─
    if not factor_contributions:
        temperature_contrib = float(row.get("baseline_risk_score", 0.0)) * settings.temperature_weight
        built_env_contrib   = float(row.get("built_environment_score", 0.0)) * settings.built_environment_weight
        service_contrib     = float(row.get("service_deficit_score", 0.0)) * settings.service_access_weight
        vuln_contrib        = float(row.get("vulnerability_index", 0.0)) * settings.vulnerability_weight
        mobility_contrib    = float(row.get("mobile_population", 0.0)) * getattr(settings, "mobility_weight", 0.15)

        factor_contributions = {
            "temperature_exposure": round(temperature_contrib, 4),
            "built_environment":    round(built_env_contrib, 4),
            "service_deficit":      round(service_contrib, 4),
            "vulnerability":        round(vuln_contrib, 4),
            "mobility":             round(mobility_contrib, 4),
        }

    # ── Plain-language top factors ────────────────────────────────────────────
    sorted_factors = sorted(factor_contributions.items(), key=lambda x: x[1], reverse=True)
    top_factors = []

    temp_c   = row.get("temperature_c") or row.get("latest_temperature_c") or row.get("heat_index")
    svc_dist = row.get("healthcare_distance_km")
    vuln_idx = row.get("vulnerability_index")
    built    = row.get("built_density")
    green    = row.get("green_cover_percent")
    elderly  = row.get("elderly_population_percent")

    if temp_c is not None:
        label = "ELEVATED" if float(temp_c) >= _TEMP_HIGH else "MODERATE"
        if float(temp_c) >= _TEMP_EXTREME:
            label = "EXTREME"
        top_factors.append(f"Temperature exposure is {label} ({float(temp_c):.1f} °C / Heat Index)")
    if svc_dist is not None and float(svc_dist) >= 5.0:
        top_factors.append(f"Nearest healthcare facility is {float(svc_dist):.1f} km away (limited access)")
    if vuln_idx is not None and float(vuln_idx) >= _VULN_HIGH:
        top_factors.append(f"Aggregate vulnerability index is HIGH ({float(vuln_idx):.2f})")
    if built is not None and float(built) >= _BUILT_ENV_HIGH:
        top_factors.append(f"High built density ({float(built):.2f}) increases urban heat retention")
    if green is not None and float(green) < 0.2:
        top_factors.append(f"Low green cover ({float(green)*100:.0f}%) reduces cooling effect")
    if elderly is not None and float(elderly) >= 0.2:
        top_factors.append(f"High elderly population share ({float(elderly)*100:.0f}%) increases heat vulnerability")

    if not top_factors:
        for f, v in sorted_factors[:2]:
            top_factors.append(f"{f.replace('_', ' ').title()} contributed {v:.3f} to the risk score")

    # ── Data gaps ─────────────────────────────────────────────────────────────
    data_gaps = []
    critical_fields = {
        "temperature_c": "Temperature reading",
        "heat_index": "Heat index",
        "healthcare_distance_km": "Healthcare distance",
        "vulnerability_index": "Vulnerability index",
        "built_density": "Built density",
        "mobile_population": "Mobile population share",
    }
    for col, label in critical_fields.items():
        val = row.get(col)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            data_gaps.append(f"{label} was not available for this record")

    # ── Narrative ─────────────────────────────────────────────────────────────
    cat_display = risk_cat.replace("_", " ")
    if top_factors:
        factor_text = "; ".join(top_factors[:3])
        narrative = (
            f"This neighbourhood is classified as **{cat_display}** risk "
            f"(composite score: {risk_score:.3f}, model v{model_version}) primarily because: {factor_text}."
        )
    else:
        narrative = (
            f"This neighbourhood is classified as **{cat_display}** risk "
            f"with a composite score of {risk_score:.3f} (model v{model_version})."
        )

    if data_gaps:
        narrative += f" ⚠ Note: {len(data_gaps)} data field(s) were missing, which may have affected accuracy."

    return {
        "risk_category":        risk_cat,
        "risk_score":           risk_score,
        "model_version":        model_version,
        "top_factors":          top_factors,
        "narrative":            narrative,
        "factor_contributions": factor_contributions,
        "factor_table":         factor_table,
        "data_gaps":            data_gaps,
    }
