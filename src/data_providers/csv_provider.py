"""
src/data_providers/csv_provider.py

Loads data directly from a selected CSV file.
Supports dynamic file selection via settings.active_csv_dataset.
Always loads ALL rows (ignores num_records) to ensure the full dataset is used.
"""
import os
import hashlib
import pandas as pd
from datetime import datetime
from typing import Tuple, Dict, Any

from src.data_providers.base_provider import BaseDataProvider
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("csv_data_provider")


def get_dataset_signature(file_path: str) -> dict:
    """Compute a dataset signature for cache-invalidation and identity."""
    if not os.path.exists(file_path):
        return {}
    stat = os.stat(file_path)
    # Quick signature using size + mtime (cheap, no full SHA256 for 50k rows)
    sig_str = f"{os.path.basename(file_path)}:{stat.st_size}:{stat.st_mtime}"
    sha = hashlib.md5(sig_str.encode()).hexdigest()
    return {
        "filename": os.path.basename(file_path),
        "file_path": os.path.abspath(file_path),
        "file_size_bytes": stat.st_size,
        "last_modified": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
        "signature": sha,
    }


def list_available_csv_datasets(raw_dir: str = None) -> list:
    """Scan the raw data directory and return available CSV filenames."""
    raw_dir = raw_dir or settings.raw_data_dir
    if not os.path.isdir(raw_dir):
        return []
    files = [f for f in os.listdir(raw_dir) if f.endswith(".csv") and "metadata" not in f.lower()]
    return sorted(files)


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise common schema mismatches that cause Pydantic validation failures.
    This is the ONE canonical place for raw CSV cleanup.
    """
    df = df.copy()

    # elderly_population_percent: schema requires 0-1; datasets may supply 0-100
    if "elderly_population_percent" in df.columns:
        mask = df["elderly_population_percent"] > 1
        df.loc[mask, "elderly_population_percent"] = (
            df.loc[mask, "elderly_population_percent"] / 100.0
        )

    # low_income_indicator: schema requires bool; datasets may supply float 0-1
    if "low_income_indicator" in df.columns:
        df["low_income_indicator"] = df["low_income_indicator"].apply(
            lambda x: True
            if (isinstance(x, (int, float)) and x > 0.5)
            or str(x).strip().lower() in ("true", "1", "yes")
            else False
        )

    # group_mobile / group_low_service_access — same treatment
    for col in ("group_mobile", "group_low_service_access"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: True
                if (isinstance(x, (int, float)) and x > 0.5)
                or str(x).strip().lower() in ("true", "1", "yes")
                else False
            )

    return df


class CSVDataProvider(BaseDataProvider):

    @property
    def provider_name(self) -> str:
        return "Local_CSV_Dataset"

    @property
    def source_type(self) -> str:
        return "CSV_DATA"

    def fetch_data(
        self, num_records: int = 0, missing_rate: float = 0.05, **kwargs
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Load the active CSV dataset.

        num_records=0 (default) → load ALL rows (correct for production use).
        num_records>0           → load only that many rows (for quick tests).
        """
        filename = getattr(settings, "active_csv_dataset", "chennai_heat_risk_big_dataset_50000.csv")
        file_path = os.path.join(settings.raw_data_dir, filename)

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"CSV dataset not found at '{file_path}'. "
                f"Place the file inside '{settings.raw_data_dir}/' and retry."
            )

        logger.info("Loading CSV dataset from %s (full load)", file_path)
        df = pd.read_csv(file_path)
        logger.info("Loaded %d rows × %d columns from %s", len(df), len(df.columns), filename)

        # Sanitize column types/scales before validation
        df = sanitize_dataframe(df)
        total_rows = len(df)

        # For multi-temporal datasets: filter to the LATEST observation date for
        # risk scoring / pipeline processing. The full historical dataset is still
        # available for trend analysis pages that explicitly need it.
        if "observation_date" in df.columns:
            df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce").dt.date.astype(str)
            unique_dates = df["observation_date"].dropna().unique()
            if len(unique_dates) > 1:
                latest_date = sorted(unique_dates)[-1]
                df_latest = df[df["observation_date"] == latest_date].copy()
                logger.info(
                    "Multi-temporal dataset: %d dates found. Filtering to latest: %s (%d rows → %d rows for pipeline).",
                    len(unique_dates), latest_date, total_rows, len(df_latest),
                )
                df = df_latest

        # Only truncate when explicitly requested (e.g. unit tests)
        if num_records and 0 < num_records < len(df):
            logger.warning(
                "Truncating dataset to %d rows (num_records parameter). "
                "This should only be used for testing.",
                num_records,
            )
            df = df.head(num_records)

        sig = get_dataset_signature(file_path)
        metadata = {
            "source_type": self.source_type,
            "provider_name": self.provider_name,
            "provider_status": "ONLINE",
            "is_live_data": False,
            "freshness": "FRESH",
            "fallback_activated": False,
            "records_fetched": len(df),
            "total_file_rows": total_rows,
            "pipeline_rows": len(df),
            "timestamp": datetime.utcnow().isoformat(),
            **sig,
        }

        return df, metadata
