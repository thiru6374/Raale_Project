"""
src/governance/dataset_registry.py

Lightweight dataset registration and lineage tracking.
Stores dataset metadata in data/governance/dataset_registry.jsonl.
"""
import os
import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("dataset_registry")

REGISTRY_DIR  = "data/governance"
REGISTRY_FILE = os.path.join(REGISTRY_DIR, "dataset_registry.jsonl")

LINEAGE_STAGES = [
    "raw_ingestion",
    "schema_validation",
    "preprocessing",
    "feature_engineering",
    "risk_assessment",
    "optimization",
    "communication",
    "experiment",
    "evidence",
]


def _ensure_dir():
    os.makedirs(REGISTRY_DIR, exist_ok=True)


def _fingerprint(df: pd.DataFrame) -> str:
    """SHA-256 fingerprint of the DataFrame shape + first/last row hash."""
    try:
        content = str(df.shape) + str(df.iloc[0].to_dict()) + str(df.iloc[-1].to_dict())
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    except Exception:
        return "N/A"


def register_dataset(
    df: pd.DataFrame,
    source_type: str = "synthetic_generated",
    pipeline_version: str = "6.0.0",
    validation_status: str = "PASS",
    notes: str = "",
) -> str:
    """
    Registers a dataset run in the registry.

    Returns: dataset_id (UUID string)
    """
    _ensure_dir()
    dataset_id = str(uuid.uuid4())[:8].upper()
    fingerprint = _fingerprint(df)
    quality_score = round(df.notna().mean().mean() * 100, 1) if not df.empty else 0.0

    record = {
        "dataset_id":         dataset_id,
        "fingerprint":        fingerprint,
        "source_type":        source_type,
        "created_at":         datetime.utcnow().isoformat() + "Z",
        "pipeline_version":   pipeline_version,
        "total_records":      len(df),
        "total_columns":      len(df.columns),
        "validation_status":  validation_status,
        "quality_score_pct":  quality_score,
        "lineage": {
            stage: "PENDING" for stage in LINEAGE_STAGES
        },
        "experiments":        [],
        "notes":              notes,
    }
    record["lineage"]["raw_ingestion"]       = "COMPLETE"
    record["lineage"]["schema_validation"]   = validation_status

    try:
        with open(REGISTRY_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
        logger.info("Dataset registered: ID=%s  fingerprint=%s", dataset_id, fingerprint)
    except Exception as exc:
        logger.error("Failed to write dataset registry: %s", exc)

    return dataset_id


def update_lineage_stage(dataset_id: str, stage: str, status: str = "COMPLETE"):
    """Updates the lineage stage for an existing dataset record (re-writes last entry)."""
    _ensure_dir()
    if not os.path.exists(REGISTRY_FILE):
        return

    records = []
    try:
        with open(REGISTRY_FILE, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except Exception:
        return

    updated = False
    for rec in records:
        if rec.get("dataset_id") == dataset_id:
            rec.setdefault("lineage", {})[stage] = status
            updated = True

    if updated:
        with open(REGISTRY_FILE, "w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")


def get_all_datasets() -> List[Dict[str, Any]]:
    """Returns all registered datasets, newest first."""
    _ensure_dir()
    if not os.path.exists(REGISTRY_FILE):
        return []
    records = []
    try:
        with open(REGISTRY_FILE, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except Exception:
        pass
    return list(reversed(records))


def get_latest_dataset() -> Optional[Dict[str, Any]]:
    """Returns the most recently registered dataset, or None."""
    all_ds = get_all_datasets()
    return all_ds[0] if all_ds else None
