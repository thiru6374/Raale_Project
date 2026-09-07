"""
src/risk/baseline_contracts.py

Pydantic data contracts for the Temperature-Only Baseline Prioritisation Model.

These contracts define:
  - BaselineRecordResult  : per-neighbourhood output row
  - BaselineMetadata      : run-level provenance (version, config, counts)
  - BaselineSummary       : human + machine readable summary
  - BaselineRunResult     : top-level container returned by the model

All contracts use stable field names so , 6, 7, 8, 12 can join / consume
them without requiring changes to the baseline module.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────
#  Enums
# ─────────────────────────────────────────────────────────────

class BaselineRecordStatus(str, Enum):
    RANKED            = "RANKED"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
    EXCLUDED          = "EXCLUDED"
    FAILED            = "FAILED"


class BaselinePriority(str, Enum):
    HIGH              = "HIGH"
    MEDIUM            = "MEDIUM"
    LOW               = "LOW"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"


class BaselineRunStatus(str, Enum):
    COMPLETED             = "COMPLETED"
    COMPLETED_WITH_WARNING = "COMPLETED_WITH_WARNING"
    FAILED                = "FAILED"


# ─────────────────────────────────────────────────────────────
#  Per-neighbourhood row contract
# ─────────────────────────────────────────────────────────────

class BaselineRecordResult(BaseModel):
    """Single neighbourhood result row — written to baseline_results.csv."""

    neighbourhood_id: str
    neighbourhood_name: Optional[str] = None

    # Temperature
    baseline_temperature_feature: str           # e.g. "latest_temperature_c"
    baseline_temperature_value: Optional[float] = None  # NaN preserved as None
    baseline_score: Optional[float] = None      # == baseline_temperature_value (explicit transparency)

    # Ranking
    baseline_rank: Optional[int] = None         # 1 = hottest; None if DATA_INSUFFICIENT
    baseline_priority: BaselinePriority = BaselinePriority.DATA_INSUFFICIENT
    baseline_selected: bool = False             # True if chosen for priority outreach

    # Status
    baseline_status: BaselineRecordStatus = BaselineRecordStatus.RANKED
    status_reason: Optional[str] = None        # Human-readable reason (e.g. "temperature missing")

    # Provenance (stamped per row for easy CSV joins)
    run_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    baseline_version: str = "4.0.0"
    dataset_fingerprint: Optional[str] = None  # SHA-256 fingerprint of input dataset

    model_config = ConfigDict(use_enum_values=True)


# ─────────────────────────────────────────────────────────────
#  Run-level metadata contract
# ─────────────────────────────────────────────────────────────

class BaselineMetadata(BaseModel):
    """Provenance metadata written to baseline_metadata.json for every run."""

    baseline_version: str
    run_timestamp: str
    input_dataset_version: str
    preprocessing_version: str
    dataset_fingerprint: str

    # Configuration snapshot
    temperature_feature: str
    selection_mode: str                     # "top_n" or "threshold"
    selection_parameter: Any               # top_n value or threshold °C
    tie_break_column: str
    missing_temperature_policy: str
    high_percentile: float
    medium_percentile: float

    # Counts
    total_neighbourhoods: int
    ranked_neighbourhoods: int
    data_insufficient_neighbourhoods: int
    selected_neighbourhoods: int
    missing_temperature_count: int
    excluded_neighbourhoods: int = 0

    # Statistics
    highest_temperature: Optional[float] = None
    lowest_ranked_temperature: Optional[float] = None


# ─────────────────────────────────────────────────────────────
#  Human-readable summary contract
# ─────────────────────────────────────────────────────────────

class BaselineSummary(BaseModel):
    """Machine and human-readable summary written to baseline_summary.json."""

    model_name: str = "Temperature-Only Baseline"
    model_description: str = (
        "This baseline uses temperature only and does not account for "
        "vulnerability, service access, fairness, or operational capacity."
    )
    temperature_feature: str
    status: BaselineRunStatus
    total_neighbourhoods: int
    ranked_neighbourhoods: int
    data_insufficient_neighbourhoods: int
    selected_neighbourhoods: int
    highest_temperature_c: Optional[float] = None
    lowest_ranked_temperature_c: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────
#  Top-level run result (returned by BaselinePrioritisationModel)
# ─────────────────────────────────────────────────────────────

class BaselineRunResult(BaseModel):
    """Complete output of one baseline model run."""

    status: BaselineRunStatus
    records: List[BaselineRecordResult] = Field(default_factory=list)
    metadata: Optional[BaselineMetadata] = None
    summary: Optional[BaselineSummary] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    model_config = ConfigDict(use_enum_values=True)
