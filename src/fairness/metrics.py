import pandas as pd
from typing import Dict

def calculate_coverage_rates(df: pd.DataFrame, group_col: str) -> Dict[str, float]:
    """
    Calculates the selection rate (coverage) for the entire dataset 
    and for the specific fairness group.
    
    Returns a dictionary with 'global_coverage' and 'group_coverage'.
    """
    if 'selected_for_outreach' not in df.columns:
        raise ValueError("DataFrame must contain 'selected_for_outreach' column from the planner.")
        
    if group_col not in df.columns:
        raise ValueError(f"Fairness group column '{group_col}' not found in DataFrame.")

    # Global coverage rate
    global_total = len(df)
    global_selected = df['selected_for_outreach'].sum()
    global_coverage = global_selected / global_total if global_total > 0 else 0.0

    # Group coverage rate
    group_df = df[df[group_col] == True]
    group_total = len(group_df)
    group_selected = group_df['selected_for_outreach'].sum() if group_total > 0 else 0
    group_coverage = group_selected / group_total if group_total > 0 else 0.0
    
    return {
        'global_coverage': global_coverage,
        'group_coverage': group_coverage,
        'group_total': group_total
    }
