import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from src.config.settings import settings
from src.data.contracts import MissingDataReport, MissingDataDetail, OutlierReport, OutlierDetail
from src.utils.logger import get_logger

logger = get_logger("data_quality")

class DataQualityAssessor:
    """Detects missing values and outliers based on configuration."""

    def __init__(self):
        self.missing_warning_threshold = settings.missing_warning_threshold
        self.missing_critical_threshold = settings.missing_critical_threshold
        self.outlier_method = settings.outlier_detection_method
        self.iqr_multiplier = settings.iqr_multiplier
        self.z_score_threshold = settings.z_score_threshold

    def assess_missing_data(self, df: pd.DataFrame, id_col: str = "neighbourhood_id") -> MissingDataReport:
        """Evaluates missing data in the dataframe and classifies its severity."""
        report = MissingDataReport()
        total_records = len(df)
        if total_records == 0:
            return report

        missing_counts = df.isna().sum()
        
        for col, count in missing_counts.items():
            if count > 0:
                report.total_missing_values += int(count)
                report.fields_with_missing_data += 1
                
                missing_percentage = count / total_records
                severity = "ACCEPTABLE"
                
                if col in ["neighbourhood_id", "neighbourhood_name", "latitude", "longitude", "latest_temperature_c"]:
                    if missing_percentage > 0:
                         severity = "CRITICAL"
                elif missing_percentage >= self.missing_critical_threshold:
                    severity = "CRITICAL"
                elif missing_percentage >= self.missing_warning_threshold:
                    severity = "WARNING"
                    
                if severity == "CRITICAL":
                    report.critical_missing_fields += 1
                elif severity == "WARNING":
                    report.warning_missing_fields += 1
                
                # Determine strategy
                strategy = "impute_median"
                if col == "latest_temperature_c":
                    strategy = settings.temperature_imputation_strategy
                elif df[col].dtype in ['bool', 'object']:
                    strategy = settings.categorical_imputation_strategy
                else:
                    strategy = settings.numeric_imputation_strategy
                
                # Affected neighbourhoods
                affected_ids = []
                if id_col in df.columns:
                    affected_ids = df[df[col].isna()][id_col].dropna().astype(str).tolist()
                    
                detail = MissingDataDetail(
                    field_name=col,
                    missing_count=int(count),
                    missing_percentage=float(missing_percentage),
                    severity=severity,
                    imputation_strategy=strategy,
                    affected_neighbourhoods=affected_ids
                )
                report.field_details[col] = detail
                
        return report

    def detect_outliers(self, df: pd.DataFrame) -> OutlierReport:
        """Detects outliers using configured method (IQR or Z-Score)."""
        report = OutlierReport()
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if col in ["latitude", "longitude"]: # Skip coordinates
                continue
            
            series = df[col].dropna()
            if len(series) < 5:
                continue
                
            outliers = pd.Series([False]*len(series), index=series.index)
            
            if self.outlier_method == "iqr":
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - self.iqr_multiplier * IQR
                upper_bound = Q3 + self.iqr_multiplier * IQR
                outliers = (series < lower_bound) | (series > upper_bound)
            elif self.outlier_method == "zscore":
                mean = series.mean()
                std = series.std()
                if std > 0:
                    z_scores = (series - mean) / std
                    outliers = abs(z_scores) > self.z_score_threshold

            outlier_count = int(outliers.sum())
            if outlier_count > 0:
                report.total_outliers_detected += outlier_count
                
                # Distinguish Plausible Extremes vs Invalid (domain specific rules could be applied here)
                # For now, default all to plausible unless obviously impossible (e.g. negative distance)
                invalid_count = 0
                if col in ["healthcare_distance_km", "travel_time_minutes", "service_time_minutes", "total_population"]:
                    invalid_count = int((series[outliers] < 0).sum())
                
                if col == "latest_temperature_c":
                    # Temperatures below -10 in Chennai are invalid, > 50 extreme
                    invalid_count = int((series[outliers] < -10).sum())
                    
                plausible_count = outlier_count - invalid_count
                report.total_plausible_extremes += plausible_count
                report.total_invalid_values += invalid_count
                
                strategy = "preserve" if settings.preserve_plausible_extremes else "clip"
                if invalid_count > 0:
                     strategy = "mixed (invalid to NaN, plausible preserved)"
                
                detail = OutlierDetail(
                    field_name=col,
                    outlier_count=outlier_count,
                    plausible_extremes_count=plausible_count,
                    invalid_count=invalid_count,
                    strategy_applied=strategy
                )
                report.field_details[col] = detail

        return report
