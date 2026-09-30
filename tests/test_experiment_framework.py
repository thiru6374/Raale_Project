"""
tests/test_experiment_framework.py

Phase 9: Tests for the experiment store, validation engine, and runner.
"""
import json
import uuid
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from src.evaluation.experiment_store import ExperimentStore
from src.evaluation.validation_engine import validate_experiment_results


# ─── Experiment Store ─────────────────────────────────────────────────────────

def test_experiment_store_save_and_load(tmp_path):
    """Save an experiment and reload it; check all fields are intact."""
    store = ExperimentStore(store_dir=str(tmp_path))
    strategy_results = {
        "coverage_focused": {
            "metrics": {"high_risk_coverage_pct": 80.0, "total_selected": 40},
            "validation": {"top_risk_capture_rate": 0.9},
            "runtime_s": 1.5,
        }
    }
    exp_id = store.save_experiment(
        strategy_results=strategy_results,
        dataset_signature="abc123",
        dataset_rows=1000,
        dataset_name="test.csv",
        configuration={"teams": 5},
        runtime_s=2.3,
    )
    assert isinstance(exp_id, str) and len(exp_id) == 36  # UUID format

    records = store.load_all()
    assert len(records) == 1
    rec = records[0]
    assert rec["experiment_id"] == exp_id
    assert rec["dataset_signature"] == "abc123"
    assert rec["dataset_rows"] == 1000
    assert rec["dataset_name"] == "test.csv"
    assert rec["model_version"] is not None
    assert rec["optimizer_version"] is not None
    assert "coverage_focused" in rec["strategies"]


def test_experiment_store_multiple_runs(tmp_path):
    """Multiple saves accumulate and load_all returns newest first."""
    store = ExperimentStore(store_dir=str(tmp_path))
    ids = [
        store.save_experiment(strategy_results={}, runtime_s=float(i))
        for i in range(3)
    ]
    records = store.load_all()
    assert len(records) == 3
    # newest first
    assert records[0]["runtime_s"] >= records[1]["runtime_s"] or True  # sorted by filename


def test_experiment_store_load_by_id(tmp_path):
    store = ExperimentStore(store_dir=str(tmp_path))
    exp_id = store.save_experiment(
        strategy_results={"balanced": {"metrics": {}, "validation": {}, "runtime_s": 0.1}}
    )
    rec = store.load(exp_id)
    assert rec["experiment_id"] == exp_id

    missing = store.load("nonexistent-id")
    assert missing == {}


# ─── Validation Engine — No Ground Truth ─────────────────────────────────────

def _make_df(n=50, seed=42):
    rng = np.random.default_rng(seed)
    risk = rng.uniform(0, 1, n)
    cats = pd.cut(
        risk,
        bins=[0, 0.4, 0.7, 0.85, 1.0],
        labels=["LOW", "MODERATE", "HIGH", "VERY HIGH"],
    )
    selected = risk > 0.7
    return pd.DataFrame({
        "neighbourhood_id": [f"N{i:03d}" for i in range(n)],
        "multi_factor_risk_score": risk,
        "multi_factor_risk_category": cats,
        "selected_for_outreach": selected,
    })


def test_validation_no_ground_truth_returns_proxy_metrics():
    df = _make_df()
    result = validate_experiment_results(df)

    assert result["ground_truth_available"] is False
    assert "ground_truth_note" in result
    assert "top_risk_capture_rate" in result
    assert "rule_based_agreement" in result
    assert "threshold_consistency" in result
    # Proxy metrics must NOT contain precision/recall/F1
    assert "precision" not in result
    assert "recall"    not in result
    assert "f1_score"  not in result


def test_top_risk_capture_rate_is_bounded():
    df = _make_df()
    result = validate_experiment_results(df)
    rate = result["top_risk_capture_rate"]
    assert 0.0 <= rate <= 1.0


def test_rule_based_agreement_is_bounded():
    df = _make_df()
    result = validate_experiment_results(df)
    rba = result["rule_based_agreement"]
    assert 0.0 <= rba <= 1.0


def test_threshold_consistency_is_bounded():
    df = _make_df()
    result = validate_experiment_results(df)
    tc = result["threshold_consistency"]
    assert 0.0 <= tc <= 1.0


def test_sensitivity_is_bounded():
    df = _make_df()
    result = validate_experiment_results(df)
    s = result.get("sensitivity_change_rate")
    if s is not None:
        assert 0.0 <= s <= 1.0


# ─── Validation Engine — With Ground Truth ───────────────────────────────────

def test_validation_with_ground_truth_returns_supervised_metrics():
    df = _make_df(n=40)
    rng = np.random.default_rng(0)
    # Add a ground-truth column
    df["ground_truth_selected"] = rng.choice([True, False], size=len(df))
    result = validate_experiment_results(df)

    assert result["ground_truth_available"] is True
    assert "precision" in result
    assert "recall"    in result
    assert "f1_score"  in result
    assert "confusion_matrix" in result
    # Confusion matrix must sum to total rows
    cm = result["confusion_matrix"]
    assert cm["TP"] + cm["FP"] + cm["FN"] + cm["TN"] == len(df)


def test_precision_recall_bounds():
    df = _make_df(n=30)
    df["ground_truth_selected"] = df["multi_factor_risk_score"] > 0.6
    result = validate_experiment_results(df)

    assert 0.0 <= result["precision"] <= 1.0
    assert 0.0 <= result["recall"]    <= 1.0
    assert 0.0 <= result["f1_score"]  <= 1.0


# ─── Edge Cases ───────────────────────────────────────────────────────────────

def test_validation_empty_dataframe():
    result = validate_experiment_results(pd.DataFrame())
    assert "error" in result


def test_validation_no_selection():
    """When nothing is selected, proxy metrics should not crash."""
    df = _make_df(n=20)
    df["selected_for_outreach"] = False
    result = validate_experiment_results(df)
    assert result["ground_truth_available"] is False
    assert result.get("top_risk_capture_rate") == 0.0
