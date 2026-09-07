# Workflow Guide

## End-to-End Pipeline Steps

### Step 1 — Generate & Ingest Data
**Module**: `src/data/generator.py`, `src/data/ingestion.py`

Produces a DataFrame of simulated Chennai neighbourhoods (N records). Each record is validated against the `NeighbourhoodData` Pydantic schema. Records failing validation are rejected and logged.

### Step 2 — Preprocess
**Module**: `src/data/preprocessing.py`

Applies two transformations:
- **Imputation**: Fills missing values with the median of the dataset for numeric fields, and `False` for boolean indicators.
- **Normalization**: Scales high-variance numeric columns to [0, 1] using Min-Max scaling. Required for equal-weighted aggregation in the risk engine.

### Step 3 — Feature Engineering
**Module**: `src/features/engineering.py`

Constructs two intermediate sub-scores from normalized columns:
- `service_deficit_score`: How poorly served is the area?
- `built_environment_score`: How hostile is the physical environment?

### Step 4 — Risk Scoring (Both Models)
**Modules**: `src/risk/baseline.py`, `src/risk/risk_engine.py`

- **Baseline**: Scores risk using only temperature/heat index. Used as a reference comparator.
- **Multi-Factor**: Combines all four pillars using configurable weights from `settings.py`.

### Step 5 — Confidence Evaluation
**Module**: `src/risk/confidence.py`

For each row, counts the number of critical fields that were `NaN` before imputation. Computes a `confidence_score` and assigns a `fallback_status`.

### Step 6 — Optimisation
**Module**: `src/optimisation/planner.py`

Formulates and solves a Binary Integer Programming problem using PuLP/CBC:
- **Objective**: Maximise total risk mitigated (risk × population)
- **Constraint 1**: Total selections ≤ teams × visits-per-team
- **Constraint 2**: MANUAL_REVIEW rows are excluded from automated selection

### Step 7 — Fairness Audit
**Module**: `src/fairness/bias_detection.py`

Compares the global selection rate against each vulnerable group's selection rate. Flags any group whose coverage gap exceeds the configured threshold.

### Step 8 — Communication
**Module**: `src/communication/message_generator.py`

For each selected neighbourhood, generates a context-specific advisory based on:
- Risk category (sets urgency)
- Green cover (cooling advice)
- Elderly proportion (community check advice)
- Healthcare distance (emergency transit advice)

### Step 9 — Human Override (Optional)
**Module**: `src/governance/overrides.py`, `src/governance/audit_logger.py`

Administrators can force-select or force-deselect any neighbourhood. Every override writes a JSON record to `logs/audit.jsonl` before being applied. If the log write fails, the override is refused.

## User Flow in Streamlit

1. Set parameters in the sidebar
2. Click **Run End-to-End Pipeline** on the Outreach Planner page
3. View live pipeline progress in the status expander
4. Inspect risk charts, the interactive Chennai map, and the action table
5. Apply human overrides if needed
6. Review bias warnings on the Fairness Analysis page
7. Check the override log on the Audit Trail page
