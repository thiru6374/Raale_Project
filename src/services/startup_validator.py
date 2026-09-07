"""
src/services/startup_validator.py

Application startup validation.
Checks Python version, required packages, directories, and config availability.
Returns a structured diagnostic report.
"""
import sys
import os
import importlib
from typing import Dict, Any, List

REQUIRED_PACKAGES = [
    "streamlit", "pandas", "numpy", "pydantic", "pulp",
    "plotly", "requests"
]

REQUIRED_DIRS = [
    "data", "data/config", "data/intelligence", "logs", "src",
]

PYTHON_MIN = (3, 10)


def _check_python() -> Dict[str, Any]:
    major, minor = sys.version_info.major, sys.version_info.minor
    ok = (major, minor) >= PYTHON_MIN
    return {
        "check": "Python Version",
        "status": "HEALTHY" if ok else "CRITICAL",
        "detail": f"Python {major}.{minor} detected. Minimum: {PYTHON_MIN[0]}.{PYTHON_MIN[1]}",
    }


def _check_packages() -> List[Dict[str, Any]]:
    results = []
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            results.append({"check": f"Package: {pkg}", "status": "HEALTHY", "detail": "Installed"})
        except ImportError:
            results.append({
                "check": f"Package: {pkg}",
                "status": "CRITICAL",
                "detail": f"Missing. Run: pip install -r requirements.txt",
            })
    return results


def _check_directories() -> List[Dict[str, Any]]:
    results = []
    for d in REQUIRED_DIRS:
        exists  = os.path.exists(d)
        writable = os.access(d, os.W_OK) if exists else False
        if not exists:
            try:
                os.makedirs(d, exist_ok=True)
                exists, writable = True, True
                status = "HEALTHY"
                detail = "Created automatically."
            except Exception as e:
                status = "CRITICAL"
                detail = f"Cannot create: {e}"
        elif not writable:
            status = "WARNING"
            detail = "Directory exists but is not writable."
        else:
            status = "HEALTHY"
            detail = "Exists and writable."
        results.append({"check": f"Directory: {d}", "status": status, "detail": detail})
    return results


def _check_config() -> Dict[str, Any]:
    cfg_path = "data/config/settings_versioned.jsonl"
    if os.path.exists(cfg_path):
        return {"check": "Configuration File", "status": "HEALTHY", "detail": "Found."}
    return {
        "check": "Configuration File",
        "status": "WARNING",
        "detail": "settings_versioned.jsonl not found. Will be created on first run.",
    }


def run_startup_validation() -> Dict[str, Any]:
    """
    Runs all startup checks and returns a structured report.
    """
    checks: List[Dict[str, Any]] = []

    checks.append(_check_python())
    checks.extend(_check_packages())
    checks.extend(_check_directories())
    checks.append(_check_config())

    critical_count = sum(1 for c in checks if c["status"] == "CRITICAL")
    warning_count  = sum(1 for c in checks if c["status"] == "WARNING")

    if critical_count > 0:
        overall = "CRITICAL"
    elif warning_count > 0:
        overall = "WARNING"
    else:
        overall = "HEALTHY"

    return {
        "overall": overall,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "checks": checks,
    }
