"""
src/data_providers/mock_api_provider.py

Simulates external REST API failures, latency, and schema variations for architecture testing.
"""
import time
import random
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any

from src.data_providers.base_provider import BaseDataProvider
from src.data_providers.synthetic_provider import SyntheticProvider

class MockAPIProvider(BaseDataProvider):
    
    def __init__(self, simulate_failure: bool = False, simulate_stale: bool = False):
        self.simulate_failure = simulate_failure
        self.simulate_stale = simulate_stale
    
    @property
    def provider_name(self) -> str:
        return "Resilience_Test_MockAPI"
        
    @property
    def source_type(self) -> str:
        return "MOCK_API"
        
    def fetch_data(self, num_records: int = 100, missing_rate: float = 0.05, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        time.sleep(random.uniform(0.1, 0.5)) # Simulate latency
        
        if self.simulate_failure:
            # Simulate a 503 or Timeout
            raise ConnectionError("Mock API simulated connection timeout (503 Service Unavailable).")
            
        # We reuse the synthetic generator to get a baseline dataframe, 
        # but pretend it came from an API
        synth_provider = SyntheticProvider()
        df, _ = synth_provider.fetch_data(num_records, missing_rate)
        
        df["data_source"] = self.source_type
        df["provider"] = self.provider_name
        
        retrieved_at = datetime.utcnow()
        obs_time = retrieved_at
        
        if self.simulate_stale:
            # Simulate data that is 48 hours old
            obs_time = retrieved_at - timedelta(hours=48)
            df["temperature_c"] = df["temperature_c"] - random.uniform(1.0, 5.0) # slightly off
            
        df["retrieved_at"] = retrieved_at.isoformat() + "Z"
        df["observation_date"] = obs_time.isoformat() + "Z"
        
        metadata = {
            "source_type": self.source_type,
            "provider_name": self.provider_name,
            "retrieved_at": retrieved_at.isoformat() + "Z",
            "observation_timestamp": obs_time.isoformat() + "Z",
            "is_live_data": False,
            "provider_status": "SIMULATED_SUCCESS",
            "freshness": "STALE" if self.simulate_stale else "FRESH"
        }
        
        return df, metadata
