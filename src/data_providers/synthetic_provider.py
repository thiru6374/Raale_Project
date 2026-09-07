"""
src/data_providers/synthetic_provider.py

Wraps the existing SyntheticDataGenerator.
"""
import pandas as pd
from datetime import datetime
from typing import Tuple, Dict, Any

from src.data_providers.base_provider import BaseDataProvider
from src.data.generator import SyntheticDataGenerator

class SyntheticProvider(BaseDataProvider):
    
    @property
    def provider_name(self) -> str:
        return "Phase2_Synthetic_Generator"
        
    @property
    def source_type(self) -> str:
        return "SYNTHETIC"
        
    def fetch_data(self, num_records: int = 100, missing_rate: float = 0.05, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        generator = SyntheticDataGenerator()
        df = generator.generate_data(num_records=num_records, missing_rate=missing_rate)
        
        # Ensure provenance is strictly attached
        df["data_source"] = self.source_type
        df["provider"] = self.provider_name
        df["retrieved_at"] = datetime.utcnow().isoformat() + "Z"
        
        metadata = {
            "source_type": self.source_type,
            "provider_name": self.provider_name,
            "retrieved_at": datetime.utcnow().isoformat() + "Z",
            "is_live_data": False,
            "provider_status": "SUCCESS",
            "freshness": "FRESH (Generated)"
        }
        
        return df, metadata
