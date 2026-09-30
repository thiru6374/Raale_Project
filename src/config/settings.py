import os
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    # Risk weights for Formal Mathematical Model
    temperature_weight: float = Field(default=0.3)
    built_environment_weight: float = Field(default=0.2)
    service_access_weight: float = Field(default=0.15)
    vulnerability_weight: float = Field(default=0.2)
    mobility_weight: float = Field(default=0.15)
    
    # Operational constraints
    number_of_teams: int = Field(default=5)
    maximum_visits_per_team: int = Field(default=10)
    working_hours: float = Field(default=8.0)
    maximum_people_per_day: int = Field(default=500)
    maximum_travel_time: int = Field(default=60) # minutes per team per day
    maximum_travel_distance: float = Field(default=50.0) # km per team per day
    neighbourhood_service_capacity: int = Field(default=100) # max people a team can serve per neighbourhood
    maximum_outreach_events_per_day: int = Field(default=50) # total network capacity
    
    # Fairness thresholds
    maximum_coverage_gap: float = Field(default=0.1)
    minimum_group_coverage: float = Field(default=0.2)
    
    # Confidence thresholds
    minimum_confidence_for_automatic_recommendation: float = Field(default=0.85)
    warning_confidence_threshold: float = Field(default=0.6)
    
    # Data Pipeline Settings
    raw_data_dir: str = Field(default="data/raw")
    processed_data_dir: str = Field(default="data/processed")
    external_data_dir: str = Field(default="data/external")
    metadata_filename: str = Field(default="metadata.json")
    
    # Synthetic Generator Settings
    default_district_name: str = Field(default="Chennai")
    synthetic_neighbourhood_count: int = Field(default=40)
    
    # Failure Simulation Flags
    simulate_missing_temperature: bool = Field(default=False)
    simulate_invalid_coordinates: bool = Field(default=False)
    simulate_duplicate_neighbourhood: bool = Field(default=False)
    simulate_extreme_temperature: bool = Field(default=False)

    # Real-world Data Mode
    # Options: SYNTHETIC, OPEN_DATA, MOCK_API, HYBRID, CSV_DATA
    data_mode: str = Field(default="CSV_DATA")

    # Active CSV dataset filename (relative to raw_data_dir).
    # Only used when data_mode == "CSV_DATA".
    active_csv_dataset: str = Field(default="chennai_heat_risk_big_dataset_50000.csv")
    
    # Freshness Thresholds
    freshness_threshold_hours: float = Field(default=4.0)
    staleness_threshold_hours: float = Field(default=24.0)
    
    # API Configuration
    weather_api_key: str = Field(default="")
    weather_api_url: str = Field(default="")
    
    # Missing Data Strategies
    missing_warning_threshold: float = Field(default=0.05)
    missing_critical_threshold: float = Field(default=0.20)
    numeric_imputation_strategy: str = Field(default="median")
    temperature_imputation_strategy: str = Field(default="preserve")
    categorical_imputation_strategy: str = Field(default="preserve")
    
    # Outlier Detection
    outlier_detection_method: str = Field(default="iqr")
    iqr_multiplier: float = Field(default=1.5)
    z_score_threshold: float = Field(default=3.0)
    preserve_plausible_extremes: bool = Field(default=True)
    
    # Data Processing & Integration
    percentage_representation: str = Field(default="0-100")
    date_format: str = Field(default="%Y-%m-%d")
    processed_dataset_format: str = Field(default="csv")
    preprocessing_version: str = Field(default="1.0.0")
    allow_unmatched_records: bool = Field(default=False)
    maximum_unmatched_percentage: float = Field(default=0.0)
    duplicate_record_policy: str = Field(default="fail")
    
    # Quality Status
    maximum_warning_count: int = Field(default=3)
    maximum_critical_error_count: int = Field(default=0)

    # Baseline Model Configuration
    # Temperature feature to use from the canonical processed dataset
    baseline_temperature_feature: str = Field(default="latest_temperature_c")
    # Supported: "top_n" (select top N hottest) or "threshold" (select above °C value)
    baseline_selection_mode: str = Field(default="top_n")
    # Number of neighbourhoods to select when mode = top_n
    baseline_top_n: int = Field(default=10)
    # Temperature threshold (°C) for selection when mode = threshold
    baseline_threshold_temperature: float = Field(default=37.0)
    # Priority category upper percentile bounds (proportional, sum must be <= 1.0)
    baseline_high_percentile: float = Field(default=0.25)   # top 25% → HIGH
    baseline_medium_percentile: float = Field(default=0.60) # next 35% → MEDIUM (25-60%)
    # Remaining valid records → LOW
    # Tie-break column (applied after temperature, must be a string/ID column)
    baseline_tie_break_column: str = Field(default="neighbourhood_id")
    # Policy when temperature is missing: "exclude" (recommended) or "impute_median"
    baseline_missing_temperature_policy: str = Field(default="exclude")
    # Baseline results output directory
    baseline_results_dir: str = Field(default="data/results/baseline")
    # Version string recorded in all baseline outputs for reproducibility
    baseline_version: str = Field(default="4.0.0")

    # ── / 6: Optimization Strategy & Experiment Settings ────────────
    # Active optimization strategy: "COVERAGE_FOCUSED", "BALANCED", "FAIRNESS_AWARE"
    optimization_strategy: str = Field(default="COVERAGE_FOCUSED")
    # Experiment output directory
    experiment_results_dir: str = Field(default="data/experiments")
    # Stakeholder feedback directory
    feedback_dir: str = Field(default="data/feedback")

    # ── Reproducibility: Random Seed ─────────────────────────────────────────
    # Set a fixed random seed for synthetic data generation.
    # Use None (or leave unset) for non-deterministic runs.
    random_seed: int = Field(default=42)

    model_config = ConfigDict(env_file=".env")

# Global settings instance
settings = Settings()
