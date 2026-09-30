"""
tests/test_sensitivity_engine.py

Phase 10: Tests for the sensitivity analysis engine and explainability modules.
"""
import json
import numpy as np
import pandas as pd
import pytest

from src.explainability.sensitivity_engine import (
    run_sensitivity_analysis, _renormalise, _apply_travel_penalty,
    _apply_fairness_weight, _compute_metrics,
)
from src.explainability.risk_explainer import explain_risk


# ── Helper: minimal pipeline-like dataframe ────────────────────────────────────
def _make_pipeline_df(n=20, seed=42):
    rng = np.random.default_rng(seed)
    risk = rng.uniform(0.1, 0.9, n)
    cats = pd.cut(risk, bins=[0, 0.25, 0.5, 0.75, 1.0],
                  labels=["LOW", "MODERATE", "HIGH", "VERY HIGH"])
    selected = risk > 0.55
    return pd.DataFrame({
        "neighbourhood_id":           [f"N{i:03d}" for i in range(n)],
        "neighbourhood_name":         [f"Area {i}" for i in range(n)],
        "multi_factor_risk_score":    risk,
        "multi_factor_risk_category": cats.astype(str),
        "selected_for_outreach":      selected,
        "healthcare_distance_km":     rng.uniform(1, 15, n),
        "group_mobile":               rng.choice([True, False], n),
        "group_low_service_access":   rng.choice([True, False], n),
        "population":                 rng.integers(500, 5000, n),
        "mobile_population":          rng.integers(50, 500, n),
        "temperature_c":              rng.uniform(30, 42, n),
        "heat_index":                 rng.uniform(35, 48, n),
        "vulnerability_index":        rng.uniform(0.2, 0.9, n),
        "built_density":              rng.uniform(0.3, 0.8, n),
        "green_cover_percent":        rng.uniform(0.05, 0.4, n),
        "elderly_population_percent": rng.uniform(0.05, 0.3, n),
    })


# ── Weight renormalisation ─────────────────────────────────────────────────────

def test_renormalise_sums_to_one():
    w = {"temperature": 0.30, "environmental": 0.20,
         "vulnerability": 0.20, "service_access": 0.15, "mobility": 0.15}
    new_w = _renormalise(w, "temperature", +0.10)
    assert abs(sum(new_w.values()) - 1.0) < 1e-6


def test_renormalise_clamps_to_bounds():
    w = {"temperature": 0.30, "environmental": 0.20,
         "vulnerability": 0.20, "service_access": 0.15, "mobility": 0.15}
    # Trying to push well below zero — should be clamped to 0.01
    new_w = _renormalise(w, "temperature", -0.99)
    assert new_w["temperature"] >= 0.01


# ── Travel penalty modifier ────────────────────────────────────────────────────

def test_apply_travel_penalty_preserves_selection_count():
    df = _make_pipeline_df()
    n_orig = int(df["selected_for_outreach"].sum())
    out    = _apply_travel_penalty(df, factor=0.5)
    assert int(out["selected_for_outreach"].sum()) == n_orig


def test_apply_travel_penalty_high_factor_prefers_close():
    df = _make_pipeline_df()
    out = _apply_travel_penalty(df, factor=2.0)
    sel_dist  = out.loc[out["selected_for_outreach"], "healthcare_distance_km"].mean()
    nsel_dist = out.loc[~out["selected_for_outreach"], "healthcare_distance_km"].mean()
    assert sel_dist <= nsel_dist  # selected should be closer on average


# ── Fairness weight modifier ───────────────────────────────────────────────────

def test_apply_fairness_weight_preserves_selection_count():
    df = _make_pipeline_df()
    n_orig = int(df["selected_for_outreach"].sum())
    out    = _apply_fairness_weight(df, weight=0.8)
    assert int(out["selected_for_outreach"].sum()) == n_orig


def test_apply_fairness_weight_high_increases_group_coverage():
    df = _make_pipeline_df()
    base_grp = (df["group_mobile"] & df["selected_for_outreach"]).sum()
    out = _apply_fairness_weight(df, weight=0.9)
    new_grp  = (df["group_mobile"] & out["selected_for_outreach"]).sum()
    assert new_grp >= base_grp  # fairness weight should not reduce group coverage


# ── Compute metrics ───────────────────────────────────────────────────────────

def test_compute_metrics_returns_required_keys():
    df = _make_pipeline_df()
    m  = _compute_metrics(df)
    assert "high_risk_coverage_pct" in m
    assert "fairness_gap_pct"       in m
    assert "total_selected"         in m


def test_compute_metrics_coverage_bounded():
    df = _make_pipeline_df()
    m  = _compute_metrics(df)
    assert 0.0 <= m["high_risk_coverage_pct"] <= 100.0
    assert 0.0 <= m["fairness_gap_pct"] <= 100.0


# ── Risk explainer ────────────────────────────────────────────────────────────

def _make_row_with_explainability(seed=0):
    rng = np.random.default_rng(seed)
    expl = {
        "model_version": "2.0.0",
        "factors": {
            "temperature":   {"raw": 38.5, "normalized": 0.7, "weight": 0.30, "contribution": 0.21},
            "environmental": {"normalized": 0.5, "weight": 0.20, "contribution": 0.10},
            "vulnerability": {"normalized": 0.6, "weight": 0.20, "contribution": 0.12},
            "service_access":{"normalized": 0.4, "weight": 0.15, "contribution": 0.06},
            "mobility":      {"normalized": 0.3, "weight": 0.15, "contribution": 0.045},
        },
        "final_score": 0.535,
        "risk_level": "HIGH",
    }
    return pd.Series({
        "neighbourhood_id":           "N001",
        "multi_factor_risk_category": "HIGH",
        "multi_factor_risk_score":    0.535,
        "risk_explainability":        json.dumps(expl),
        "temperature_c":              38.5,
        "heat_index":                 42.0,
        "healthcare_distance_km":     6.0,
        "vulnerability_index":        0.65,
        "built_density":              0.72,
        "green_cover_percent":        0.08,
        "mobile_population":          120,
        "elderly_population_percent": 0.25,
    })


def test_explain_risk_returns_factor_table():
    row = _make_row_with_explainability()
    result = explain_risk(row)
    assert result["risk_category"] == "HIGH"
    assert abs(result["risk_score"] - 0.535) < 0.001
    assert len(result["factor_table"]) == 5
    for entry in result["factor_table"]:
        assert "Factor" in entry
        assert "Weight" in entry
        assert "Contribution" in entry


def test_explain_risk_narrative_not_empty():
    row = _make_row_with_explainability()
    result = explain_risk(row)
    assert len(result["narrative"]) > 20


def test_explain_risk_legacy_fallback():
    """When no risk_explainability JSON, falls back gracefully."""
    row = pd.Series({
        "neighbourhood_id":           "N002",
        "multi_factor_risk_category": "MODERATE",
        "multi_factor_risk_score":    0.40,
        "temperature_c":              35.0,
    })
    result = explain_risk(row)
    assert result["risk_score"] == 0.40
    assert len(result["factor_contributions"]) > 0
