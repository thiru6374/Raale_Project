"""
src/security/permissions.py

Centralized permission matrix.
"""
from src.security.roles import Role

# --- Permission constants ---
PERM_VIEW_DASHBOARD           = "view_dashboard"
PERM_VIEW_RISK_MAP            = "view_risk_map"
PERM_VIEW_RECOMMENDATIONS     = "view_recommendations"
PERM_VIEW_ALERTS              = "view_alerts"
PERM_VIEW_EXPLANATIONS        = "view_explanations"
PERM_SUBMIT_FEEDBACK          = "submit_feedback"
PERM_ACKNOWLEDGE_ALERT        = "acknowledge_alert"
PERM_SUBMIT_MANUAL_REVIEW     = "submit_manual_review"
PERM_REVIEW_PROPOSALS         = "review_proposals"
PERM_REVIEW_OVERRIDES         = "review_overrides"
PERM_REVIEW_CONFIG            = "review_config"
PERM_APPROVE_CONFIG           = "approve_config"
PERM_ACTIVATE_CONFIG          = "activate_config"
PERM_ROLLBACK_CONFIG          = "rollback_config"
PERM_APPROVE_OVERRIDE         = "approve_override"
PERM_DISMISS_CRITICAL_ALERT   = "dismiss_critical_alert"
PERM_RESTORE_BACKUP           = "restore_backup"
PERM_CREATE_BACKUP            = "create_backup"
PERM_OVERRIDE_DECISION        = "override_decision"

# Permission matrix: role → set of permissions
PERMISSION_MATRIX: dict[Role, set[str]] = {
    Role.VIEWER: {
        PERM_VIEW_DASHBOARD,
        PERM_VIEW_RISK_MAP,
        PERM_VIEW_RECOMMENDATIONS,
        PERM_VIEW_ALERTS,
        PERM_VIEW_EXPLANATIONS,
    },
    Role.OPERATOR: {
        PERM_VIEW_DASHBOARD,
        PERM_VIEW_RISK_MAP,
        PERM_VIEW_RECOMMENDATIONS,
        PERM_VIEW_ALERTS,
        PERM_VIEW_EXPLANATIONS,
        PERM_SUBMIT_FEEDBACK,
        PERM_ACKNOWLEDGE_ALERT,
        PERM_SUBMIT_MANUAL_REVIEW,
        PERM_CREATE_BACKUP,
    },
    Role.REVIEWER: {
        PERM_VIEW_DASHBOARD,
        PERM_VIEW_RISK_MAP,
        PERM_VIEW_RECOMMENDATIONS,
        PERM_VIEW_ALERTS,
        PERM_VIEW_EXPLANATIONS,
        PERM_SUBMIT_FEEDBACK,
        PERM_ACKNOWLEDGE_ALERT,
        PERM_SUBMIT_MANUAL_REVIEW,
        PERM_CREATE_BACKUP,
        PERM_REVIEW_PROPOSALS,
        PERM_REVIEW_OVERRIDES,
        PERM_REVIEW_CONFIG,
    },
    Role.ADMIN: {
        PERM_VIEW_DASHBOARD,
        PERM_VIEW_RISK_MAP,
        PERM_VIEW_RECOMMENDATIONS,
        PERM_VIEW_ALERTS,
        PERM_VIEW_EXPLANATIONS,
        PERM_SUBMIT_FEEDBACK,
        PERM_ACKNOWLEDGE_ALERT,
        PERM_SUBMIT_MANUAL_REVIEW,
        PERM_CREATE_BACKUP,
        PERM_REVIEW_PROPOSALS,
        PERM_REVIEW_OVERRIDES,
        PERM_REVIEW_CONFIG,
        PERM_APPROVE_CONFIG,
        PERM_ACTIVATE_CONFIG,
        PERM_ROLLBACK_CONFIG,
        PERM_APPROVE_OVERRIDE,
        PERM_OVERRIDE_DECISION,
        PERM_DISMISS_CRITICAL_ALERT,
        PERM_RESTORE_BACKUP,
    },
}


def get_permissions(role: Role) -> set[str]:
    """Returns the permission set for a given role."""
    return PERMISSION_MATRIX.get(role, set())


def has_permission(role: Role, permission: str) -> bool:
    """Checks if a role has a specific permission."""
    return permission in get_permissions(role)
