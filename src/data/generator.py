import os
import json
import numpy as np
import pandas as pd
from datetime import date, datetime
import random
from typing import Tuple, Dict, Any

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("data_generator")

class SyntheticDataGenerator:
    """Generates synthetic neighbourhood heat-risk data for the chosen district."""
    
    # Bounding box roughly for the district (default Chennai)
    LAT_MIN = 12.9
    LAT_MAX = 13.2
    LON_MIN = 80.1
    LON_MAX = 80.3

    ZONES = [
        "North", "South", "East", "West", "Central"
    ]

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.reset_seed(seed)

    def reset_seed(self, seed: int):
        self.seed = seed
        np.random.seed(seed)
        random.seed(seed)

    def generate_data(self, num_records: int = None, missing_rate: float = 0.05) -> pd.DataFrame:
        """
        Generates a synthetic DataFrame and randomly injects missing values.
        Also applies failure simulations if enabled in settings.
        """
        num_records = num_records or settings.synthetic_neighbourhood_count
        district = settings.default_district_name
        
        data = []
        for i in range(num_records):
            zone = random.choice(self.ZONES)
            
            # Geography
            lat = np.random.uniform(self.LAT_MIN, self.LAT_MAX)
            lon = np.random.uniform(self.LON_MIN, self.LON_MAX)
            
            if settings.simulate_invalid_coordinates and i == 0:
                lat = 100.0 # Invalid latitude
            
            # Environment
            built_density = np.random.uniform(0.3, 0.95)
            green_cover = max(0.01, 1.0 - built_density - np.random.uniform(0, 0.2))
            impervious = min(0.99, built_density + np.random.uniform(0, 0.1))
            urban_heat_exposure = (built_density * 0.5) + (impervious * 0.4) - (green_cover * 0.3) + np.random.uniform(0, 0.1)

            # Temperature
            base_temp = np.random.uniform(32.0, 38.0)
            if settings.simulate_extreme_temperature and i == 1:
                base_temp = 55.0
                
            uhi_effect = built_density * 3.0
            temperature_c = base_temp + uhi_effect
            heat_index = temperature_c + np.random.uniform(2.0, 5.0)

            # Population & Demographics
            total_population = int(np.random.uniform(10000, 100000))
            elderly_percent = np.random.uniform(0.05, 0.25)
            low_income = random.choice([True, False, False])
            vuln_index = (elderly_percent * 2.0) + (0.3 if low_income else 0.0) + np.random.uniform(0, 0.2)
            vuln_index = min(1.0, vuln_index)

            # Mobile population
            mobile_pop = int(total_population * np.random.uniform(0.01, 0.1))
            mobile_pop_percent = mobile_pop / total_population

            # Services
            distance_km = np.random.uniform(0.5, 5.0)
            capacity = int(np.random.uniform(500, 5000))
            transport = np.random.uniform(0.1, 1.0)
            travel_time_minutes = distance_km * np.random.uniform(5.0, 15.0)
            service_time_minutes = np.random.uniform(10.0, 30.0)
            estimated_people_reachable = int(capacity * np.random.uniform(0.5, 1.0))
            
            # IDs
            n_id = f"NH-{i:03d}"
            if settings.simulate_duplicate_neighbourhood and i == 2:
                n_id = "NH-000" # Force duplicate with first record

            record = {
                "neighbourhood_id": n_id,
                "neighbourhood_name": f"{district} {zone} Zone {np.random.randint(1, 10)}",
                "district": district,
                "latitude": lat,
                "longitude": lon,
                "observation_date": date.today().isoformat(),
                "temperature_c": temperature_c,
                "heat_index": heat_index,
                "humidity_percent": np.random.uniform(30, 90),
                "built_density": built_density,
                "green_cover_percent": green_cover * 100, # converted to 0-100 scale
                "impervious_surface_percent": impervious * 100, # converted to 0-100 scale
                "urban_heat_exposure_score": urban_heat_exposure,
                "healthcare_distance_km": distance_km,
                "healthcare_capacity": capacity,
                "transport_access_score": transport,
                "estimated_people_reachable": estimated_people_reachable,
                "travel_time_minutes": travel_time_minutes,
                "service_time_minutes": service_time_minutes,
                "vulnerability_index": vuln_index,
                "elderly_population_percent": elderly_percent,
                "low_income_indicator": low_income,
                "total_population": total_population,
                "mobile_population": mobile_pop,
                "mobile_population_percent": mobile_pop_percent,
                "group_mobile": mobile_pop_percent > 0.05,
                "group_low_service_access": transport < 0.4,
                "data_source": "synthetic_generator",
                "generated_at": datetime.now().isoformat(),
                "dataset_version": "1.0.0",
                "synthetic_data": True
            }
            data.append(record)
            
        df = pd.DataFrame(data)

        # Inject missing values for fallback testing
        if settings.simulate_missing_temperature:
            mask = np.random.rand(len(df)) < missing_rate
            df.loc[mask, "temperature_c"] = np.nan
        
        nullable_fields = [
            "heat_index", 
            "healthcare_capacity", 
            "vulnerability_index", 
            "low_income_indicator"
        ]
        
        for field in nullable_fields:
            mask = np.random.rand(len(df)) < missing_rate
            if df[field].dtype == 'bool':
                df[field] = df[field].astype('object')
            if df[field].dtype == 'object':
                df.loc[mask, field] = None
            else:
                df.loc[mask, field] = np.nan
                
        return df

    def save_dataset(self, df: pd.DataFrame, output_dir: str) -> Tuple[str, Dict[str, Any]]:
        os.makedirs(output_dir, exist_ok=True)
        csv_path = os.path.join(output_dir, "neighbourhoods_raw.csv")
        df.to_csv(csv_path, index=False)
        
        # Save separate domain files for integration testing
        # 1. Temperature (allow multiple observations to test aggregation)
        temp_cols = ["neighbourhood_id", "observation_date", "temperature_c", "heat_index", "humidity_percent"]
        df_temp = df[temp_cols].copy()
        
        # Add a mock historical observation for the first 5 records to test aggregation
        if len(df_temp) > 5:
            historical = df_temp.iloc[:5].copy()
            historical["observation_date"] = "2023-01-01"
            historical["temperature_c"] = historical["temperature_c"] - np.random.uniform(1.0, 3.0)
            df_temp = pd.concat([df_temp, historical], ignore_index=True)
            
        df_temp.to_csv(os.path.join(output_dir, "temperature_raw.csv"), index=False)
        
        # 2. Built Environment
        built_cols = ["neighbourhood_id", "built_density", "green_cover_percent", "impervious_surface_percent", "urban_heat_exposure_score"]
        df[built_cols].to_csv(os.path.join(output_dir, "built_environment_raw.csv"), index=False)
        
        # 3. Service Access
        service_cols = ["neighbourhood_id", "healthcare_distance_km", "healthcare_capacity", "transport_access_score", "estimated_people_reachable", "travel_time_minutes", "service_time_minutes"]
        df[service_cols].to_csv(os.path.join(output_dir, "service_access_raw.csv"), index=False)
        
        # 4. Vulnerability & Demographics
        vuln_cols = ["neighbourhood_id", "vulnerability_index", "elderly_population_percent", "low_income_indicator", "total_population", "mobile_population", "mobile_population_percent", "group_mobile", "group_low_service_access"]
        df[vuln_cols].to_csv(os.path.join(output_dir, "vulnerability_raw.csv"), index=False)
        
        metadata = {
            "dataset_name": "synthetic_neighbourhood_data",
            "dataset_version": "1.0.0",
            "source_type": "synthetic",
            "source_name": "SyntheticDataGenerator",
            "synthetic_data": True,
            "generated_at": datetime.now().isoformat(),
            "random_seed": self.seed,
            "record_count": len(df),
            "schema_version": "1.0"
        }
        
        meta_path = os.path.join(output_dir, settings.metadata_filename)
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=4)
            
        logger.info(f"Saved unified dataset, domain datasets, and metadata to {output_dir}")
        return csv_path, metadata

if __name__ == "__main__":
    """Entry point: python -m src.data.generator
    
    Generates a clean synthetic dataset, saves raw CSV + metadata, then runs
    validation and saves the valid records to the processed directory.
    """
    import os
    from src.data.ingestion import DataIngestor, CSVDataProvider

    # 1. Generate raw data
    generator = SyntheticDataGenerator()
    raw_df = generator.generate_data()
    raw_csv_path, metadata = generator.save_dataset(raw_df, settings.raw_data_dir)
    logger.info(f"Raw dataset: {len(raw_df)} records written to {raw_csv_path}")

    # 2. Validate using the CSV provider (ensures the saved file is the source of truth)
    provider = CSVDataProvider(file_path=raw_csv_path)
    ingestor = DataIngestor(provider)
    valid_df, report = ingestor.load_and_validate()
    logger.info(
        f"Validation complete: {report.valid_records}/{report.total_records} valid. "
        f"Status: {report.status.value}"
    )

    # 3. Save processed dataset
    os.makedirs(settings.processed_data_dir, exist_ok=True)
    processed_path = os.path.join(settings.processed_data_dir, "neighbourhood_dataset.csv")
    valid_df.to_csv(processed_path, index=False)
    logger.info(f"Processed dataset saved to {processed_path}")

    # 4. Print summary
    print(f"\n{'='*60}")
    print(f"  GENERATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Raw records        : {report.total_records}")
    print(f"  Valid records      : {report.valid_records}")
    print(f"  Invalid/Skipped    : {report.invalid_records}")
    print(f"  Duplicate IDs      : {report.duplicate_records}")
    print(f"  Quality Status     : {report.status.value}")
    print(f"  Raw CSV            : {raw_csv_path}")
    print(f"  Processed CSV      : {processed_path}")
    print(f"  Metadata JSON      : {os.path.join(settings.raw_data_dir, settings.metadata_filename)}")
    print(f"{'='*60}\n")
