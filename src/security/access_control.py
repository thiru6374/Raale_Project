"""
src/security/access_control.py

Centralized access control: checks permissions, logs denials.
"""
import uuid
from datetime import datetime
from typing import Optional
from src.security.roles import Role
from src.security.permissions import has_permission
from src.utils.logger import get_logger

logger = get_logger("access_control")

# Lazy-import to avoid circular deps; security audit written here
_security_store = None

def _get_security_store():
    global _security_store
    if _security_store is None:
        from src.services.persistence.jsonl_store import JSONLStore
        _security_store = JSONLStore("data/intelligence/security_audit.jsonl")
    return _security_store


def _log_security_event(
    event_type: str,
    actor_role: str,
    action: str,
    resource: str,
    result: str,
    reason: str = "",
    pipeline_run_id: Optional[str] = None,
    config_version: Optional[str] = None,
):
    store = _get_security_store()
    record = {
        "event_id":        str(uuid.uuid4()),
        "timestamp":       datetime.utcnow().isoformat() + "Z",
        "event_type":      event_type,
        "actor_role":      actor_role,
        "action":          action,
        "resource":        resource,
        "result":          result,
        "reason":          reason,
        "pipeline_run_id": pipeline_run_id,
        "config_version":  config_version,
    }
    store.append(record)


class AccessControl:
    """
    Centralized access control guard.

    Usage:
        ok, reason = AccessControl.require(role, PERM_APPROVE_CONFIG)
        if not ok:
            st.error(reason)
            return
    """

    @staticmethod
    def require(
        role: Role,
        permission: str,
        action: str = "",
        resource: str = "",
        pipeline_run_id: Optional[str] = None,
        config_version: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Checks if `role` has `permission`.
        Returns (True, "") on success.
        Returns (False, user-safe denial message) on failure,
        and logs an ACCESS_DENIED event.
        """
        granted = has_permission(role, permission)

        if granted:
            _log_security_event(
                event_type="ACCESS_GRANTED",
                actor_role=role,
                action=action or permission,
                resource=resource,
                result="GRANTED",
                pipeline_run_id=pipeline_run_id,
                config_version=config_version,
            )
            return True, ""
        else:
            msg = (
                f"Action not permitted for role {role}. "
                f"Required permission: {permission}. "
                "Contact an authorised administrator."
            )
            logger.warning(
                "ACCESS_DENIED | role=%s | permission=%s | action=%s | resource=%s",
                role, permission, action, resource,
            )
            _log_security_event(
                event_type="ACCESS_DENIED",
                actor_role=role,
                action=action or permission,
                resource=resource,
                result="DENIED",
                reason=f"Role {role} lacks {permission}",
                pipeline_run_id=pipeline_run_id,
                config_version=config_version,
            )
            return False, msg

    @staticmethod
    def log_action(
        event_type: str,
        role: Role,
        action: str,
        resource: str = "",
        result: str = "OK",
        reason: str = "",
        config_version: Optional[str] = None,
    ):
        """Logs a completed security-relevant action."""
        _log_security_event(
            event_type=event_type,
            actor_role=role,
            action=action,
            resource=resource,
            result=result,
            reason=reason,
            config_version=config_version,
        )

    @staticmethod
    def get_recent_events(limit: int = 50):
        store = _get_security_store()
        events = store.read_all()
        return events[-limit:]

    @staticmethod
    def get_denial_count() -> int:
        events = AccessControl.get_recent_events(500)
        return sum(1 for e in events if e.get("event_type") == "ACCESS_DENIED")
