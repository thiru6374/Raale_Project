"""
src/services/config_version_service.py
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from src.services.persistence.config_repository import ConfigRepository
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("config_version_service")

class ConfigVersionService:
    def __init__(self):
        self.repo = ConfigRepository()
        self._ensure_initial_config()
        
    def _ensure_initial_config(self):
        latest = self.repo.get_latest_approved_version()
        if not latest:
            logger.info("Initializing baseline configuration version.")
            initial_config = {
                "config_version": "v1_baseline",
                "parent_version": None,
                "change_reason": "System Initialization",
                "change_source": "SYSTEM",
                "approval_status": "APPROVED",
                "configuration": settings.model_dump(),
                "validation_status": "VALID",
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            self.repo.save_version(initial_config)
            self.repo.log_audit_event("CONFIG_CREATED", "v1_baseline", reason="Initial configuration")
            
    def get_active_config(self) -> Dict[str, Any]:
        """Returns the current active configuration."""
        latest = self.repo.get_latest_approved_version()
        if latest and "configuration" in latest:
            return latest["configuration"]
        return settings.model_dump()
        
    def apply_active_config_to_settings(self):
        """Overrides the memory `settings` with the active configuration."""
        active = self.get_active_config()
        for k, v in active.items():
            if hasattr(settings, k):
                setattr(settings, k, v)
                
    def propose_configuration(self, new_config: Dict[str, Any], reason: str, actor: str = "SYSTEM") -> str:
        latest = self.repo.get_latest_approved_version()
        parent_version = latest["config_version"] if latest else None
        
        proposal = {
            "config_version": f"v_{uuid.uuid4().hex[:8]}",
            "parent_version": parent_version,
            "change_reason": reason,
            "change_source": actor,
            "approval_status": "PROPOSED",
            "configuration": new_config,
            "validation_status": "PENDING",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        self.repo.save_version(proposal)
        self.repo.log_audit_event("CONFIG_PROPOSED", proposal["config_version"], actor=actor, reason=reason)
        return proposal["config_version"]
        
    def approve_and_activate(self, config_version: str, actor: str = "ADMIN") -> bool:
        proposal = self.repo.get_version(config_version)
        if not proposal:
            return False
            
        # Validate first
        if not self._validate_config(proposal["configuration"]):
            proposal["validation_status"] = "INVALID"
            proposal["approval_status"] = "REJECTED"
            self.repo.save_version(proposal) # Append updated state
            self.repo.log_audit_event("CONFIG_REJECTED", config_version, actor=actor, reason="Validation Failed")
            return False
            
        # Approve and activate
        proposal["validation_status"] = "VALID"
        proposal["approval_status"] = "APPROVED"
        proposal["approved_at"] = datetime.utcnow().isoformat() + "Z"
        proposal["approved_by"] = actor
        
        # Save as new record reflecting approval
        self.repo.save_version(proposal)
        self.repo.log_audit_event("CONFIG_APPROVED", config_version, actor=actor, previous_version=proposal.get("parent_version"))
        self.repo.log_audit_event("CONFIG_ACTIVATED", config_version, actor=actor)
        
        # Apply to memory
        self.apply_active_config_to_settings()
        return True
        
    def reject_configuration(self, config_version: str, actor: str = "ADMIN", reason: str = "") -> bool:
        proposal = self.repo.get_version(config_version)
        if not proposal:
            return False
            
        proposal["approval_status"] = "REJECTED"
        self.repo.save_version(proposal)
        self.repo.log_audit_event("CONFIG_REJECTED", config_version, actor=actor, reason=reason)
        return True
        
    def rollback_to_version(self, config_version: str, actor: str = "ADMIN", reason: str = "Manual Rollback") -> bool:
        target = self.repo.get_version(config_version)
        if not target or target.get("validation_status") != "VALID":
            return False
            
        latest = self.repo.get_latest_approved_version()
        prev_version = latest["config_version"] if latest else None
        
        # Rollback is fundamentally proposing and auto-approving a clone of the target
        rollback_proposal = {
            "config_version": f"v_{uuid.uuid4().hex[:8]}",
            "parent_version": prev_version,
            "rollback_reference": config_version,
            "change_reason": reason,
            "change_source": actor,
            "approval_status": "APPROVED",
            "configuration": target["configuration"],
            "validation_status": "VALID",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "approved_at": datetime.utcnow().isoformat() + "Z",
            "approved_by": actor
        }
        
        self.repo.save_version(rollback_proposal)
        self.repo.log_audit_event("CONFIG_ROLLED_BACK", rollback_proposal["config_version"], actor=actor, reason=reason, previous_version=prev_version, new_version=config_version)
        self.apply_active_config_to_settings()
        return True
        
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Basic validation to ensure safety limits are not breached."""
        if config.get("number_of_teams", 0) < 1:
            return False
        if config.get("maximum_visits_per_team", 0) < 1:
            return False
        if config.get("maximum_coverage_gap", 1.0) < 0.0 or config.get("maximum_coverage_gap", 1.0) > 1.0:
            return False
        return True
