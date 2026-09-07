"""
src/governance/improvement_candidates.py

Records structured improvement candidates generated from stakeholder feedback,
fairness warnings, failure analysis, and experiment results.

Candidates are NEVER automatically applied — they must be manually approved.
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.utils.logger import get_logger

logger = get_logger("improvement_candidates")

CANDIDATES_DIR  = "data/governance"
CANDIDATES_FILE = os.path.join(CANDIDATES_DIR, "improvement_candidates.jsonl")

VALID_STATUSES = {"PROPOSED", "TESTING", "APPROVED", "REJECTED", "IMPLEMENTED"}


def _ensure_dir():
    os.makedirs(CANDIDATES_DIR, exist_ok=True)


def create_improvement_candidate(
    source: str,
    problem_description: str,
    affected_component: str,
    proposed_improvement: str,
    expected_benefit: str,
    risk: str = "LOW",
) -> str:
    """
    Creates and persists a new improvement candidate.

    Parameters:
        source              : "stakeholder_feedback" | "fairness_warning" |
                              "failure_analysis" | "data_quality" | "experiment_result"
        problem_description : Plain-language description of the issue
        affected_component  : e.g. "optimization", "data_ingestion", "fairness_auditor"
        proposed_improvement: Concrete suggested change
        expected_benefit    : e.g. "Increase high-risk coverage by ~15%"
        risk                : "LOW" | "MEDIUM" | "HIGH"

    Returns: improvement_id
    """
    _ensure_dir()
    improvement_id = "IMP-" + str(uuid.uuid4())[:6].upper()

    record = {
        "improvement_id":       improvement_id,
        "timestamp":            datetime.utcnow().isoformat() + "Z",
        "source":               source,
        "problem_description":  problem_description,
        "affected_component":   affected_component,
        "proposed_improvement": proposed_improvement,
        "expected_benefit":     expected_benefit,
        "risk":                 risk,
        "status":               "PROPOSED",
        "status_history":       [{"status": "PROPOSED", "at": datetime.utcnow().isoformat() + "Z"}],
    }

    try:
        with open(CANDIDATES_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.info("Improvement candidate created: %s", improvement_id)
    except Exception as exc:
        logger.error("Failed to write improvement candidate: %s", exc)

    return improvement_id


def update_candidate_status(improvement_id: str, new_status: str, notes: str = ""):
    """Updates the status of an existing improvement candidate."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of {VALID_STATUSES}")

    _ensure_dir()
    if not os.path.exists(CANDIDATES_FILE):
        logger.warning("Candidates file not found — cannot update %s", improvement_id)
        return

    records = []
    with open(CANDIDATES_FILE) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    for rec in records:
        if rec.get("improvement_id") == improvement_id:
            rec["status"] = new_status
            rec.setdefault("status_history", []).append(
                {"status": new_status, "at": datetime.utcnow().isoformat() + "Z", "notes": notes}
            )

    with open(CANDIDATES_FILE, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    logger.info("Improvement %s status → %s", improvement_id, new_status)


def get_all_candidates() -> List[Dict[str, Any]]:
    """Returns all improvement candidates, newest first."""
    _ensure_dir()
    if not os.path.exists(CANDIDATES_FILE):
        return []
    records = []
    try:
        with open(CANDIDATES_FILE) as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except Exception:
        pass
    return list(reversed(records))


def get_open_candidates() -> List[Dict[str, Any]]:
    """Returns only PROPOSED candidates."""
    return [c for c in get_all_candidates() if c.get("status") == "PROPOSED"]


def generate_candidates_from_feedback(
    feedback_records: List[Dict[str, Any]],
    trust_threshold: float = 3.0,
) -> List[str]:
    """
    Inspects stakeholder feedback and auto-creates improvement candidates
    when average scores fall below the trust_threshold.

    Returns list of created improvement_ids.
    """
    if not feedback_records:
        return []

    import pandas as pd
    df = pd.DataFrame(feedback_records)
    created_ids = []

    score_map = {
        "recommendation_trust":      ("optimization", "Improve recommendation trust through data quality enhancements"),
        "prioritization_clarity":    ("communication", "Improve clarity of risk prioritization communication"),
        "recommendation_usefulness": ("outreach_planner", "Refine outreach recommendations based on planner feedback"),
        "fairness_understanding":    ("fairness_auditor", "Improve fairness explanation in outreach communications"),
    }

    for col, (component, improvement) in score_map.items():
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if not series.empty and series.mean() < trust_threshold:
                imp_id = create_improvement_candidate(
                    source="stakeholder_feedback",
                    problem_description=(
                        f"Stakeholder avg score for '{col}' is {series.mean():.1f}/5 "
                        f"(below threshold of {trust_threshold})."
                    ),
                    affected_component=component,
                    proposed_improvement=improvement,
                    expected_benefit=f"Increase '{col}' score above {trust_threshold}/5",
                    risk="LOW",
                )
                created_ids.append(imp_id)

    return created_ids
