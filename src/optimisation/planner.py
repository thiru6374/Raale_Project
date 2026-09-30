"""
src/optimisation/planner.py

Multi-objective Outreach Optimization Engine.

Every call to plan_outreach():
  1. Builds binary MIP via PuLP
  2. Applies capacity / fallback constraints
  3. Solves with CBC
  4. Computes full per-run metrics
  5. Persists the run via OptimizationRunStore

Three canonical strategies are supported:
  COVERAGE_FOCUSED  – prioritises highest-risk neighbourhoods
  BALANCED          – balances risk, fairness, and travel cost
  FAIRNESS_AWARE    – maximises reach of vulnerable / low-access groups
"""
import time
import pulp
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from src.config.settings import settings
from src.utils.logger import get_logger
from src.optimisation.constraints import apply_capacity_constraints
from src.optimisation.objectives import build_objective_function, get_strategy_weights
from src.optimisation.run_store import OptimizationRunStore
from src.optimisation.constraint_engine import ConstraintEngine
from src.optimisation.scheduler import OutreachScheduler

logger = get_logger("outreach_planner")


def _safe(val, default: float = 0.0) -> float:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return float(val)


class OutreachPlanner:
    """Multi-objective MIP-based outreach assignment planner."""

    def plan_outreach(
        self,
        df: pd.DataFrame,
        strategy: str = "COVERAGE_FOCUSED",
        custom_weights: Optional[Dict[str, float]] = None,
        dataset_signature: str = "",
    ) -> pd.DataFrame:
        """
        Solve the outreach assignment problem and return an augmented DataFrame.

        Parameters
        ----------
        df                Input DataFrame (post risk-scoring + confidence).
        strategy          One of COVERAGE_FOCUSED | BALANCED | FAIRNESS_AWARE.
        custom_weights    Optional override for objective weight coefficients.
        dataset_signature Dataset hash for audit provenance.
        """
        logger.info("Initializing multi-objective optimization planner (Strategy: %s)...", strategy)
        t0 = time.time()
        result_df = df.copy()

        # 1. MIP model ──────────────────────────────────────────────────────────
        model = pulp.LpProblem("Neighbourhood_Outreach_Assignment", pulp.LpMaximize)

        # 2. Binary decision variables ─────────────────────────────────────────
        selection_vars = pulp.LpVariable.dicts("Select", result_df.index, cat="Binary")

        # 3. Objective function ────────────────────────────────────────────────
        model = build_objective_function(
            model, selection_vars, result_df, strategy, custom_weights
        )

        # 3b. Force non-schedulable records to 0 ──────────────────────────────
        if "is_spatially_schedulable" in result_df.columns:
            for idx, row in result_df.iterrows():
                if not row["is_spatially_schedulable"]:
                    model += selection_vars[idx] == 0, f"Unreachable_{idx}"

        # 4. Constraints ───────────────────────────────────────────────────────
        model = apply_capacity_constraints(
            model,
            selection_vars,
            result_df,
            max_teams=settings.number_of_teams,
            visits_per_team=settings.maximum_visits_per_team,
        )

        # 5. Solve ─────────────────────────────────────────────────────────────
        logger.info("Solving MIP assignment problem...")
        solver = pulp.PULP_CBC_CMD(msg=False)
        model.solve(solver)
        lp_status = pulp.LpStatus[model.status]

        if lp_status != "Optimal":
            logger.warning("Optimization status: %s", lp_status)

        # 6. Extract selections ────────────────────────────────────────────────
        selected_flags = []
        priorities = []

        for idx, row in result_df.iterrows():
            is_selected = bool(selection_vars[idx].varValue)
            selected_flags.append(is_selected)

            if is_selected:
                priorities.append("PRIMARY_OUTREACH")
            elif not row.get("is_spatially_schedulable", True) and row.get(
                "multi_factor_risk_category"
            ) in ["VERY HIGH", "EXTREME", "HIGH"]:
                priorities.append("MANUAL_REVIEW")
                result_df.at[idx, "fallback_status"] = "MANUAL_REVIEW"
            elif row.get("fallback_status") == "MANUAL_REVIEW":
                priorities.append("NEEDS_REVIEW")
            elif row.get("multi_factor_risk_category") in ["VERY HIGH", "EXTREME", "HIGH"]:
                priorities.append("WAITLIST_HIGH_RISK")
            else:
                priorities.append("NO_ACTION")

        result_df["selected_for_outreach"] = selected_flags
        result_df["outreach_priority"] = priorities
        result_df["optimization_strategy"] = strategy

        # --- Generate Geographic Schedule ---
        scheduler = OutreachScheduler()
        result_df, team_schedules = scheduler.schedule_plan(result_df)

        # --- Operational Constraint Engine Evaluation ---
        ce = ConstraintEngine()
        ce_result = ce.evaluate(result_df, "selected_for_outreach")
        
        if not ce_result["is_feasible"]:
            logger.warning(f"Proposed plan is unfeasible. Reasons: {ce_result['reasons']}. Activating safe fallback.")
            result_df["selected_for_outreach"] = False
            result_df["outreach_priority"] = "NO_ACTION"
            result_df["fallback_status"] = "FAILED"
            lp_status = "Infeasible (Constraint Engine)"
            
        runtime_s = time.time() - t0

        # 7. Compute full per-run metrics ──────────────────────────────────────
        metrics = self._compute_metrics(result_df, strategy, lp_status, runtime_s)
        metrics["constraint_table"] = ce_result["table"]
        metrics["constraint_penalties"] = ce_result["penalties"]
        metrics["is_feasible"] = ce_result["is_feasible"]
        metrics["infeasibility_reasons"] = ce_result["reasons"]
        metrics["team_schedules"] = team_schedules.to_dict(orient="records") if not team_schedules.empty else []

        # 8. Persist run ───────────────────────────────────────────────────────
        weights = get_strategy_weights(strategy)
        if custom_weights:
            weights.update(custom_weights)
        try:
            store = OptimizationRunStore()
            run_id = store.save(
                strategy=strategy,
                objective_weights=weights,
                metrics=metrics,
                dataset_signature=dataset_signature,
                runtime_s=runtime_s,
            )
            result_df["optimization_run_id"] = run_id
            logger.info(
                "Planned outreach for %d neighbourhoods (run_id=%s, strategy=%s, %.2fs).",
                int(sum(selected_flags)), run_id, strategy, runtime_s
            )
        except Exception as exc:
            logger.warning("Could not persist optimization run: %s", exc)
            result_df["optimization_run_id"] = ""

        return result_df

    # ── Metrics ───────────────────────────────────────────────────────────────
    def _compute_metrics(
        self,
        df: pd.DataFrame,
        strategy: str,
        lp_status: str,
        runtime_s: float,
    ) -> Dict[str, Any]:
        """
        Calculate all required per-run metrics from the solved DataFrame.
        """
        is_high = df["multi_factor_risk_category"].isin(
            ["VERY HIGH", "EXTREME", "HIGH"]
        ) if "multi_factor_risk_category" in df.columns else pd.Series(False, index=df.index)

        is_sel = df["selected_for_outreach"] == True

        selected_df = df[is_sel]
        high_risk_df = df[is_high]

        total_records = len(df)
        total_selected = int(is_sel.sum())
        high_risk_count = int(is_high.sum())
        high_risk_reached = int((is_high & is_sel).sum())

        # Risk coverage
        risk_coverage_pct = (
            (high_risk_reached / high_risk_count * 100.0) if high_risk_count > 0 else 0.0
        )

        # Population metrics (use mobile_population as proxy for total population)
        total_pop_col = (
            "population" if "population" in df.columns else "mobile_population"
        )
        total_population_reached = int(selected_df[total_pop_col].fillna(0).sum()) if total_pop_col in df.columns else 0
        mobile_pop_reached = int(
            selected_df["mobile_population"].fillna(0).sum()
        ) if "mobile_population" in df.columns else 0

        # Low-service-access population reached
        low_svc_reached = 0
        if "group_low_service_access" in df.columns:
            low_svc_reached = int((is_sel & (df["group_low_service_access"] == True)).sum())

        # Travel metrics
        travel_dist_total = float(selected_df["healthcare_distance_km"].fillna(0).sum()) if "healthcare_distance_km" in df.columns else 0.0
        travel_dist_avg = float(selected_df["healthcare_distance_km"].fillna(0).mean()) if "healthcare_distance_km" in df.columns and total_selected > 0 else 0.0

        # Estimated travel time (assume 30 km/h average speed in urban area)
        estimated_travel_time_h = travel_dist_total / 30.0

        # Capacity utilization
        max_capacity = settings.number_of_teams * settings.maximum_visits_per_team
        capacity_utilization_pct = (
            (total_selected / max_capacity * 100.0) if max_capacity > 0 else 0.0
        )

        # Fairness gap — difference in selection rates between groups
        fairness_gap = 0.0
        group_selection_rates = {}
        for group_col in ["group_mobile", "group_low_service_access"]:
            if group_col in df.columns:
                g_mask = df[group_col] == True
                g_total = int(g_mask.sum())
                g_sel = int((g_mask & is_sel).sum())
                rate = (g_sel / g_total * 100.0) if g_total > 0 else 0.0
                group_selection_rates[group_col] = rate

        if len(group_selection_rates) == 2:
            rates = list(group_selection_rates.values())
            fairness_gap = abs(rates[0] - rates[1])

        # Objective score — weighted sum of normalised metrics
        weights = get_strategy_weights(strategy)
        max_pop = max(total_population_reached, 1)
        objective_score = (
            weights["alpha"] * (risk_coverage_pct / 100.0)
            + weights["beta"] * min(mobile_pop_reached / max(mobile_pop_reached, 1), 1.0)
            + weights["gamma"] * (low_svc_reached / max(high_risk_count, 1))
            + weights["delta"] * max(0.0, 1.0 - fairness_gap / 100.0)
            - weights["epsilon"] * min(travel_dist_avg / max(travel_dist_total, 1), 1.0)
            - weights["zeta"] * (0.0 if lp_status == "Optimal" else 1.0)
        )

        # Constraint violations (simple check)
        constraint_violations = 0 if lp_status == "Optimal" else 1

        return {
            "strategy":                    strategy,
            "lp_status":                   lp_status,
            "total_records":               total_records,
            "total_selected":              total_selected,
            "high_risk_count":             high_risk_count,
            "high_risk_reached":           high_risk_reached,
            "risk_coverage_pct":           round(risk_coverage_pct, 2),
            "total_population_reached":    total_population_reached,
            "mobile_population_reached":   mobile_pop_reached,
            "low_service_access_reached":  low_svc_reached,
            "travel_distance_total_km":    round(travel_dist_total, 2),
            "travel_distance_avg_km":      round(travel_dist_avg, 2),
            "estimated_travel_time_h":     round(estimated_travel_time_h, 2),
            "num_outreach_events":         total_selected,
            "capacity_utilization_pct":    round(capacity_utilization_pct, 2),
            "fairness_gap_pct":            round(fairness_gap, 2),
            "group_selection_rates":       group_selection_rates,
            "constraint_violations":       constraint_violations,
            "objective_score":             round(objective_score, 6),
            "runtime_s":                   round(runtime_s, 4),
        }
