import pandas as pd
from src.utils.logger import get_logger
from src.governance.audit_logger import AuditLogger

logger = get_logger("override_manager")

class OverrideManager:
    """Handles manual interventions to the automated outreach plan."""
    
    def __init__(self, audit_logger: AuditLogger):
        self.audit = audit_logger
        
    def force_selection(self, df: pd.DataFrame, neighbourhood_id: str, force_select: bool, user_id: str, reason: str) -> pd.DataFrame:
        """
        Forces a neighbourhood to be selected (or deselected) for outreach, 
        regardless of the optimizer's original output.
        """
        result_df = df.copy()
        
        # Check if neighbourhood exists
        if neighbourhood_id not in result_df['neighbourhood_id'].values:
            logger.error(f"Cannot override: Neighbourhood {neighbourhood_id} not found.")
            raise ValueError(f"Neighbourhood {neighbourhood_id} not found.")
            
        # Get index
        idx = result_df[result_df['neighbourhood_id'] == neighbourhood_id].index[0]
        original_decision = result_df.at[idx, 'selected_for_outreach']
        
        if original_decision == force_select:
            logger.info(f"Neighbourhood {neighbourhood_id} is already in the requested state ({force_select}). No action taken.")
            return result_df
            
        # Write to secure audit log first
        self.audit.log_override(
            user_id=user_id,
            neighbourhood_id=neighbourhood_id,
            original_decision=bool(original_decision),
            new_decision=force_select,
            reason=reason
        )
        
        # Apply the override
        result_df.at[idx, 'selected_for_outreach'] = force_select
        
        # Ensure column exists
        if 'override_status' not in result_df.columns:
            result_df['override_status'] = "AUTOMATED"
            
        result_df.at[idx, 'override_status'] = "MANUAL_OVERRIDE"
        result_df.at[idx, 'outreach_priority'] = "HUMAN_MANDATED" if force_select else "HUMAN_REJECTED"
        
        logger.info(f"Successfully applied override to {neighbourhood_id}.")
        return result_df
