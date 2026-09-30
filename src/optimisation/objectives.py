"""
src/optimisation/objectives.py

Multi-objective function builder for the outreach optimization engine.

Supported strategies:
  COVERAGE_FOCUSED  – maximises risk-weighted population coverage
  BALANCED          – balances risk coverage with fairness and travel
  FAIRNESS_AWARE    – heavily weights underserved/vulnerable group coverage

Objective =
  α × Risk Coverage
  + β × Mobile Coverage
  + γ × Low-Service Coverage
  + δ × Fairness Bonus
  − ε × Travel Cost Proxy
  − ζ × Operational Penalty
"""
import pulp
import pandas as pd
from typing import Dict, Any
from src.utils.logger import get_logger

logger = get_logger("outreach_objectives")

# ── Canonical strategy weight profiles ────────────────────────────────────────
_STRATEGY_PROFILES: Dict[str, Dict[str, float]] = {
    "COVERAGE_FOCUSED": {
        "alpha":   0.50,   # risk coverage
        "beta":    0.10,   # mobile population coverage
        "gamma":   0.10,   # low-service coverage
        "delta":   0.05,   # fairness bonus
        "epsilon": 0.15,   # travel cost penalty
        "zeta":    0.10,   # operational penalty
    },
    "BALANCED": {
        "alpha":   0.30,
        "beta":    0.20,
        "gamma":   0.20,
        "delta":   0.15,
        "epsilon": 0.10,
        "zeta":    0.05,
    },
    "FAIRNESS_AWARE": {
        "alpha":   0.15,
        "beta":    0.25,
        "gamma":   0.30,
        "delta":   0.25,
        "epsilon": 0.03,
        "zeta":    0.02,
    },
}


def get_strategy_weights(strategy: str) -> Dict[str, float]:
    """Return the canonical weight profile for a given strategy name."""
    if strategy not in _STRATEGY_PROFILES:
        logger.warning("Unknown strategy '%s'. Defaulting to COVERAGE_FOCUSED.", strategy)
        return _STRATEGY_PROFILES["COVERAGE_FOCUSED"]
    return _STRATEGY_PROFILES[strategy]


def _safe(val, default: float = 0.0) -> float:
    """Return float or default when None / NaN."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return float(val)


def build_objective_function(
    model: pulp.LpProblem,
    selection_vars: dict,
    df: pd.DataFrame,
    strategy: str = "COVERAGE_FOCUSED",
    custom_weights: Dict[str, float] = None,
) -> pulp.LpProblem:
    """
    Builds the multi-objective function and adds it to the PuLP model.

    Parameters
    ----------
    model           PuLP maximisation problem.
    selection_vars  Binary decision variable dict keyed by df.index.
    df              Processed pipeline DataFrame.
    strategy        One of COVERAGE_FOCUSED | BALANCED | FAIRNESS_AWARE.
    custom_weights  Optional dict overriding any of {alpha, beta, gamma,
                    delta, epsilon, zeta}. Must all be in [0, 1].
    """
    weights = get_strategy_weights(strategy).copy()
    if custom_weights:
        for k, v in custom_weights.items():
            if k in weights:
                weights[k] = float(v)

    α = weights["alpha"]
    β = weights["beta"]
    γ = weights["gamma"]
    δ = weights["delta"]
    ε = weights["epsilon"]
    ζ = weights["zeta"]

    # ── Pre-compute per-row scores (avoid re-computation in loop) ─────────────
    n = len(df)
    max_dist = df["healthcare_distance_km"].max() if "healthcare_distance_km" in df.columns else 1.0
    if not max_dist or pd.isna(max_dist) or max_dist == 0:
        max_dist = 1.0

    objective_terms = []
    for idx, row in df.iterrows():
        risk_score    = _safe(row.get("multi_factor_risk_score"), 0.0)
        mobile_pop    = _safe(row.get("mobile_population"), 0.0)
        low_svc       = float(bool(row.get("group_low_service_access", False)))
        mob_flag      = float(bool(row.get("group_mobile", False)))
        vuln_idx      = _safe(row.get("vulnerability_index"), 0.0)
        travel_dist   = _safe(row.get("healthcare_distance_km"), 0.0)
        # Normalise travel distance to [0, 1]
        travel_norm   = travel_dist / max_dist

        # α – Risk Coverage (risk score drives priority)
        risk_term = α * risk_score

        # β – Mobile population coverage (fraction of mobile residents reached)
        # Normalise mobile_pop roughly: use 1 if any flag, scaled by vuln
        mobile_term = β * (0.5 + 0.5 * vuln_idx) * mob_flag

        # γ – Low-service-access coverage
        low_svc_term = γ * (0.5 + 0.5 * risk_score) * low_svc

        # δ – Fairness bonus for multiple vulnerability markers
        fairness_bonus = (mob_flag + low_svc + min(vuln_idx, 1.0)) / 3.0
        fairness_term  = δ * fairness_bonus

        # ε – Travel cost penalty (penalise distant sites unless high risk justifies)
        travel_penalty = ε * travel_norm * (1.0 - risk_score)

        # ζ – Operational penalty for fallback / low-confidence records
        is_fallback = str(row.get("fallback_status", "STANDARD")).upper() not in ("STANDARD", "APPROVED", "OK", "")
        op_penalty  = ζ * (1.0 if is_fallback else 0.0)

        score = risk_term + mobile_term + low_svc_term + fairness_term \
                - travel_penalty - op_penalty

        objective_terms.append(score * selection_vars[idx])

    model += pulp.lpSum(objective_terms), f"MultiObjective_{strategy}"
    return model
