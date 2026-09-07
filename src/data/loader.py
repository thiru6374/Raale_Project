import os
import pandas as pd
from typing import Optional, Dict, Any, Tuple
from src.utils.logger import get_logger
from src.utils.helpers import safe_read_csv, safe_read_json
from src.config.settings import settings

logger = get_logger("data_loader")

class DataLoader:
    """Provides reusable loading layer for raw and processed datasets."""
    
    def __init__(self, raw_dir: str = None, processed_dir: str = None):
        self.raw_dir = raw_dir or settings.raw_data_dir
        self.processed_dir = processed_dir or settings.processed_data_dir

    def load_raw_unified(self) -> Optional[pd.DataFrame]:
        """Loads the backward-compatible unified raw dataset."""
        path = os.path.join(self.raw_dir, "neighbourhoods_raw.csv")
        logger.info(f"Loading unified raw dataset from {path}")
        return safe_read_csv(path)

    def load_raw_domain_files(self) -> Dict[str, Optional[pd.DataFrame]]:
        """Loads the domain-specific raw datasets."""
        domain_files = {
            "temperature": "temperature_raw.csv",
            "built_environment": "built_environment_raw.csv",
            "service_access": "service_access_raw.csv",
            "vulnerability": "vulnerability_raw.csv"
        }
        
        datasets = {}
        for domain, filename in domain_files.items():
            path = os.path.join(self.raw_dir, filename)
            logger.info(f"Loading {domain} raw dataset from {path}")
            df = safe_read_csv(path)
            if df is not None:
                datasets[domain] = df
            else:
                logger.warning(f"Failed to load {domain} raw dataset.")
                datasets[domain] = None
                
        return datasets

    def load_raw_metadata(self) -> Optional[Dict[str, Any]]:
        """Loads raw dataset provenance metadata."""
        path = os.path.join(self.raw_dir, settings.metadata_filename)
        return safe_read_json(path)

    def load_processed_dataset(self, as_parquet: bool = False) -> Optional[pd.DataFrame]:
        """
        Loads the canonical processed dataset.
        Future modules (+) should use this method.
        """
        if as_parquet or settings.processed_dataset_format == "parquet":
            path = os.path.join(self.processed_dir, "neighbourhood_dataset.parquet")
            if os.path.isfile(path):
                logger.info(f"Loading processed dataset from {path}")
                try:
                    return pd.read_parquet(path)
                except Exception as e:
                    logger.error(f"Failed to read parquet: {e}")
                    return None
            logger.warning(f"Parquet format not found at {path}, attempting CSV fallback.")
            
        path = os.path.join(self.processed_dir, "neighbourhood_dataset.csv")
        logger.info(f"Loading processed dataset from {path}")
        return safe_read_csv(path)

    def save_processed_dataset(self, df: pd.DataFrame):
        """Saves the canonical processed dataset as CSV (and Parquet if configured)."""
        os.makedirs(self.processed_dir, exist_ok=True)
        
        csv_path = os.path.join(self.processed_dir, "neighbourhood_dataset.csv")
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved processed dataset to {csv_path}")
        
        if settings.processed_dataset_format == "parquet":
            parquet_path = os.path.join(self.processed_dir, "neighbourhood_dataset.parquet")
            try:
                df.to_parquet(parquet_path, index=False)
                logger.info(f"Saved processed dataset to {parquet_path}")
            except Exception as e:
                logger.error(f"Failed to save parquet format: {e}. Check if pyarrow or fastparquet is installed.")
