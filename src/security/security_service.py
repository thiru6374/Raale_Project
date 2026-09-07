"""
src/security/security_service.py

Prototype session management and security orchestration.

PROTOTYPE NOTICE:
Uses Streamlit session state to hold the current role. This is a LOCAL
simulation only. No passwords, tokens, or identity verification exist.
"""
from __future__ import annotations
from typing import Optional
from src.security.roles import Role, ROLE_DISPLAY
from src.security.access_control import AccessControl


# Key used in st.session_state
SESSION_ROLE_KEY = "ph11_current_role"
DEFAULT_ROLE = Role.VIEWER


class SecurityService:
    """
    Manages the prototype role session and provides convenience helpers.
    Import this in Streamlit pages instead of accessing session_state directly.
    """

    @staticmethod
    def get_current_role() -> Role:
        """Returns the currently active role from session state."""
        import streamlit as st
        raw = st.session_state.get(SESSION_ROLE_KEY, DEFAULT_ROLE)
        try:
            return Role(raw)
        except ValueError:
            return DEFAULT_ROLE

    @staticmethod
    def set_role(role: Role):
        """Sets the active role in session state."""
        import streamlit as st
        st.session_state[SESSION_ROLE_KEY] = role

    @staticmethod
    def render_role_selector(sidebar: bool = True):
        """
        Renders the role selector widget.
        Call this once in each page that needs role awareness.
        """
        import streamlit as st
        target = st.sidebar if sidebar else st
        current = SecurityService.get_current_role()
        labels = [r.value for r in Role]
        idx = labels.index(current.value)
        selected = target.selectbox(
            "🔑 Active Role (Prototype)",
            options=labels,
            index=idx,
            key="ph11_role_selector",
            help="PROTOTYPE: Role simulation only. Not a production authentication system.",
        )
        SecurityService.set_role(Role(selected))
        target.caption(ROLE_DISPLAY[Role(selected)])
        return Role(selected)

    @staticmethod
    def access_denied_message(reason: str):
        """Renders a safe access-denied message in the Streamlit UI."""
        import streamlit as st
        st.error(f"🚫 **Access Denied** — {reason}")

    @staticmethod
    def get_recent_security_events(limit: int = 20):
        return AccessControl.get_recent_events(limit)

    @staticmethod
    def get_denial_count() -> int:
        return AccessControl.get_denial_count()
