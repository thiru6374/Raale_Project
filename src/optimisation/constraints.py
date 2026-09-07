import pulp
import pandas as pd

def apply_capacity_constraints(model: pulp.LpProblem, selection_vars: dict, df: pd.DataFrame, max_teams: int, visits_per_team: int):
    """
    Applies operational capacity constraints to the PuLP model.
    """
    # Constraint 1: Total selected neighbourhoods cannot exceed total operational capacity
    total_capacity = max_teams * visits_per_team
    model += pulp.lpSum(selection_vars.values()) <= total_capacity, "Max_Total_Capacity"
    
    # Constraint 2: Cannot select neighbourhoods with MANUAL_REVIEW or FAILED status
    # This prevents the system from blindly dispatching teams based on guessed/low-confidence data
    if 'fallback_status' in df.columns:
        for idx, row in df.iterrows():
            if row['fallback_status'] in ['MANUAL_REVIEW', 'FAILED']:
                model += selection_vars[idx] == 0, f"Fallback_Block_{idx}"

    return model
