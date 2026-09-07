"""
src/data_providers/base_provider.py

Defines the common interface for all Data Providers (Synthetic, Open, Mock, Hybrid).
"""
import pandas as pd
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any

class BaseDataProvider(ABC):
    """
    Common data provider interface that all sources must implement.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def source_type(self) -> str:
        """E.g. SYNTHETIC, OPEN_DATA, MOCK_API, HYBRID"""
        pass
        
    @abstractmethod
    def fetch_data(self, **kwargs) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Fetches and returns the data along with provenance metadata.
        The dataframe must adhere to the common data contract expected by .
        
        Returns:
            Tuple[pd.DataFrame, Dict[str, Any]]: (dataframe, provenance_metadata)
        """
        pass
