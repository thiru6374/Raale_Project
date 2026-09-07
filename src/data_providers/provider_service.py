"""
src/data_providers/provider_service.py

Orchestrates data providers, handling source selection, configuration, and fallback mechanisms.
"""
import pandas as pd
from typing import Tuple, Dict, Any

from src.data_providers.synthetic_provider import SyntheticProvider
from src.data_providers.open_data_provider import OpenDataProvider
from src.data_providers.mock_api_provider import MockAPIProvider
from src.data_providers.hybrid_provider import HybridDataProvider
from src.data_providers.csv_provider import CSVDataProvider
from src.utils.logger import get_logger

logger = get_logger("provider_service")

class ProviderService:
    
    @staticmethod
    def get_data(data_mode: str, num_records: int = 100, missing_rate: float = 0.05) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Fetches data based on the requested mode.
        If the requested mode fails, attempts safe fallback to SYNTHETIC.
        """
        provider = None
        data_mode = data_mode.upper()
        
        logger.info(f"ProviderService requested data mode: {data_mode}")
        
        if data_mode == "SYNTHETIC":
            provider = SyntheticProvider()
        elif data_mode == "OPEN_DATA":
            provider = OpenDataProvider()
        elif data_mode == "MOCK_API":
            provider = MockAPIProvider(simulate_failure=False, simulate_stale=False)
        elif data_mode == "HYBRID":
            provider = HybridDataProvider()
        elif data_mode == "CSV_DATA":
            provider = CSVDataProvider()
        else:
            logger.warning(f"Unknown data mode '{data_mode}', defaulting to SYNTHETIC.")
            provider = SyntheticProvider()
            
        try:
            df, metadata = provider.fetch_data(num_records=num_records, missing_rate=missing_rate)
            metadata["fallback_activated"] = False
            return df, metadata
            
        except Exception as e:
            logger.error(f"Primary provider '{provider.provider_name}' failed: {e}")
            logger.info("Initiating Safe Fallback to SYNTHETIC provider.")
            
            # Safe Fallback to Synthetic
            fallback_provider = SyntheticProvider()
            df, metadata = fallback_provider.fetch_data(num_records=num_records, missing_rate=missing_rate)
            
            # Record the fallback in provenance
            metadata["fallback_activated"] = True
            metadata["fallback_reason"] = str(e)
            metadata["original_requested_mode"] = data_mode
            metadata["provider_status"] = "FALLBACK_TO_SYNTHETIC"
            
            df["data_source"] = "SYNTHETIC_FALLBACK"
            
            return df, metadata
