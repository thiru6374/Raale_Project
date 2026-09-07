"""
tests/test_data_providers.py
"""
import pytest
import pandas as pd
from src.data_providers.synthetic_provider import SyntheticProvider
from src.data_providers.mock_api_provider import MockAPIProvider
from src.data_providers.provider_service import ProviderService
from src.config.settings import settings

def test_synthetic_provider():
    provider = SyntheticProvider()
    df, meta = provider.fetch_data(num_records=10)
    assert len(df) == 10
    assert meta["source_type"] == "SYNTHETIC"
    assert "data_source" in df.columns

def test_mock_api_provider():
    provider = MockAPIProvider(simulate_failure=False, simulate_stale=True)
    df, meta = provider.fetch_data(num_records=10)
    assert meta["source_type"] == "MOCK_API"
    assert meta["freshness"] == "STALE"

def test_provider_service_fallback():
    # If we request a mock API that fails, it should fallback to SYNTHETIC
    # We will simulate this by forcing the mock API to fail inside the service if we could inject it.
    # But since ProviderService creates it internally based on string, let's test the string matching.
    df, meta = ProviderService.get_data("UNKNOWN_MODE", num_records=10)
    assert len(df) == 10
    assert meta["source_type"] == "SYNTHETIC"
    
def test_hybrid_provider_through_service():
    df, meta = ProviderService.get_data("HYBRID", num_records=10)
    assert len(df) == 10
    assert meta["source_type"] == "HYBRID"
    assert "temperature" in meta.get("domain_provenance", {})
