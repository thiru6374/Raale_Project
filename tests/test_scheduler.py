"""
tests/test_scheduler.py

Phase 5: Geographic Clustering & Outreach Scheduling tests.
Covers:
  - team assignment
  - cluster map data correctness
  - missing GPS handling
  - capacity-overflow isolation
  - schedule column completeness
  - 50K-row performance
"""
import time
import pytest
import numpy as np
import pandas as pd

from src.config.settings import settings
from src.optimisation.scheduler import OutreachScheduler


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_selected_df(n: int, lat_base: float = 13.0, lon_base: float = 80.0) -> pd.DataFrame:
    """Return a DataFrame of n neighbourhoods all selected for outreach."""
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "neighbourhood_id": [f"N{i}" for i in range(n)],
        "neighbourhood_name": [f"Hood_{i}" for i in range(n)],
        "selected_for_outreach": [True] * n,
        "latitude": lat_base + rng.uniform(-0.15, 0.15, n),
        "longitude": lon_base + rng.uniform(-0.15, 0.15, n),
        "population": rng.integers(500, 5000, n),
        "mobile_population": rng.integers(50, 500, n),
        "healthcare_distance_km": rng.uniform(1.0, 20.0, n),
        "multi_factor_risk_category": rng.choice(["EXTREME", "HIGH", "MODERATE", "LOW"], n),
        "group_low_service_access": rng.choice([True, False], n),
    })


# ─────────────────────────────────────────────────────────────────────────────
# 1. Basic assignment
# ─────────────────────────────────────────────────────────────────────────────

def test_scheduler_assigns_teams_and_times():
    settings.number_of_teams = 3
    settings.maximum_visits_per_team = 10
    settings.working_hours = 12.0

    df = _make_selected_df(9)
    scheduler = OutreachScheduler()
    result_df, schedules = scheduler.schedule_plan(df)

    sel = result_df[result_df["selected_for_outreach"] == True]

    assert not sel.empty
    # Every selected row must have a team, date, start and end time
    assert sel["assigned_team"].notna().all()
    assert sel["outreach_date"].notna().all()
    assert sel["start_time"].notna().all()
    assert sel["end_time"].notna().all()

    # Team IDs follow the "Team_N" pattern
    assert sel["assigned_team"].str.startswith("Team_").all()


def test_scheduler_cluster_ids_are_integers():
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 10

    df = _make_selected_df(6)
    scheduler = OutreachScheduler()
    result_df, _ = scheduler.schedule_plan(df)

    cluster_ids = result_df.loc[result_df["selected_for_outreach"] == True, "cluster_id"].dropna()
    assert (cluster_ids.astype(int) >= 0).all(), "Cluster IDs must be non-negative integers"


def test_unselected_rows_have_no_team():
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 5

    df = _make_selected_df(4)
    # Un-select last two
    df.loc[2, "selected_for_outreach"] = False
    df.loc[3, "selected_for_outreach"] = False

    scheduler = OutreachScheduler()
    result_df, _ = scheduler.schedule_plan(df)

    assert pd.isna(result_df.loc[2, "assigned_team"])
    assert pd.isna(result_df.loc[3, "assigned_team"])


# ─────────────────────────────────────────────────────────────────────────────
# 2. Cluster-map data
# ─────────────────────────────────────────────────────────────────────────────

def test_num_unique_teams_matches_num_clusters():
    settings.number_of_teams = 4
    settings.maximum_visits_per_team = 10

    df = _make_selected_df(8)
    scheduler = OutreachScheduler()
    result_df, schedules = scheduler.schedule_plan(df)

    # Number of unique teams in the schedule summary should be ≤ num_teams
    assert len(schedules) <= settings.number_of_teams


# ─────────────────────────────────────────────────────────────────────────────
# 3. Missing GPS handling
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_gps_falls_back_to_single_cluster():
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 5

    df = _make_selected_df(4)
    df["latitude"] = np.nan
    df["longitude"] = np.nan

    scheduler = OutreachScheduler()
    result_df, schedules = scheduler.schedule_plan(df)

    # All selected should fall back to cluster 0
    sel = result_df[result_df["selected_for_outreach"] == True]
    assert (sel["cluster_id"] == 0).all()


def test_partial_missing_gps():
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 10

    df = _make_selected_df(6)
    df.loc[0, "latitude"] = np.nan  # one invalid row
    df.loc[0, "longitude"] = np.nan

    scheduler = OutreachScheduler()
    result_df, schedules = scheduler.schedule_plan(df)

    # Scheduler should not crash and should return a non-empty schedule
    assert not schedules.empty


# ─────────────────────────────────────────────────────────────────────────────
# 4. Capacity-overflow isolation
# ─────────────────────────────────────────────────────────────────────────────

def test_overflow_isolates_extra_rows():
    settings.number_of_teams = 1
    settings.maximum_visits_per_team = 2

    df = _make_selected_df(4)
    scheduler = OutreachScheduler()
    result_df, schedules = scheduler.schedule_plan(df)

    # With 4 rows and capacity 2, at least 2 should be isolated
    assert result_df["is_isolated"].sum() >= 2


def test_schedule_reflects_empty_input():
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 5

    df = _make_selected_df(4)
    df["selected_for_outreach"] = False  # None selected

    scheduler = OutreachScheduler()
    result_df, schedules = scheduler.schedule_plan(df)

    assert schedules.empty


# ─────────────────────────────────────────────────────────────────────────────
# 5. Team summary columns
# ─────────────────────────────────────────────────────────────────────────────

def test_team_schedule_columns_present():
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 5

    df = _make_selected_df(6)
    scheduler = OutreachScheduler()
    _, schedules = scheduler.schedule_plan(df)

    required = {"Team", "Events", "Utilization (%)", "Status", "Shift Hours"}
    assert required.issubset(set(schedules.columns)), f"Missing columns: {required - set(schedules.columns)}"


def test_utilization_within_valid_range():
    settings.number_of_teams = 2
    settings.maximum_visits_per_team = 5

    df = _make_selected_df(6)
    scheduler = OutreachScheduler()
    _, schedules = scheduler.schedule_plan(df)

    assert (schedules["Utilization (%)"] >= 0).all()
    assert (schedules["Utilization (%)"] <= 100).all()


# ─────────────────────────────────────────────────────────────────────────────
# 6. 50K-row performance test
# ─────────────────────────────────────────────────────────────────────────────

def test_scheduler_50k_rows_under_10_seconds():
    """Scheduler must complete for 50,000 selected rows in under 10 seconds."""
    settings.number_of_teams = 10
    settings.maximum_visits_per_team = 5000  # so nothing gets isolated

    rng = np.random.default_rng(0)
    n = 50_000
    df = pd.DataFrame({
        "neighbourhood_id": [f"N{i}" for i in range(n)],
        "neighbourhood_name": [f"Hood_{i}" for i in range(n)],
        "selected_for_outreach": [True] * n,
        "latitude": 13.0 + rng.uniform(-0.3, 0.3, n),
        "longitude": 80.0 + rng.uniform(-0.3, 0.3, n),
        "population": rng.integers(500, 5000, n),
        "mobile_population": rng.integers(50, 500, n),
        "healthcare_distance_km": rng.uniform(1.0, 20.0, n),
        "multi_factor_risk_category": rng.choice(["EXTREME", "HIGH", "MODERATE", "LOW"], n),
        "group_low_service_access": rng.choice([True, False], n),
    })

    scheduler = OutreachScheduler()
    t0 = time.time()
    result_df, schedules = scheduler.schedule_plan(df)
    elapsed = time.time() - t0

    assert elapsed < 10.0, f"Scheduler took {elapsed:.1f}s for 50K rows (limit: 10s)"
    assert not schedules.empty
    assert result_df["assigned_team"].notna().sum() > 0
