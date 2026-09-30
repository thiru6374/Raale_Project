import pandas as pd
import uuid
from datetime import datetime
from src.utils.logger import get_logger
from src.governance.audit_logger import AuditLogger
from src.security.access_control import AccessControl
from src.security.permissions import PERM_OVERRIDE_DECISION

logger = get_logger("override_manager")

class OverrideManager:
    """Handles manual interventions to the automated outreach plan securely."""
    
    def __init__(self, audit_logger: AuditLogger):
        self.audit = audit_logger
        
    def apply_override(self, 
                       df: pd.DataFrame, 
                       neighbourhood_id: str, 
                       force_select: bool, 
                       actor: str, 
                       role: str,
                       reason: str, 
                       comment: str,
                       analysis_id: str = "UNKNOWN_ANALYSIS") -> pd.DataFrame:
        """
        Forces a neighbourhood to be selected (or deselected) for outreach, 
        preserves original decision, performs authorization, and audits the event.
        """
        result_df = df.copy()
        
        # 1. Input Validation
        if not reason or len(reason.strip()) < 5:
            raise ValueError("A valid reason (min 5 chars) is required for override.")
            
        if neighbourhood_id not in result_df['neighbourhood_id'].values:
            logger.error(f"Cannot override: Neighbourhood {neighbourhood_id} not found.")
            raise ValueError(f"Neighbourhood {neighbourhood_id} not found.")
            
        # 2. Authorization Check — requires PERM_OVERRIDE_DECISION (ADMIN only)
        is_authorized, auth_msg = AccessControl.require(
            role, PERM_OVERRIDE_DECISION, action="override", resource=neighbourhood_id
        )
        auth_status = "AUTHORIZED" if is_authorized else "DENIED"
        
        if not is_authorized:
            self._log_audit_event(
                neighbourhood_id, None, force_select, actor, role, 
                reason, comment, auth_status, analysis_id, 1.0, result_df
            )
            raise PermissionError(f"Unauthorized override attempt by {actor} ({role}): {auth_msg}")
            
        # 3. Preserve Original Decision
        if 'original_selected_for_outreach' not in result_df.columns:
            result_df['original_selected_for_outreach'] = result_df['selected_for_outreach']
            
        idx = result_df[result_df['neighbourhood_id'] == neighbourhood_id].index[0]
        original_decision = bool(result_df.at[idx, 'original_selected_for_outreach'])
        confidence = float(result_df.at[idx, 'confidence_score']) if 'confidence_score' in result_df.columns else 1.0
        
        # 4. Write to secure audit log first
        self._log_audit_event(
            neighbourhood_id, original_decision, force_select, actor, role, 
            reason, comment, auth_status, analysis_id, confidence, result_df
        )
        
        # 5. Apply the override to Final Decision
        result_df.at[idx, 'selected_for_outreach'] = force_select
        result_df.at[idx, 'override_status'] = "MANUAL_OVERRIDE"
        result_df.at[idx, 'outreach_priority'] = "HUMAN_MANDATED" if force_select else "HUMAN_REJECTED"
        
        logger.info(f"Successfully applied override to {neighbourhood_id}.")
        return result_df
        
    def _log_audit_event(self, n_id, orig, new_dec, actor, role, reason, comment, auth_status, analysis_id, conf, df):
        event_id = str(uuid.uuid4())
        self.audit.log_override_event(
            event_id=event_id,
            analysis_id=analysis_id,
            neighbourhood_id=n_id,
            original_decision=orig,
            new_decision=new_dec,
            actor=actor,
            role=role,
            reason=reason,
            comment=comment,
            auth_status=auth_status,
            system_confidence=conf
        )
