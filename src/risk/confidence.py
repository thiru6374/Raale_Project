import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("confidence_evaluator")

class ConfidenceEvaluator:
    """Evaluates the confidence of risk scores and determines if a fallback is required."""
    
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
        Calculates confidence score based on missing values, abnormal data, and schema compliance.
        Appends confidence metrics to the processed_df.
        """
        logger.info("Evaluating prediction confidence and failure-safes...")
        result_df = processed_df.copy()
        
        fields_to_check = [f for f in self.CRITICAL_FIELDS if f in raw_df.columns]
        total_fields = len(fields_to_check)
        
        if total_fields == 0:
            logger.warning("No critical fields found for confidence evaluation.")
            result_df['confidence_score'] = 1.0
            result_df['confidence_level'] = "HIGH CONFIDENCE"
            result_df['confidence_reason'] = "No schema fields to evaluate."
            result_df['fallback_status'] = "STANDARD"
            return result_df
            
        confidence_scores = []
        levels = []
        statuses = []
        reasons_list = []
        
        for idx, row in raw_df.iterrows():
            reasons = []
            penalties = 0.0
            
            # 1. Missing Data Completeness
            missing_count = row[fields_to_check].isna().sum()
            base_score = (total_fields - missing_count) / total_fields
            
            if missing_count > 0:
                penalties += 0.2 * missing_count
                reasons.append(f"Missing {missing_count} fields")
                
            # 2. Invalid Data (GPS)
            lat = row.get("latitude")
            lon = row.get("longitude")
            invalid_gps = False
            try:
                if pd.isna(lat) or pd.isna(lon) or not (-90 <= float(lat) <= 90) or not (-180 <= float(lon) <= 180):
                    invalid_gps = True
            except (ValueError, TypeError):
                invalid_gps = True
                
            if invalid_gps:
                penalties += 0.4
                reasons.append("Invalid/Missing GPS")
                
            # 3. Abnormal Values (Extreme Temps)
            temp = row.get("temperature_c")
            if pd.notna(temp):
                try:
                    t = float(temp)
                    if t < -20 or t > 60:
                        penalties += 0.5
                        reasons.append(f"Abnormal temp ({t}°C)")
                except (ValueError, TypeError):
                    penalties += 0.5
                    reasons.append("Invalid temp type")
            else:
                penalties += 0.5
                reasons.append("Missing temp")
                
            # 4. Final Score & Status Map
            final_score = max(0.0, base_score - penalties)
            
            if final_score >= 0.8:
                level = "HIGH CONFIDENCE"
                fallback = "STANDARD"
            elif final_score >= 0.5:
                level = "MEDIUM CONFIDENCE"
                fallback = "STANDARD"
            else:
                level = "LOW CONFIDENCE"
                fallback = "MANUAL_REVIEW"
                
            confidence_scores.append(round(final_score, 2))
            levels.append(level)
            statuses.append(fallback)
            reasons_list.append("; ".join(reasons) if reasons else "Data complete and valid")
            
        result_df['confidence_score'] = confidence_scores
        result_df['confidence_level'] = levels
        result_df['confidence_reason'] = reasons_list
        result_df['fallback_status'] = statuses
        
        # Safe-guard if the entire dataset is Low Confidence
        if result_df['fallback_status'].eq("MANUAL_REVIEW").all() and len(result_df) > 0:
            logger.error("Dataset-wide failure. All records fell back to MANUAL_REVIEW.")
            
        return result_df
