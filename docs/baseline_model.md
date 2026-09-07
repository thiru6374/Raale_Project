# Phase 4: Temperature-Only Baseline Prioritisation Model

## Purpose
The purpose of the Temperature-Only Baseline Model is to establish a simple, transparent, deterministic comparator for the proposed Multi-Factor system (Phase 5).

By isolating the temperature factor, the final system can be evaluated in Phase 12 to demonstrate the exact measurable value added by integrating vulnerability, service-access, built-environment, and fairness indicators into the optimisation process.

## Algorithm
1. **Load Data**: Ingests the Phase 3 canonical processed dataset.
2. **Partition**: Identifies records missing the configured temperature feature and partitions them as `DATA_INSUFFICIENT`.
3. **Sort**: Valid records are sorted descending by temperature.
4. **Tie-Break**: Deterministic tie-breaking is applied using an alphabetical sort on `neighbourhood_id`. No fairness or vulnerability indicators are used to resolve ties.
5. **Categorise**: Percentile bounds assign the ranked records to `HIGH`, `MEDIUM`, or `LOW` priority.
6. **Select**: Records are flagged as selected for priority outreach based on configured `top_n` or temperature thresholds.

## Configuration
Controlled via `src/config/settings.py` (or `.env` overrides):
- `baseline_temperature_feature` (default: `latest_temperature_c`)
- `baseline_selection_mode` (`top_n` or `threshold`)
- `baseline_top_n` (default: 10)
- `baseline_threshold_temperature` (default: 37.0°C)
- `baseline_high_percentile` (default: 0.25)
- `baseline_medium_percentile` (default: 0.60)
- `baseline_missing_temperature_policy` (default: `exclude`)

## Input Contract
The Baseline strictly consumes `data/processed/neighbourhood_dataset.csv` loaded via `DataLoader`. It never reads raw data.

## Output Contract
Outputs are persisted to `data/results/baseline/`:
1. `baseline_results.csv`: Contains the per-neighbourhood ranks, scores, priorities, and selection flags.
2. `baseline_metadata.json`: Contains model version, input dataset fingerprint, timestamps, and parameters used.
3. `baseline_summary.json`: Contains aggregate statistics (total neighbourhoods, missing count, selected count).

## Missing Data Handling
If temperature data is missing, the baseline does not impute a value unless explicitly configured. By default (`exclude`), missing records are flagged as `DATA_INSUFFICIENT` and omitted from ranking. They do not silently fall to the bottom of the priority list as this could obscure actual high-risk areas from attention. 

## Limitations
- **Naive Priority**: This model intentionally ignores capacity constraints, meaning it may select areas that outreach teams cannot feasibly reach.
- **Fairness Blind**: The model does not attempt to distribute outreach equitably across mobile populations or historically underserved areas.
- **Vulnerability Blind**: A neighbourhood with slightly lower temperatures but extreme elderly populations will be ranked below a hotter neighbourhood with zero vulnerable individuals.
