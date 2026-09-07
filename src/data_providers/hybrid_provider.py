"""
src/data_providers/hybrid_provider.py

Creates a hybrid dataset using Open Data for available domains,
falling back to Synthetic for missing domains.
"""
import pandas as pd
from datetime import datetime
from typing import Tuple, Dict, Any

from src.data_providers.base_provider import BaseDataProvider
from src.data_providers.open_data_provider import OpenDataProvider
from src.data_providers.synthetic_provider import SyntheticProvider
from src.utils.logger import get_logger

logger = get_logger("hybrid_provider")

class HybridDataProvider(BaseDataProvider):
    
    @property
    def provider_name(self) -> str:
        return "Hybrid_Orchestrator"
        
    @property
    def source_type(self) -> str:
        return "HYBRID"
        
    def fetch_data(self, num_records: int = 100, missing_rate: float = 0.05, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        synth_provider = SyntheticProvider()
        df_base, synth_meta = synth_provider.fetch_data(num_records, missing_rate)
        
        domain_provenance = {
            "vulnerability": "SYNTHETIC",
            "service_access": "SYNTHETIC",
            "built_environment": "SYNTHETIC",
            "temperature": "SYNTHETIC"
        }
        
        provider_status = "PARTIAL_SUCCESS"
        freshness = "FRESH"
        obs_time = datetime.utcnow()
        
        # Attempt to inject Open Data for temperature
        open_provider = OpenDataProvider()
        try:
            df_open, open_meta = open_provider.fetch_data(num_records, 0.0) # no missing rate injected for real data initially
            
            # Hybrid mix
            df_base["temperature_c"] = df_open["temperature_c"]
            df_base["heat_index"] = df_open["heat_index"]
            df_base["observation_date"] = df_open["observation_date"]
            
            domain_provenance["temperature"] = "OPEN_DATA"
            provider_status = "SUCCESS"
            freshness = open_meta.get("freshness", "FRESH")
            
            # If the open data has a valid obs time, use it
            if "observation_timestamp" in open_meta:
                obs_time = datetime.fromisoformat(open_meta["observation_timestamp"].replace("Z", ""))
                
        except Exception as e:
            logger.warning(f"Hybrid mode could not fetch Open Data. Falling back to 100% Synthetic. Error: {e}")
            provider_status = "OPEN_DATA_FAILED_USING_FALLBACK"

        df_base["data_source"] = self.source_type
        df_base["provider"] = self.provider_name
        
        metadata = {
            "source_type": self.source_type,
            "provider_name": self.provider_name,
            "retrieved_at": datetime.utcnow().isoformat() + "Z",
            "observation_timestamp": obs_time.isoformat() + "Z",
            "is_live_data": domain_provenance["temperature"] == "OPEN_DATA",
            "provider_status": provider_status,
            "freshness": freshness,
            "domain_provenance": domain_provenance
        }
        
        return df_base, metadata
