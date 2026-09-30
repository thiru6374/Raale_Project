"""
src/evaluation/experiment_store.py

Phase 9: Persistent experiment registry.

Each experiment record captures:
  experiment_id      — UUID
  timestamp          — ISO-8601 UTC
  dataset_signature  — hash of the active dataset
  dataset_rows       — number of rows in the dataset
  dataset_name       — filename or source label
  configuration      — key operational settings snapshot
  strategy           — strategy name
  metrics            — full metrics dict
  validation         — validation metrics (top-risk capture, rank stability, etc.)
  model_version      — risk model version
  optimizer_version  — optimizer version
  runtime_s          — wall-clock seconds
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("experiment_store")

_DEFAULT_STORE_DIR = Path("data/experiments")
MODEL_VERSION     = "2.0.0"
OPTIMIZER_VERSION = "3.1.0"


class ExperimentStore:
    """Persists and retrieves full experiment comparison records."""

    def __init__(self, store_dir: Optional[str] = None):
        self.store_dir = Path(store_dir) if store_dir else _DEFAULT_STORE_DIR
        self.store_dir.mkdir(parents=True, exist_ok=True)

    # ── Write ──────────────────────────────────────────────────────────────────
    def save_experiment(
        self,
        strategy_results: Dict[str, Any],
        dataset_signature: str = "",
        dataset_rows: int = 0,
        dataset_name: str = "",
        configuration: Optional[Dict[str, Any]] = None,
        runtime_s: float = 0.0,
    ) -> str:
        """
        Persist a full multi-strategy experiment run. Returns experiment_id.
        strategy_results: {strategy_key: {"metrics": {...}, "validation": {...}}}
        """
        experiment_id = str(uuid.uuid4())
        record = {
            "experiment_id":     experiment_id,
            "timestamp":         datetime.now(timezone.utc).isoformat(),
            "dataset_signature": dataset_signature,
            "dataset_rows":      dataset_rows,
            "dataset_name":      dataset_name,
            "configuration":     configuration or {},
            "model_version":     MODEL_VERSION,
            "optimizer_version": OPTIMIZER_VERSION,
            "runtime_s":         round(runtime_s, 4),
            "strategies":        strategy_results,
        }

        file_path = self.store_dir / f"{experiment_id}.json"
        try:
            file_path.write_text(json.dumps(record, indent=2, default=str))
            logger.info("Experiment saved: %s", experiment_id)
        except OSError as exc:
            logger.warning("Could not persist experiment: %s", exc)

        return experiment_id

    # ── Read ───────────────────────────────────────────────────────────────────
    def load_all(self) -> List[Dict[str, Any]]:
        """Return all persisted experiment records, newest first."""
        records = []
        for path in sorted(self.store_dir.glob("*.json"), reverse=True):
            try:
                records.append(json.loads(path.read_text()))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not read experiment file %s: %s", path.name, exc)
        return records

    def load(self, experiment_id: str) -> Dict[str, Any]:
        """Load a single experiment record by ID. Returns {} if not found."""
        path = self.store_dir / f"{experiment_id}.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
