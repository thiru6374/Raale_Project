import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("feature_engineering")

class FeatureEngineer:
    """Creates intermediate sub-scores from preprocessed/normalized data."""
    
    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates service deficit and built environment risk scores.
        Assumes data has already passed through DataPreprocessor.
        """
        logger.info("Generating intermediate features...")
        result_df = df.copy()
        
        # 1. Service Deficit Score [0, 1]
        # High deficit = low capacity (inverted) and high distance
        if 'healthcare_capacity_normalized' in result_df.columns and 'healthcare_distance_km_normalized' in result_df.columns:
            capacity_deficit = 1.0 - result_df['healthcare_capacity_normalized']
            distance_risk = result_df['healthcare_distance_km_normalized']
            # Simple average of the two deficits
            result_df['service_deficit_score'] = (capacity_deficit + distance_risk) / 2.0
        else:
            logger.warning("Missing capacity/distance columns, defaulting service_deficit_score to 0.")
            result_df['service_deficit_score'] = 0.0
            
        # 2. Built Environment Risk [0, 1]
        # High risk = high density, high impervious, low green cover
        if all(c in result_df.columns for c in ['built_density_normalized', 'impervious_surface_percent', 'green_cover_percent']):
            density_risk = result_df['built_density_normalized']
            impervious_risk = result_df['impervious_surface_percent']
            # Invert green cover (low green cover = high risk)
            green_deficit = 1.0 - result_df['green_cover_percent']
            
            result_df['built_environment_score'] = (density_risk + impervious_risk + green_deficit) / 3.0
        else:
            logger.warning("Missing built environment columns, defaulting built_environment_score to 0.")
            result_df['built_environment_score'] = 0.0
            
        return result_df
