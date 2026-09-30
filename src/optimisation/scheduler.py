"""
src/optimisation/scheduler.py

Phase 5: Geographic Clustering and Outreach Scheduling

Generates realistic geographic routes and schedules based on the optimization plan.

Clustering strategy: KMeans – chosen because:
  - Works well on lat/lon data at city scale
  - Groups by geographic proximity (minimises intra-team travel)
  - Number of clusters maps directly to number of teams
  - Handles 50K rows efficiently (sklearn KMeans is vectorized)

Fallback for missing GPS:
  - Rows without valid lat/lon are assigned to cluster 0 without clustering

Respects Phase 4 hard constraints (capacity per team per day).

Returns:
    (augmented_df, team_schedules_df)
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple

from scipy.cluster.vq import kmeans2
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("outreach_scheduler")

_VISIT_DURATION_MIN = 45   # minutes per visit
_TRAVEL_BUFFER_MIN  = 15   # travel buffer between visits
_EVENT_SLOT_H       = (_VISIT_DURATION_MIN + _TRAVEL_BUFFER_MIN) / 60.0  # 1 hour
_AVG_SPEED_KMPH     = 30.0  # urban average speed


class OutreachScheduler:
    """
    Geographically clusters selected neighbourhoods and assigns realistic
    daily team schedules that respect Phase 4 hard constraints.
    """

    def __init__(self):
        self.num_teams  = settings.number_of_teams
        self.max_visits = settings.maximum_visits_per_team
        self.shift_h    = settings.working_hours

    def schedule_plan(
        self,
        df: pd.DataFrame,
        target_date: str = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Cluster and schedule outreach for selected neighbourhoods.

        Parameters
        ----------
        df           Full pipeline DataFrame (post optimization).
        target_date  YYYY-MM-DD string for scheduling; defaults to today.

        Returns
        -------
        (result_df, team_schedules_df)
        result_df          – original df with added scheduling columns.
        team_schedules_df  – one row per team summarising daily utilization.
        """
        logger.info("Initializing geographic clustering and scheduling…")
        result_df = df.copy()

        # Initialise scheduling output columns with safe defaults
        result_df["cluster_id"]    = pd.NA
        result_df["assigned_team"] = pd.NA
        result_df["outreach_date"] = pd.NA
        result_df["start_time"]    = pd.NA
        result_df["end_time"]      = pd.NA
        result_df["is_isolated"]   = False

        selected_mask = result_df["selected_for_outreach"] == True  # noqa: E712
        if not selected_mask.any():
            logger.warning("No neighbourhoods selected for outreach — schedule is empty.")
            return result_df, pd.DataFrame()

        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")

        # ── Step 1: KMeans geographic clustering ─────────────────────────────
        sel_idx = result_df.index[selected_mask]

        # Check for lat/lon columns
        has_lat_col = "latitude" in result_df.columns
        has_lon_col = "longitude" in result_df.columns

        if has_lat_col and has_lon_col:
            has_geo = (
                result_df.loc[sel_idx, "latitude"].notna()
                & result_df.loc[sel_idx, "longitude"].notna()
            )
            geo_idx    = sel_idx[has_geo]
            no_geo_idx = sel_idx[~has_geo]
        else:
            # No geo columns at all — assign everything to cluster 0
            geo_idx    = pd.Index([], dtype=sel_idx.dtype)
            no_geo_idx = sel_idx

        if len(geo_idx) > 0:
            coords = result_df.loc[geo_idx, ["latitude", "longitude"]].values
            n_clusters = min(self.num_teams, len(geo_idx))
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                centroids, labels = kmeans2(coords.astype(float), n_clusters, minit='points')
            
            result_df.loc[geo_idx, "cluster_id"] = labels
        else:
            logger.warning("No valid GPS coordinates — all selected rows assigned to cluster 0.")

        # Rows without GPS → cluster 0
        if len(no_geo_idx) > 0:
            result_df.loc[no_geo_idx, "cluster_id"] = 0

        # ── Step 2: Assign teams and build time-slots (vectorized per cluster) ──
        team_summaries = []
        base_dt = datetime.strptime(target_date + " 08:00:00", "%Y-%m-%d %H:%M:%S")

        clustered_mask = result_df["cluster_id"].notna() & selected_mask
        for cluster_id, grp_idx in result_df[clustered_mask].groupby("cluster_id").groups.items():
            team_id = f"Team_{int(cluster_id) + 1}"

            # Sort within cluster by latitude (north→south sweep) to minimise backtracking
            if "latitude" in result_df.columns:
                sorted_idx = (
                    result_df.loc[grp_idx, "latitude"]
                    .sort_values()
                    .index
                )
            else:
                sorted_idx = grp_idx

            # Split into capacity window vs overflow
            within_cap = sorted_idx[:self.max_visits]
            overflow   = sorted_idx[self.max_visits:]

            # Mark overflow as isolated (informational only — do NOT mutate selected_for_outreach;
            # the Phase 4 ConstraintEngine is the single authority on feasibility)
            if len(overflow) > 0:
                result_df.loc[overflow, "is_isolated"] = True
                logger.warning(
                    "Team %s overloaded: %d neighbourhood(s) marked isolated (informational).",
                    team_id, len(overflow)
                )

            # Assign team and time-slots to within-capacity rows (vectorised)
            n_events = len(within_cap)
            result_df.loc[within_cap, "assigned_team"] = team_id
            result_df.loc[within_cap, "outreach_date"] = target_date

            # Time-slot calculation: slot i starts at base + i * _EVENT_SLOT_H hours
            slot_offsets = np.arange(n_events)
            start_times = [
                (base_dt + timedelta(hours=float(i) * _EVENT_SLOT_H)).strftime("%H:%M")
                for i in slot_offsets
            ]
            end_times = [
                (base_dt + timedelta(hours=float(i) * _EVENT_SLOT_H, minutes=_VISIT_DURATION_MIN)).strftime("%H:%M")
                for i in slot_offsets
            ]
            result_df.loc[within_cap, "start_time"] = start_times
            result_df.loc[within_cap, "end_time"]   = end_times

            # ── Team summary stats ──────────────────────────────────────────
            grp = result_df.loc[within_cap]

            pop_col = "population" if "population" in grp.columns else "mobile_population"
            total_pop       = int(grp[pop_col].fillna(0).sum())        if pop_col in grp.columns else 0
            total_mobile    = int(grp["mobile_population"].fillna(0).sum()) if "mobile_population" in grp.columns else 0
            total_dist_km   = float(grp["healthcare_distance_km"].fillna(0).sum()) if "healthcare_distance_km" in grp.columns else 0.0

            # Low-service-access target population
            if "group_low_service_access" in grp.columns:
                low_svc_mask = grp["group_low_service_access"] == True  # noqa: E712
                total_low_svc = int(grp.loc[low_svc_mask, pop_col].fillna(0).sum()) if pop_col in grp.columns else 0
            else:
                total_low_svc = 0

            shift_h     = n_events * _EVENT_SLOT_H
            utilization = (n_events / self.max_visits * 100.0) if self.max_visits > 0 else 0.0

            if shift_h > self.shift_h:
                status = "OVERLOADED"
            elif n_events == 0:
                status = "IDLE"
            else:
                status = "HEALTHY"

            team_summaries.append({
                "Team":                team_id,
                "Events":              n_events,
                "Population Target":   total_pop,
                "Mobile Pop Target":   total_mobile,
                "Low-Service Target":  total_low_svc,
                "Travel Dist (km)":    round(total_dist_km, 1),
                "Travel Time (hrs)":   round(total_dist_km / _AVG_SPEED_KMPH, 1),
                "Shift Hours":         round(shift_h, 1),
                "Utilization (%)":     round(min(utilization, 100.0), 1),
                "Status":              status,
            })

        schedule_df = pd.DataFrame(team_summaries)
        total_events = int(schedule_df["Events"].sum()) if not schedule_df.empty else 0
        logger.info(
            "Schedule generated: %d teams, %d events.", len(schedule_df), total_events
        )
        return result_df, schedule_df
