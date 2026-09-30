"""
src/optimisation/run_store.py

Persists every optimization run as a JSON record so runs are reproducible,
auditable and comparable.

Each record contains:
  run_id           – UUID
  timestamp        – ISO-8601 UTC
  dataset_signature – hash of the active dataset (from session state / provider)
  strategy         – strategy name
  objective_weights – {alpha, beta, gamma, delta, epsilon, zeta}
  metrics          – full metrics dict (risk_coverage, population reached, etc.)
  runtime_s        – wall-clock seconds
"""
import json
import uuid
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("optimization_run_store")

_DEFAULT_STORE_DIR = Path("data/optimization_runs")


class OptimizationRunStore:
    """Persists and retrieves optimization run records."""

    def __init__(self, store_dir: str = None):
        self.store_dir = Path(store_dir) if store_dir else _DEFAULT_STORE_DIR
        self.store_dir.mkdir(parents=True, exist_ok=True)

    # ── Write ──────────────────────────────────────────────────────────────────
    def save(
        self,
        strategy: str,
        objective_weights: Dict[str, float],
        metrics: Dict[str, Any],
        dataset_signature: str = "",
        runtime_s: float = 0.0,
    ) -> str:
        """
        Persist an optimization run. Returns the run_id.
        """
        run_id = str(uuid.uuid4())
        record = {
            "run_id":             run_id,
            "timestamp":          datetime.now(timezone.utc).isoformat(),
            "dataset_signature":  dataset_signature,
            "strategy":           strategy,
            "objective_weights":  objective_weights,
            "metrics":            metrics,
            "runtime_s":          round(runtime_s, 4),
        }

        file_path = self.store_dir / f"{run_id}.json"
        try:
            file_path.write_text(json.dumps(record, indent=2, default=str))
            logger.info("Optimization run saved: %s (%s)", run_id, strategy)
        except OSError as exc:
            logger.warning("Could not persist optimization run: %s", exc)

        return run_id

    # ── Read ───────────────────────────────────────────────────────────────────
    def load_all(self) -> List[Dict[str, Any]]:
        """Return all persisted run records, newest first."""
        records = []
        for path in sorted(self.store_dir.glob("*.json"), reverse=True):
            try:
                records.append(json.loads(path.read_text()))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not read run file %s: %s", path.name, exc)
        return records

    def load(self, run_id: str) -> Dict[str, Any]:
        """Load a single run record by ID. Returns {} if not found."""
        path = self.store_dir / f"{run_id}.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    # Alias for convenience
    def get(self, run_id: str) -> Dict[str, Any]:
        """Alias for load()."""
        return self.load(run_id)
