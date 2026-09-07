"""
src/security/roles.py

Role definitions for the prototype role-based access model.

PROTOTYPE NOTICE:
This module implements a LOCAL role simulation for development and demonstration
purposes only. It is NOT a production authentication system. There is no user
identity verification, password storage, or session management. Roles are
selected by the user in the UI and enforced at the service layer only.

For real production deployment, integrate with an identity provider such as
OAuth 2.0, LDAP, or a managed authentication service.
"""
from enum import Enum


class Role(str, Enum):
    """Conceptual roles in the system."""
    VIEWER   = "VIEWER"
    OPERATOR = "OPERATOR"
    REVIEWER = "REVIEWER"
    ADMIN    = "ADMIN"


ROLE_DISPLAY = {
    Role.VIEWER:   "👁  Viewer   — Read-only access to dashboard, maps, and recommendations.",
    Role.OPERATOR: "🛠  Operator — Viewer + submit feedback, acknowledge alerts, manual review.",
    Role.REVIEWER: " Reviewer — Operator + review proposals, overrides, and config proposals.",
    Role.ADMIN:    "🔑 Admin    — Reviewer + approve configs, activate versions, execute rollback.",
}

# Ordered hierarchy for inheritance checks
ROLE_HIERARCHY: list[Role] = [Role.VIEWER, Role.OPERATOR, Role.REVIEWER, Role.ADMIN]


def role_rank(role: Role) -> int:
    """Returns the numeric rank of a role (higher = more permissions)."""
    return ROLE_HIERARCHY.index(role)


def has_minimum_role(current_role: Role, required_role: Role) -> bool:
    """Returns True if current_role meets or exceeds required_role."""
    return role_rank(current_role) >= role_rank(required_role)
