"""
tests/test_optimizer.py

Comprehensive test suite for the Phase 3 multi-objective outreach optimizer.

Covers:
  - All three strategy variants
  - Objective weight profiles
  - Capacity constraint enforcement
  - Fallback / MANUAL_REVIEW blocking
  - Full per-run metrics calculation
  - OptimizationRunStore persistence
  - Experiment runner (all 3 strategies on same data)
  - 50k-row dataset smoke test (sampling for speed)
"""
import json
import time
import pytest
import pandas as pd
import numpy as np

from src.optimisation.planner import OutreachPlanner
from src.optimisation.objectives import get_strategy_weights, build_objective_function
from src.optimisation.run_store import OptimizationRunStore
from src.evaluation.metrics import calculate_evaluation_metrics
from src.config.settings import settings


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_df(n: int = 20, risk_score: float = 0.8, strategy: str = "COVERAGE_FOCUSED") -> pd.DataFrame:
    """Create a minimal DataFrame with all columns expected by the planner."""
    np.random.seed(42)
    return pd.DataFrame({
        "neighbourhood_id":          [f"N{i}" for i in range(n)],
        "neighbourhood_name":        [f"Area {i}" for i in range(n)],
        "multi_factor_risk_score":   np.random.uniform(0.0, 1.0, n),
        "multi_factor_risk_category": np.random.choice(
            ["LOW", "MODERATE", "HIGH", "VERY HIGH"], n
        ),
        "mobile_population":         np.random.uniform(100, 1000, n),
        "vulnerability_index":       np.random.uniform(0.0, 1.0, n),
        "healthcare_distance_km":    np.random.uniform(1.0, 15.0, n),
        "transport_access_score":    np.random.uniform(0.0, 1.0, n),
        "group_mobile":              np.random.choice([True, False], n),
        "group_low_service_access":  np.random.choice([True, False], n),
        "fallback_status":           ["STANDARD"] * n,
        "is_spatially_schedulable":  [True] * n,
    })


# ── Strategy weight profiles ──────────────────────────────────────────────────

def test_strategy_weights_sum_to_one():
    """All canonical strategy weight profiles must sum to exactly 1.0."""
    for strategy in ["COVERAGE_FOCUSED", "BALANCED", "FAIRNESS_AWARE"]:
        w = get_strategy_weights(strategy)
        total = sum(w.values())
        assert abs(total - 1.0) < 1e-9, f"Weights for {strategy} sum to {total}"


def test_strategy_weights_all_non_negative():
    for strategy in ["COVERAGE_FOCUSED", "BALANCED", "FAIRNESS_AWARE"]:
        w = get_strategy_weights(strategy)
        for k, v in w.items():
            assert v >= 0.0, f"Weight {k} in {strategy} is negative: {v}"


def test_unknown_strategy_defaults_gracefully():
    """Unknown strategy names fall back to COVERAGE_FOCUSED silently."""
    w = get_strategy_weights("NONEXISTENT_STRATEGY")
    baseline = get_strategy_weights("COVERAGE_FOCUSED")
    assert w == baseline


# ── Planner — strategy execution ──────────────────────────────────────────────

@pytest.mark.parametrize("strategy", ["COVERAGE_FOCUSED", "BALANCED", "FAIRNESS_AWARE"])
def test_planner_runs_all_strategies(strategy):
    """All three strategies must return a valid, non-empty DataFrame."""
    settings.number_of_teams = 3
    settings.maximum_visits_per_team = 5
    df = _make_df(30)

    planner = OutreachPlanner()
    result = planner.plan_outreach(df, strategy=strategy)

    assert "selected_for_outreach" in result.columns
    assert "outreach_priority" in result.columns
    assert "optimization_strategy" in result.columns
    assert result["optimization_strategy"].unique()[0] == strategy
    assert result["selected_for_outreach"].dtype == bool


@pytest.mark.parametrize("strategy", ["COVERAGE_FOCUSED", "BALANCED", "FAIRNESS_AWARE"])
def test_planner_respects_capacity(strategy):
    """Regardless of strategy, selections must never exceed max_teams × visits_per_team."""
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 4
    df = _make_df(50)
    df["multi_factor_risk_score"] = 0.99
    df["multi_factor_risk_category"] = "VERY HIGH"

    planner = OutreachPlanner()
    result = planner.plan_outreach(df, strategy=strategy)

    assert result["selected_for_outreach"].sum() <= 8, \
        f"{strategy}: selected {result['selected_for_outreach'].sum()} > capacity 8"


def test_planner_blocks_manual_review_records():
    """MANUAL_REVIEW fallback records must never be selected."""
    settings.number_of_teams = 5
    settings.maximum_visits_per_team = 10

    df = _make_df(20)
    df.loc[:9, "fallback_status"] = "MANUAL_REVIEW"
    df.loc[:9, "multi_factor_risk_score"] = 1.0  # highest risk — but blocked

    planner = OutreachPlanner()
    result = planner.plan_outreach(df)

    blocked = result[result["fallback_status"] == "MANUAL_REVIEW"]
    assert not blocked["selected_for_outreach"].any(), \
        "MANUAL_REVIEW records were selected — constraint violated"


def test_planner_unreachable_records_not_selected():
    """Records with is_spatially_schedulable=False must not be selected."""
    settings.number_of_teams = 5
    settings.maximum_visits_per_team = 20

    df = _make_df(10)
    df["is_spatially_schedulable"] = [True, False] * 5
    df["multi_factor_risk_score"] = 1.0

    planner = OutreachPlanner()
    result = planner.plan_outreach(df)

    unreachable = result[~result["is_spatially_schedulable"]]
    assert not unreachable["selected_for_outreach"].any()


# ── Per-run metrics ───────────────────────────────────────────────────────────

def test_planner_computes_metrics_in_result():
    """The planner should store an optimization_run_id on the result DataFrame."""
    settings.number_of_teams = 3
    settings.maximum_visits_per_team = 5
    df = _make_df(20)

    planner = OutreachPlanner()
    result = planner.plan_outreach(df, strategy="BALANCED")

    assert "optimization_run_id" in result.columns


def test_calculate_evaluation_metrics_full():
    """Full metrics calculation must return all required keys."""
    settings.number_of_teams = 3
    settings.maximum_visits_per_team = 5
    df = _make_df(20)
    planner = OutreachPlanner()
    result = planner.plan_outreach(df)

    metrics = calculate_evaluation_metrics(result, strategy_name="COVERAGE_FOCUSED")

    required_keys = [
        "strategy", "total_analyzed", "high_risk_identified", "high_risk_reached",
        "high_risk_coverage_pct", "total_selected", "total_population_reached",
        "mobile_population_reached", "low_service_access_reached",
        "travel_distance_total_km", "estimated_travel_time_h", "num_outreach_events",
        "capacity_utilization_pct", "fairness_gap_pct", "avg_selected_risk_score",
    ]
    for key in required_keys:
        assert key in metrics, f"Missing metric key: {key}"


def test_metrics_coverage_values_in_range():
    """All percentage metrics must be in [0, 100]."""
    settings.number_of_teams = 3
    settings.maximum_visits_per_team = 5
    df = _make_df(30)
    planner = OutreachPlanner()
    result = planner.plan_outreach(df)
    metrics = calculate_evaluation_metrics(result)

    for pct_key in ["high_risk_coverage_pct", "capacity_utilization_pct", "fairness_gap_pct"]:
        assert 0.0 <= metrics[pct_key] <= 100.0, \
            f"{pct_key} = {metrics[pct_key]} is out of [0, 100]"


def test_metrics_all_three_strategies_differ():
    """
    Metrics for COVERAGE_FOCUSED, BALANCED, and FAIRNESS_AWARE on the same
    data should differ in at least one measurable dimension.
    """
    settings.number_of_teams = 3
    settings.maximum_visits_per_team = 8
    settings.maximum_travel_distance = 1000.0
    settings.maximum_travel_time = 2000
    settings.working_hours = 24.0
    df = _make_df(40)

    planner = OutreachPlanner()
    metrics = {}
    for strategy in ["COVERAGE_FOCUSED", "BALANCED", "FAIRNESS_AWARE"]:
        result = planner.plan_outreach(df.copy(), strategy=strategy)
        metrics[strategy] = calculate_evaluation_metrics(result, strategy_name=strategy)

    # Objective scores should not all be identical (they use different weight profiles)
    obj_scores = [m["high_risk_coverage_pct"] for m in metrics.values()]
    # At least one pair of strategies produces a different selection set
    # (This is an existence check — exact values depend on the MIP solver)
    assert not (obj_scores[0] == obj_scores[1] == obj_scores[2]), \
        "All three strategies produced identical results — objective function may be broken"


# ── Persistence ───────────────────────────────────────────────────────────────

def test_run_store_saves_and_loads(tmp_path):
    store = OptimizationRunStore(store_dir=str(tmp_path))
    metrics = {"risk_coverage_pct": 82.5, "total_selected": 10}
    weights = get_strategy_weights("BALANCED")

    run_id = store.save(
        strategy="BALANCED",
        objective_weights=weights,
        metrics=metrics,
        dataset_signature="abc123",
        runtime_s=1.234,
    )

    records = store.load_all()
    assert len(records) == 1
    r = records[0]
    assert r["run_id"] == run_id
    assert r["strategy"] == "BALANCED"
    assert r["dataset_signature"] == "abc123"
    assert r["metrics"]["risk_coverage_pct"] == 82.5
    assert abs(r["runtime_s"] - 1.234) < 0.001


def test_run_store_load_by_id(tmp_path):
    store = OptimizationRunStore(store_dir=str(tmp_path))
    run_id = store.save("FAIRNESS_AWARE", {}, {})
    record = store.load(run_id)
    assert record["run_id"] == run_id
    assert record["strategy"] == "FAIRNESS_AWARE"


def test_run_store_missing_id_returns_empty(tmp_path):
    store = OptimizationRunStore(store_dir=str(tmp_path))
    assert store.load("nonexistent-id") == {}


# ── Experiment runner ─────────────────────────────────────────────────────────

def test_experiment_runner_all_strategies():
    """ExperimentRunner must return SUCCESS with all three strategy keys."""
    from src.evaluation.experiment_runner import ExperimentRunner
    runner = ExperimentRunner(num_records=10)
    results = runner.run_comparison()

    assert results["status"] == "SUCCESS"
    assert "coverage_focused" in results
    assert "balanced" in results
    assert "fairness_aware" in results

    for key in ["coverage_focused", "balanced", "fairness_aware"]:
        assert results[key]["metrics"]["total_analyzed"] > 0


def test_experiment_runner_same_dataset():
    """All three strategies must analyze the same number of records."""
    from src.evaluation.experiment_runner import ExperimentRunner
    runner = ExperimentRunner(num_records=10)
    results = runner.run_comparison()

    totals = [
        results["coverage_focused"]["metrics"]["total_analyzed"],
        results["balanced"]["metrics"]["total_analyzed"],
        results["fairness_aware"]["metrics"]["total_analyzed"],
    ]
    assert totals[0] == totals[1] == totals[2], \
        f"Dataset sizes differ across strategies: {totals}"


# ── 50k-row dataset smoke test ────────────────────────────────────────────────

def test_optimizer_with_50k_dataset_sample():
    """
    Verify the optimizer works correctly on a sample from the 50k Chennai dataset.
    Uses PipelineService with num_records=50 for speed while confirming real data.
    """
    from src.services.pipeline_service import PipelineService
    settings.maximum_travel_distance = 1000.0
    settings.maximum_travel_time = 2000
    settings.working_hours = 24.0
    result = PipelineService.run_full_pipeline(num_records=50, strategy="BALANCED")

    assert result["status"] == "SUCCESS", f"Pipeline failed: {result.get('errors')}"
    df = result["pipeline_results"]
    assert "selected_for_outreach" in df.columns
    assert "optimization_strategy" in df.columns
    assert df["optimization_strategy"].iloc[0] == "BALANCED"

    # Capacity never exceeded
    max_cap = settings.number_of_teams * settings.maximum_visits_per_team
    assert df["selected_for_outreach"].sum() <= max_cap
