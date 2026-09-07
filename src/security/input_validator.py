"""
src/security/input_validator.py

Centralized backend input validation for all user-supplied values.
UI controls alone are insufficient; validation must exist at the service layer.
"""
import re
from typing import Any, Dict, Optional, Tuple

# --- Patterns ---
_SUSPICIOUS_PATTERNS = [
    re.compile(r'(api[_\-]?key\s*=\s*["\']?\w{8,})', re.IGNORECASE),
    re.compile(r'(password\s*=\s*["\']?\w{4,})', re.IGNORECASE),
    re.compile(r'(secret\s*=\s*["\']?\w{4,})', re.IGNORECASE),
    re.compile(r'(token\s*=\s*["\']?\w{8,})', re.IGNORECASE),
    re.compile(r'(bearer\s+[A-Za-z0-9\-_\.]{20,})', re.IGNORECASE),
]

_MAX_TEXT_LEN = 2000
_MAX_REASON_LEN = 500


def validate_text_input(value: Any, field_name: str, required: bool = True,
                        max_length: int = _MAX_TEXT_LEN) -> Tuple[bool, str]:
    """Validates a free-text input field."""
    if value is None or str(value).strip() == "":
        if required:
            return False, f"'{field_name}' is required and cannot be empty."
        return True, ""
    text = str(value).strip()
    if len(text) > max_length:
        return False, f"'{field_name}' exceeds maximum length of {max_length} characters."
    return True, ""


def validate_override_reason(reason: str) -> Tuple[bool, str]:
    """Validates a human override reason."""
    ok, msg = validate_text_input(reason, "override_reason", required=True, max_length=_MAX_REASON_LEN)
    if not ok:
        return False, msg
    if len(reason.strip()) < 10:
        return False, "Override reason must be at least 10 characters."
    return True, ""


def validate_feedback_record(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validates a feedback record."""
    valid_ratings = {"Yes", "Partially", "No"}
    for field in ("usefulness_rating", "clarity_rating", "feasibility_rating"):
        val = data.get(field)
        if val is not None and val not in valid_ratings:
            return False, f"'{field}' must be one of {valid_ratings}, got '{val}'."
    comment = data.get("comment", "")
    if comment and len(str(comment)) > _MAX_TEXT_LEN:
        return False, f"'comment' exceeds maximum length of {_MAX_TEXT_LEN}."
    return True, ""


def validate_configuration(config: Dict[str, Any]) -> Tuple[bool, str]:
    """Validates a proposed configuration dictionary."""
    teams = config.get("number_of_teams")
    if teams is not None:
        if not isinstance(teams, int) or teams < 1 or teams > 500:
            return False, "number_of_teams must be an integer between 1 and 500."

    visits = config.get("maximum_visits_per_team")
    if visits is not None:
        if not isinstance(visits, int) or visits < 1 or visits > 200:
            return False, "maximum_visits_per_team must be an integer between 1 and 200."

    gap = config.get("maximum_coverage_gap")
    if gap is not None:
        if not isinstance(gap, (int, float)) or gap < 0.0 or gap > 1.0:
            return False, "maximum_coverage_gap must be a float between 0.0 and 1.0."

    return True, ""


def validate_alert_action(action: str) -> Tuple[bool, str]:
    """Validates an alert lifecycle action string."""
    valid_actions = {"ACKNOWLEDGE", "RESOLVE", "DISMISS", "UNDER_REVIEW"}
    if action.upper() not in valid_actions:
        return False, f"Alert action must be one of {valid_actions}."
    return True, ""


def detect_secrets_in_text(text: str) -> Tuple[bool, str]:
    """
    Lightweight check for accidental secret patterns in text.
    Returns (True, warning_message) if suspicious pattern found.
    Does NOT print the secret value in the warning.
    """
    for pattern in _SUSPICIOUS_PATTERNS:
        if pattern.search(text):
            return True, (
                "A potentially sensitive pattern was detected in the input. "
                "Do not include API keys, passwords, tokens, or secrets in text fields. "
                "The value has not been stored."
            )
    return False, ""
