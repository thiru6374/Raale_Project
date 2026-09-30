"""
src/explainability/sensitivity_engine.py

Phase 10: Full sensitivity analysis engine.

Varies each of the 7 configurable parameters and measures the impact on
key operational metrics — not just category counts.

Parameters varied:
  - temperature_weight
  - vulnerability_weight
  - service_access_weight
  - environmental_weight  (built_environment_weight)
  - mobility_weight
  - travel_penalty        (synthetic: biases selection toward nearby areas)
  - fairness_weight       (synthetic: biases selection toward protected groups)

For each perturbation the engine reports:
  Parameter | Original | Changed | high_risk_coverage_pct | total_selected |
  category_changes | fairness_gap_pct | metric_impact (summary)
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from src.config.settings import settings

logger = logging.getLogger("sensitivity_engine")

_VARIANCES = [-0.10, +0.10]

def _renormalise(weights: Dict[str, float], changed_key: str, delta: float) -> Dict[str, float]:
    """
    Increase `changed_key` by `delta`, then proportionally rescale all other
    weights so the total still sums to 1.0.
    """
    new_w = weights.copy()
    new_w[changed_key] = max(0.01, min(0.99, new_w[changed_key] + delta))
    remainder = 1.0 - new_w[changed_key]
    others_sum = sum(v for k, v in weights.items() if k != changed_key)
    if others_sum > 0:
        for k in new_w:
            if k != changed_key:
                new_w[k] = weights[k] / others_sum * remainder
    return new_w


def _apply_travel_penalty(df: pd.DataFrame, factor: float) -> pd.DataFrame:
    """
    Synthetic travel-penalty variation: re-sort selection to prefer
    closer neighbourhoods when factor > 1 (higher penalty).
    Returns a modified df with updated selected_for_outreach.
    """
    out = df.copy()
    if "selected_for_outreach" not in out.columns or "healthcare_distance_km" not in out.columns:
        return out
    n_selected = int(out["selected_for_outreach"].sum())
    if n_selected == 0:
        return out
    # Score = risk_score - factor * normalised_distance
    risk  = out.get("multi_factor_risk_score", pd.Series(0.5, index=out.index))
    dist  = out.get("healthcare_distance_km", pd.Series(5.0, index=out.index)).fillna(5.0)
    dist_norm = (dist - dist.min()) / (dist.max() - dist.min() + 1e-9)
    score = risk - factor * dist_norm
    top_idx = score.nlargest(n_selected).index
    out["selected_for_outreach"] = False
    out.loc[top_idx, "selected_for_outreach"] = True
    return out


def _apply_fairness_weight(df: pd.DataFrame, weight: float) -> pd.DataFrame:
    """
    Synthetic fairness-weight variation: boost selection probability
    for protected groups. weight=0 → pure risk-based; weight=1 → pure fairness.
    """
    out = df.copy()
    if "selected_for_outreach" not in out.columns:
        return out
    n_selected = int(out["selected_for_outreach"].sum())
    if n_selected == 0:
        return out
    risk   = out.get("multi_factor_risk_score", pd.Series(0.5, index=out.index))
    mobile = out.get("group_mobile", pd.Series(False, index=out.index)).astype(float)
    low_sv = out.get("group_low_service_access", pd.Series(False, index=out.index)).astype(float)
    fair   = (mobile + low_sv).clip(0, 1)
    score  = (1 - weight) * risk + weight * fair
    top_idx = score.nlargest(n_selected).index
    out["selected_for_outreach"] = False
    out.loc[top_idx, "selected_for_outreach"] = True
    return out


def _compute_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """Derive the key metrics we care about from a pipeline result df."""
    is_hr  = df.get("multi_factor_risk_category", pd.Series(dtype=str)).isin({"VERY HIGH","HIGH","EXTREME"})
    is_sel = df.get("selected_for_outreach", pd.Series(False, index=df.index)).astype(bool)
    n_hr   = int(is_hr.sum())
    hr_reached = int((is_hr & is_sel).sum())
    n_sel  = int(is_sel.sum())

    # Fairness gap
    gap = 0.0
    rates = []
    for grp in ["group_mobile", "group_low_service_access"]:
        if grp in df.columns:
            g_mask = df[grp].astype(bool)
            g_tot  = int(g_mask.sum())
            g_sel  = int((g_mask & is_sel).sum())
            rates.append(g_sel / g_tot * 100 if g_tot > 0 else 0.0)
    if len(rates) == 2:
        gap = abs(rates[0] - rates[1])

    return {
        "total_selected":         n_sel,
        "high_risk_coverage_pct": round(hr_reached / n_hr * 100, 2) if n_hr > 0 else 0.0,
        "fairness_gap_pct":       round(gap, 2),
    }


def run_sensitivity_analysis(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Full 7-parameter sensitivity analysis.
    Returns a list of row dicts suitable for a DataFrame / table display.

    Each row: {
      parameter, original_value, changed_value, delta,
      high_risk_coverage_pct_orig, high_risk_coverage_pct_new,
      fairness_gap_pct_orig, fairness_gap_pct_new,
      category_changes, metric_impact
    }
    """
    if df is None or df.empty:
        return []

    from src.risk.risk_engine import MultiFactorRiskModel
    from src.optimisation.planner import OutreachPlanner

    base_weights = {
        "temperature":   settings.temperature_weight,
        "environmental": settings.built_environment_weight,
        "vulnerability": settings.vulnerability_weight,
        "service_access": settings.service_access_weight,
        "mobility":      settings.mobility_weight,
    }

    # Baseline metrics from the actual df
    base_metrics = _compute_metrics(df)
    base_cats    = df.get("multi_factor_risk_category", pd.Series(dtype=str))

    rows = []

    # ── Risk weight parameters ─────────────────────────────────────────────────
    param_labels = {
        "temperature":    "Temperature Weight (α)",
        "environmental":  "Environmental Weight (β)",
        "vulnerability":  "Vulnerability Weight (γ)",
        "service_access": "Service-Access Weight (δ)",
        "mobility":       "Mobility Weight (ε)",
    }

    for key, label in param_labels.items():
        orig_val = base_weights[key]
        for delta in _VARIANCES:
            new_w = _renormalise(base_weights, key, delta)
            try:
                model    = MultiFactorRiskModel(weights_dict=new_w)
                risk_df  = model.calculate_risk(df.copy())

                # Re-run selection with planner on the re-scored df
                planner  = OutreachPlanner()
                planned  = planner.plan_outreach(risk_df, strategy="COVERAGE_FOCUSED",
                                                 dataset_signature="sensitivity")
                new_m    = _compute_metrics(planned)
                new_cats = risk_df.get("multi_factor_risk_category", pd.Series(dtype=str))
                cat_chg  = int((base_cats != new_cats).sum())
            except Exception as e:
                logger.warning("Sensitivity run failed for %s delta=%+.2f: %s", key, delta, e)
                continue

            cov_chg  = new_m["high_risk_coverage_pct"] - base_metrics["high_risk_coverage_pct"]
            fair_chg = new_m["fairness_gap_pct"]       - base_metrics["fairness_gap_pct"]
            impact   = (
                f"Coverage {cov_chg:+.1f}pp, "
                f"Fairness Gap {fair_chg:+.1f}pp, "
                f"{cat_chg} cat. changes"
            )
            rows.append({
                "Parameter":             label,
                "Original":              round(orig_val, 3),
                "Changed":               round(new_w[key], 3),
                "Δ Weight":              f"{delta:+.2f}",
                "Coverage Orig (%)":     base_metrics["high_risk_coverage_pct"],
                "Coverage New (%)":      new_m["high_risk_coverage_pct"],
                "Coverage Δ (pp)":       round(cov_chg, 2),
                "Fairness Gap Orig (%)": base_metrics["fairness_gap_pct"],
                "Fairness Gap New (%)":  new_m["fairness_gap_pct"],
                "Fairness Gap Δ (pp)":   round(fair_chg, 2),
                "Category Changes":      cat_chg,
                "Metric Impact":         impact,
            })

    # ── Travel Penalty (synthetic) ─────────────────────────────────────────────
    for travel_factor, label_suffix in [(0.2, "Low"), (0.5, "Medium"), (1.0, "High")]:
        mod_df  = _apply_travel_penalty(df, travel_factor)
        new_m   = _compute_metrics(mod_df)
        cov_chg = new_m["high_risk_coverage_pct"] - base_metrics["high_risk_coverage_pct"]
        fair_chg= new_m["fairness_gap_pct"]       - base_metrics["fairness_gap_pct"]
        rows.append({
            "Parameter":             f"Travel Penalty ({label_suffix})",
            "Original":              0.0,
            "Changed":               travel_factor,
            "Δ Weight":              f"+{travel_factor:.1f}",
            "Coverage Orig (%)":     base_metrics["high_risk_coverage_pct"],
            "Coverage New (%)":      new_m["high_risk_coverage_pct"],
            "Coverage Δ (pp)":       round(cov_chg, 2),
            "Fairness Gap Orig (%)": base_metrics["fairness_gap_pct"],
            "Fairness Gap New (%)":  new_m["fairness_gap_pct"],
            "Fairness Gap Δ (pp)":   round(fair_chg, 2),
            "Category Changes":      0,
            "Metric Impact":         f"Coverage {cov_chg:+.1f}pp, Fairness Gap {fair_chg:+.1f}pp",
        })

    # ── Fairness Weight (synthetic) ────────────────────────────────────────────
    for fw, label_suffix in [(0.2, "Low"), (0.5, "Medium"), (0.8, "High")]:
        mod_df  = _apply_fairness_weight(df, fw)
        new_m   = _compute_metrics(mod_df)
        cov_chg = new_m["high_risk_coverage_pct"] - base_metrics["high_risk_coverage_pct"]
        fair_chg= new_m["fairness_gap_pct"]       - base_metrics["fairness_gap_pct"]
        rows.append({
            "Parameter":             f"Fairness Weight ({label_suffix})",
            "Original":              0.0,
            "Changed":               fw,
            "Δ Weight":              f"+{fw:.1f}",
            "Coverage Orig (%)":     base_metrics["high_risk_coverage_pct"],
            "Coverage New (%)":      new_m["high_risk_coverage_pct"],
            "Coverage Δ (pp)":       round(cov_chg, 2),
            "Fairness Gap Orig (%)": base_metrics["fairness_gap_pct"],
            "Fairness Gap New (%)":  new_m["fairness_gap_pct"],
            "Fairness Gap Δ (pp)":   round(fair_chg, 2),
            "Category Changes":      0,
            "Metric Impact":         f"Coverage {cov_chg:+.1f}pp, Fairness Gap {fair_chg:+.1f}pp",
        })

    return rows
