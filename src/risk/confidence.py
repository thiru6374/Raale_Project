import pandas as pd
from src.utils.logger import get_logger
from src.governance.fallback import assess_data_completeness

logger = get_logger("confidence_evaluator")

class ConfidenceEvaluator:
    """Evaluates the confidence of risk scores based on raw data completeness."""
    
    # Core fields that heavily influence the multi-factor risk score
    CRITICAL_FIELDS = [
        'temperature_c',
        'heat_index',
        'built_density',
        'green_cover_percent',
        'impervious_surface_percent',
        'healthcare_capacity',
        'healthcare_distance_km',
        'vulnerability_index',
        'elderly_population_percent',
        'low_income_indicator'
    ]
    
    def evaluate(self, raw_df: pd.DataFrame, processed_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates confidence score based on missing values in raw_df.
        Appends confidence metrics to the processed_df.
        """
        logger.info("Evaluating prediction confidence...")
        result_df = processed_df.copy()
        
        # Only evaluate fields that exist in the raw dataframe structure
        fields_to_check = [f for f in self.CRITICAL_FIELDS if f in raw_df.columns]
        total_fields = len(fields_to_check)
        
        if total_fields == 0:
            logger.warning("No critical fields found for confidence evaluation.")
            result_df['confidence_score'] = 1.0
            result_df['fallback_status'] = "APPROVED"
            return result_df
            
        confidence_scores = []
        statuses = []
        
        for idx, row in raw_df.iterrows():
            # Count missing values in critical fields
            missing_count = row[fields_to_check].isna().sum()
            
            # Pass to our governance fallback logic
            fallback_result = assess_data_completeness(missing_fields=missing_count, total_fields=total_fields)
            
            score = (total_fields - missing_count) / total_fields
            confidence_scores.append(score)
            statuses.append(fallback_result.status.value)
            
        result_df['confidence_score'] = confidence_scores
        result_df['fallback_status'] = statuses
        
        return result_df
