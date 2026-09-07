import pulp
import pandas as pd
from src.config.settings import settings
from src.utils.logger import get_logger
from src.optimisation.constraints import apply_capacity_constraints
from src.optimisation.objectives import build_objective_function

logger = get_logger("outreach_planner")

class OutreachPlanner:
    """Optimizes the assignment of outreach teams to high-risk neighbourhoods."""
    
    def plan_outreach(self, df: pd.DataFrame, strategy: str = "COVERAGE_FOCUSED") -> pd.DataFrame:
        logger.info(f"Initializing multi-objective optimization planner (Strategy: {strategy})...")
        result_df = df.copy()
        
        # 1. Create Model
        model = pulp.LpProblem("Neighbourhood_Outreach_Assignment", pulp.LpMaximize)
        
        # 2. Decision Variables (Binary: 1 if selected for outreach, 0 if not)
        selection_vars = pulp.LpVariable.dicts("Select", result_df.index, cat='Binary')
        
        # 3. Apply Objective
        model = build_objective_function(model, selection_vars, result_df, strategy)
        
        # 3b. Force non-schedulable records to 0
        if "is_spatially_schedulable" in result_df.columns:
            for idx, row in result_df.iterrows():
                if not row["is_spatially_schedulable"]:
                    model += selection_vars[idx] == 0, f"Unreachable_{idx}"
        
        # 4. Apply Constraints
        model = apply_capacity_constraints(
            model, 
            selection_vars, 
            result_df, 
            max_teams=settings.number_of_teams, 
            visits_per_team=settings.maximum_visits_per_team
        )
        
        # 5. Solve
        logger.info("Solving MIP assignment problem...")
        solver = pulp.PULP_CBC_CMD(msg=False)
        model.solve(solver)
        
        if pulp.LpStatus[model.status] != 'Optimal':
            logger.warning(f"Optimization did not find an optimal solution. Status: {pulp.LpStatus[model.status]}")
            
        # 6. Extract Results
        selected_flags = []
        priorities = []
        
        for idx, row in result_df.iterrows():
            is_selected = bool(selection_vars[idx].varValue)
            selected_flags.append(is_selected)
            
            if is_selected:
                priorities.append("PRIMARY_OUTREACH")
            elif not row.get("is_spatially_schedulable", True) and row.get('multi_factor_risk_category') in ['EXTREME', 'HIGH']:
                priorities.append("MANUAL_REVIEW")
                result_df.at[idx, 'fallback_status'] = 'MANUAL_REVIEW'
            elif row.get('fallback_status') == 'MANUAL_REVIEW':
                priorities.append("NEEDS_REVIEW")
            elif row.get('multi_factor_risk_category') in ['EXTREME', 'HIGH']:
                priorities.append("WAITLIST_HIGH_RISK")
            else:
                priorities.append("NO_ACTION")
                
        result_df['selected_for_outreach'] = selected_flags
        result_df['outreach_priority'] = priorities
        
        logger.info(f"Planned outreach for {sum(selected_flags)} neighbourhoods.")
        return result_df
