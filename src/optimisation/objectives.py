import pulp
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("outreach_objectives")

def build_objective_function(
    model: pulp.LpProblem, 
    selection_vars: dict, 
    df: pd.DataFrame,
    strategy: str = "COVERAGE_FOCUSED"
):
    """
    Builds the objective function to maximize total risk mitigated and optionally
    balance fairness across groups.
    
    Supported Strategies:
    - COVERAGE_FOCUSED: Maximizes risk reduction (high_risk * population).
    - BALANCED: Mix of risk reduction and providing equity to underserved groups.
    - FAIRNESS_AWARE: Heavily prioritizes equity to vulnerable/low-access groups.
    """
    # Strategy weight assignments
    if strategy == "COVERAGE_FOCUSED":
        coverage_weight = 1.0
        fairness_weight = 0.05
    elif strategy == "BALANCED":
        coverage_weight = 0.6
        fairness_weight = 0.4
    elif strategy == "FAIRNESS_AWARE":
        coverage_weight = 0.3
        fairness_weight = 0.7
    else:
        logger.warning(f"Unknown strategy '{strategy}'. Defaulting to COVERAGE_FOCUSED.")
        coverage_weight = 1.0
        fairness_weight = 0.05

    objective_terms = []
    
    for idx, row in df.iterrows():
        # Coverage component
        population = row.get('mobile_population', 1.0)
        if pd.isna(population): population = 1.0
        
        risk_score = row.get('multi_factor_risk_score', 0.0)
        if pd.isna(risk_score): risk_score = 0.0
        
        coverage_impact = risk_score * population
        
        # Fairness component (bonus for selecting vulnerable/low service groups)
        # Note: the dataset uses booleans for groups (e.g., group_low_service_access)
        fairness_bonus = 0.0
        if row.get('group_low_service_access') == True:
            fairness_bonus += 1.0
        if row.get('group_mobile') == True:
            fairness_bonus += 0.5
            
        # Scale fairness bonus so it's somewhat comparable to coverage impact
        # We multiply by population so the units are roughly in the same magnitude
        fairness_impact = fairness_bonus * population * risk_score
        
        total_impact = (coverage_impact * coverage_weight) + (fairness_impact * fairness_weight)
        
        objective_terms.append(total_impact * selection_vars[idx])
        
    model += pulp.lpSum(objective_terms), f"Maximize_Risk_and_Fairness_{strategy}"
    
    return model
