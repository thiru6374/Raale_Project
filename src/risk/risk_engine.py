import pandas as pd
import numpy as np
from src.config.settings import settings
from src.utils.logger import get_logger
from src.risk.baseline import BaselineRiskModel

logger = get_logger("multi_factor_risk")

class MultiFactorRiskModel:
    """Calculates the weighted multi-factor heat-risk score."""
    
    def calculate_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Requires baseline_risk_score, built_environment_score, service_deficit_score, and vulnerability_index.
        """
        logger.info("Calculating multi-factor risk scores...")
        result_df = df.copy()
        
        # Ensure baseline risk is calculated first
        if 'baseline_risk_score' not in result_df.columns:
            logger.info("Baseline risk not found. Calculating baseline first...")
            baseline = BaselineRiskModel()
            result_df = baseline.calculate_risk(result_df)
            
        # Fill missing sub-scores with 0 temporarily if they don't exist
        for col in ['built_environment_score', 'service_deficit_score', 'vulnerability_index']:
            if col not in result_df.columns:
                logger.warning(f"Required sub-score '{col}' missing. Assuming 0.")
                result_df[col] = 0.0
                
        # Calculate Weighted Sum
        weighted_sum = (
            (result_df['baseline_risk_score'] * settings.temperature_weight) +
            (result_df['built_environment_score'] * settings.built_environment_weight) +
            (result_df['service_deficit_score'] * settings.service_access_weight) +
            (result_df['vulnerability_index'] * settings.vulnerability_weight)
        )
        
        # The sum of weights from settings should ideally be 1.0, but we normalize just in case
        total_weight = (settings.temperature_weight + settings.built_environment_weight + 
                        settings.service_access_weight + settings.vulnerability_weight)
                        
        result_df['multi_factor_risk_score'] = (weighted_sum / total_weight).clip(0.0, 1.0)
        
        # Categorize
        # Using proportional bounds based on the [0, 1] score
        conditions = [
            (result_df['multi_factor_risk_score'] >= 0.75),
            (result_df['multi_factor_risk_score'] >= 0.50),
            (result_df['multi_factor_risk_score'] >= 0.25),
            (result_df['multi_factor_risk_score'] < 0.25)
        ]
        choices = ['EXTREME', 'HIGH', 'MODERATE', 'LOW']
        
        result_df['multi_factor_risk_category'] = np.select(conditions, choices, default='UNKNOWN')
        
        return result_df
