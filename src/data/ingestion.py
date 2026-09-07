import os
import pandas as pd
from typing import Tuple, List, Dict, Optional
from pydantic import ValidationError
from abc import ABC, abstractmethod

from src.data.validation import NeighbourhoodData, DataQualityReport, DataQualityStatus
from src.utils.logger import get_logger
from src.config.settings import settings

logger = get_logger("data_ingestion")

class BaseDataProvider(ABC):
    """Base class for data ingestion providers."""
    
    @abstractmethod
    def fetch_data(self) -> pd.DataFrame:
        """Fetch data from the source and return a raw DataFrame."""
        pass

class CSVDataProvider(BaseDataProvider):
    """Ingests data from a CSV file."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def fetch_data(self) -> pd.DataFrame:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")
        logger.info(f"Fetching data from CSV: {self.file_path}")
        return pd.read_csv(self.file_path)

class APIDataProvider(BaseDataProvider):
    """
    Ingests data from a live external API.
    This is an architectural placeholder; real API integration is added in later phases.
    Fails gracefully when API_URL or API_KEY are not configured.
    """
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        
    def fetch_data(self) -> pd.DataFrame:
        if not self.api_url or not self.api_key:
            logger.warning(
                "APIDataProvider: API_URL or API_KEY not configured. "
                "Returning empty DataFrame. Configure settings.weather_api_url "
                "and settings.weather_api_key to enable live data."
            )
            return pd.DataFrame()
            
        logger.info(f"Fetching data from API: {self.api_url}")
        # Placeholder — replace with requests.get(...) and response parsing in +
        raise NotImplementedError(
            "Live API ingestion not yet implemented. "
            "Use SyntheticDataProvider or CSVDataProvider for ."
        )

class MockAPIDataProvider(BaseDataProvider):
    """
    mock for external API data sources.
    Returns a standardised synthetic DataFrame that mimics what a real
    temperature / built-environment / service-access API would return.

    Design contract:
      - Implements BaseDataProvider so it is a drop-in for APIDataProvider.
      - Produces a dataset column-compatible with NeighbourhoodData.
      - Real API providers (OpenWeatherMap, government met APIs, etc.) only
        need to replace this class — the rest of the pipeline is unchanged.

    Supported mock_type values:
      'temperature'        — simulates a weather API response
      'built_environment'  — simulates a land-use / GIS API response
      'service_access'     — simulates a healthcare facilities API response
      'full'               — simulates a combined response (default)
    """

    def __init__(self, num_records: int = None, seed: int = 42, mock_type: str = "full"):
        self.num_records = num_records or settings.synthetic_neighbourhood_count
        self.seed = seed
        self.mock_type = mock_type

    def fetch_data(self) -> pd.DataFrame:
        """Return a mock DataFrame simulating an external API response."""
        logger.info(
            f"MockAPIDataProvider: returning mock '{self.mock_type}' data "
            f"({self.num_records} records, seed={self.seed})"
        )
        from src.data.generator import SyntheticDataGenerator
        generator = SyntheticDataGenerator(seed=self.seed)
        df = generator.generate_data(num_records=self.num_records, missing_rate=0.0)
        df["data_source"] = f"mock_api_{self.mock_type}"
        return df

class SyntheticDataProvider(BaseDataProvider):
    """Ingests data from the synthetic generator."""
    def __init__(self, num_records: int = None, missing_rate: float = 0.05):
        self.num_records = num_records or settings.synthetic_neighbourhood_count
        self.missing_rate = missing_rate
        
    def fetch_data(self) -> pd.DataFrame:
        from src.data.generator import SyntheticDataGenerator
        logger.info(f"Generating {self.num_records} synthetic records (Missing rate: {self.missing_rate})")
        generator = SyntheticDataGenerator(seed=settings.random_seed)
        df = generator.generate_data(num_records=self.num_records, missing_rate=self.missing_rate)
        return df

class DataIngestor:
    """Handles ingestion and strict validation of neighbourhood data."""

    def __init__(self, provider: BaseDataProvider):
        self.provider = provider

    def load_and_validate(self) -> Tuple[pd.DataFrame, DataQualityReport]:
        """Loads data from the provider and validates it, generating a DataQualityReport."""
        raw_df = self.provider.fetch_data()
        if raw_df.empty:
            logger.error("No data fetched from provider.")
            return raw_df, self._create_empty_report()
            
        return self.validate_dataframe(raw_df)

    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, DataQualityReport]:
        """
        Validates each row of the dataframe against the Pydantic schema.
        Returns a tuple of (valid_dataframe, DataQualityReport).
        """
        valid_records = []
        errors = []
        
        # Tracking metrics
        missing_values_count = 0
        out_of_range_values_count = 0
        
        # Duplicate detection setup
        seen_ids = set()
        duplicate_records = 0

        for idx, row in df.iterrows():
            row_dict = row.replace({pd.NA: None}).where(pd.notnull(row), None).to_dict()
            
            n_id = row_dict.get("neighbourhood_id")
            obs_date = row_dict.get("observation_date", "")
            # Use composite key: neighbourhood_id + observation_date
            # This correctly handles multi-temporal datasets where the same
            # neighbourhood has one record per observation date.
            composite_key = f"{n_id}|{obs_date}"
            if composite_key in seen_ids:
                duplicate_records += 1
                errors.append({"row_index": idx, "neighbourhood_id": n_id, "error_type": "duplicate_id"})
                continue
            
            if composite_key:
                seen_ids.add(composite_key)
            
            try:
                validated = NeighbourhoodData(**row_dict)
                valid_records.append(validated.model_dump())
            except ValidationError as e:
                for error in e.errors():
                    if error['type'] == 'missing':
                        missing_values_count += 1
                    else:
                        out_of_range_values_count += 1
                
                errors.append({
                    "row_index": idx,
                    "neighbourhood_id": n_id or "UNKNOWN",
                    "errors": e.errors()
                })
        
        valid_df = pd.DataFrame(valid_records) if valid_records else pd.DataFrame()
        
        invalid_records = len(errors)
        total = len(df)
        valid = len(valid_records)
        
        # Determine Status
        status = DataQualityStatus.APPROVED
        if invalid_records > 0 or duplicate_records > 0:
            if valid == 0:
                status = DataQualityStatus.FAILED
            elif (invalid_records + duplicate_records) / total > 0.2:
                status = DataQualityStatus.MANUAL_REVIEW
            else:
                status = DataQualityStatus.WARNING
                
        report = DataQualityReport(
            dataset_name="neighbourhood_dataset",
            total_records=total,
            valid_records=valid,
            invalid_records=invalid_records,
            duplicate_records=duplicate_records,
            missing_values=missing_values_count,
            out_of_range_values=out_of_range_values_count,
            warnings=invalid_records if status == DataQualityStatus.WARNING else 0,
            critical_failures=invalid_records if status in [DataQualityStatus.MANUAL_REVIEW, DataQualityStatus.FAILED] else 0,
            status=status,
            details=errors
        )
        
        if errors:
            logger.warning(f"{invalid_records} records failed validation out of {total}. Status: {status}")
            
        return valid_df, report

    def _create_empty_report(self) -> DataQualityReport:
        return DataQualityReport(
            dataset_name="empty_dataset",
            total_records=0, valid_records=0, invalid_records=0, duplicate_records=0,
            missing_values=0, out_of_range_values=0, warnings=0, critical_failures=0,
            status=DataQualityStatus.FAILED
        )

# Kept for backward compatibility in tests while transitioning
def load_synthetic_data(num_records: int = 50, missing_rate: float = 0.05) -> Tuple[pd.DataFrame, List[Dict]]:
    """Convenience wrapper: generate synthetic data, validate it, return (valid_df, error_list)."""
    provider = SyntheticDataProvider(num_records=num_records, missing_rate=missing_rate)
    ingestor = DataIngestor(provider)
    valid_df, report = ingestor.load_and_validate()
    return valid_df, report.details


if __name__ == "__main__":
    """Entry point: python -m src.data.ingestion  →  prints a Data Quality Report."""
    import json
    _provider = SyntheticDataProvider()
    _ingestor = DataIngestor(_provider)
    _valid_df, _report = _ingestor.load_and_validate()

    print("\n" + "=" * 60)
    print("  DATA QUALITY REPORT")
    print("=" * 60)
    print(f"  Dataset       : {_report.dataset_name}")
    print(f"  Total Records : {_report.total_records}")
    print(f"  Valid Records : {_report.valid_records}")
    print(f"  Invalid       : {_report.invalid_records}")
    print(f"  Duplicates    : {_report.duplicate_records}")
    print(f"  Missing Values: {_report.missing_values}")
    print(f"  Out-of-Range  : {_report.out_of_range_values}")
    print(f"  Warnings      : {_report.warnings}")
    print(f"  Critical Fail : {_report.critical_failures}")
    print(f"  Status        : {_report.status.value}")
    print("=" * 60 + "\n")
