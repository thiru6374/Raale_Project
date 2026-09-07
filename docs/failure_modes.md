# Data Pipeline Failure Modes

This document details the intentional failure simulations available in the Phase 2 Data Pipeline, used to test downstream governance and error handling.

## Available Simulations

These simulations can be activated in `src/config/settings.py` or via environment variables.

### 1. `simulate_missing_temperature`
- **Effect:** Randomly injects `NaN` values into the `temperature_c` field based on `missing_rate`.
- **Validation Impact:** Triggers a missing required field validation error.
- **Expected Status:** `WARNING` or `MANUAL_REVIEW` depending on severity.

### 2. `simulate_invalid_coordinates`
- **Effect:** Forces the first generated neighbourhood to have an invalid latitude (e.g., 100.0).
- **Validation Impact:** Violates the `-90` to `90` constraint in Pydantic schema.
- **Expected Status:** Out-of-bounds error logged; record dropped from valid set.

### 3. `simulate_duplicate_neighbourhood`
- **Effect:** Forces the third generated neighbourhood to reuse the `neighbourhood_id` of the first record.
- **Validation Impact:** Ingestion pipeline detects the duplicate `neighbourhood_id`.
- **Expected Status:** Duplicate error logged; duplicates tracked in Data Quality Report.

### 4. `simulate_extreme_temperature`
- **Effect:** Forces the second generated neighbourhood to have an unrealistic base temperature (e.g., 55.0 °C).
- **Validation Impact:** May violate logical bounds if extreme limit set in schema (currently up to 60 °C is valid for hot districts, but higher triggers an out of bounds).
- **Expected Status:** Out of range failure or flagged as extreme risk downstream.

## Phase 4 Failure Behaviours

### 5. Missing Temperature in Baseline
- **Trigger:** Processed dataset contains rows where `latest_temperature_c` is missing.
- **Expected Behaviour:** Rows are marked as `DATA_INSUFFICIENT` and omitted from ranking. They do not silently drop to the bottom of the list. Baseline pipeline status becomes `COMPLETED_WITH_WARNING`.

### 6. All Temperatures Missing in Baseline
- **Trigger:** No valid temperatures exist in the canonical processed dataset.
- **Expected Behaviour:** The Baseline Pipeline aborts safely with status `FAILED` and outputs a clear error preventing misleading empty ranks.

### 7. Invalid Canonical Schema
- **Trigger:** Required temperature feature column missing from processed dataset.
- **Expected Behaviour:** Input validation catches the schema mismatch, logs the available columns, and aborts with status `FAILED`.

