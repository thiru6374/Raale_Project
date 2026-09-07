import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple

from src.utils.logger import get_logger
from src.utils.helpers import safe_write_json
from src.config.settings import settings
from src.data.loader import DataLoader
from src.data.quality import DataQualityAssessor
from src.data.contracts import PreprocessingResult, PreprocessingMetadata
from src.data.validation import DataQualityStatus, NeighbourhoodData

logger = get_logger("preprocessing")

class DataPreprocessor:
    """Master orchestrator for the Preprocessing Pipeline."""

    def __init__(self):
        self.loader = DataLoader()
        self.assessor = DataQualityAssessor()

    def run_pipeline(self) -> PreprocessingResult:
        """Executes the 15-step preprocessing pipeline."""
        logger.info("Starting Preprocessing Pipeline...")
        
        # 1. Load Datasets
        unified_df = self.loader.load_raw_unified()
        domain_dfs = self.loader.load_raw_domain_files()
        metadata_json = self.loader.load_raw_metadata() or {}
        
        # Determine Integration Strategy
        if domain_dfs.get("temperature") is not None and domain_dfs.get("built_environment") is not None:
            logger.info("Domain datasets detected. Proceeding with Safe Integration.")
            merged_df = self._integrate_domain_datasets(domain_dfs)
            # Fetch base identity from unified (or we can just use the merged if it has identity)
            # To ensure identity fields are present, we'll merge identity fields from unified.
            if unified_df is not None:
                id_cols = ["neighbourhood_id", "neighbourhood_name", "district", "latitude", "longitude"]
                identity = unified_df[id_cols].drop_duplicates()
                merged_df = pd.merge(identity, merged_df, on="neighbourhood_id", how="inner")
        elif unified_df is not None:
            logger.info("Using unified dataset as primary source.")
            merged_df = unified_df.copy()
        else:
            logger.error("No raw data found!")
            return self._build_failed_result("No raw data found.")
            
        records_input = len(merged_df)
            
        # 2-3. Temperature Aggregation (if needed)
        if "observation_date" in merged_df.columns:
            merged_df = self._aggregate_temperature(merged_df)
            
        records_after_agg = len(merged_df)
            
        # 4-5. Quality Assessment
        missing_report = self.assessor.assess_missing_data(merged_df)
        outlier_report = self.assessor.detect_outliers(merged_df)
        
        # Evaluate Overall Status
        status = DataQualityStatus.APPROVED
        if missing_report.critical_missing_fields > 0 or outlier_report.total_invalid_values > 10:
            status = DataQualityStatus.MANUAL_REVIEW
        elif missing_report.warning_missing_fields > 0 or outlier_report.total_invalid_values > 0:
            status = DataQualityStatus.WARNING
            
        # 6-8. Safe Cleaning & Transformation
        processed_df, missing_handled = self._handle_missing_data(merged_df, missing_report)
        processed_df = self._handle_outliers(processed_df, outlier_report)
        processed_df = self._standardise_formats(processed_df)
        
        # 9. Save Canonical Dataset
        self.loader.save_processed_dataset(processed_df)
        
        # 10. Generate Output Contracts
        records_output = len(processed_df)
        
        meta = PreprocessingMetadata(
            dataset_version=metadata_json.get("dataset_version", "unknown"),
            preprocessing_version=settings.preprocessing_version,
            source_metadata=metadata_json
        )
        
        result = PreprocessingResult(
            status=status,
            records_input=records_input,
            records_output=records_output,
            records_removed=records_input - records_output, # Ignoring aggregation reduction as removal
            missing_values_handled=missing_handled,
            outliers_detected=outlier_report.total_outliers_detected,
            missing_data_report=missing_report,
            outlier_report=outlier_report,
            metadata=meta,
            dataset=processed_df
        )
        
        self._save_reports(result)
        logger.info(f"Pipeline completed with status: {status.value}")
        return result

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processes an in-memory DataFrame (used for integrated pipelines)."""
        # 4-5. Quality Assessment
        missing_report = self.assessor.assess_missing_data(df)
        outlier_report = self.assessor.detect_outliers(df)
        
        # 6-8. Safe Cleaning & Transformation
        processed_df, _ = self._handle_missing_data(df, missing_report)
        processed_df = self._handle_outliers(processed_df, outlier_report)
        processed_df = self._standardise_formats(processed_df)
        
        # Save Canonical Dataset
        self.loader.save_processed_dataset(processed_df)
        
        return processed_df

    def _integrate_domain_datasets(self, domain_dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Safely merges domain datasets on neighbourhood_id."""
        df_temp = domain_dfs["temperature"]
        df_built = domain_dfs["built_environment"]
        df_service = domain_dfs["service_access"]
        df_vuln = domain_dfs["vulnerability"]
        
        # Merge built, service, vulnerability (these are typically 1-to-1)
        merged = pd.merge(df_built, df_service, on="neighbourhood_id", how="outer")
        merged = pd.merge(merged, df_vuln, on="neighbourhood_id", how="outer")
        
        # Merge with temperature (may be 1-to-many, causing row multiplication)
        merged = pd.merge(merged, df_temp, on="neighbourhood_id", how="left")
        
        return merged

    def _aggregate_temperature(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates temperature records to latest observation per neighbourhood."""
        if "temperature_c" not in df.columns or "observation_date" not in df.columns:
            return df
            
        df['observation_date'] = pd.to_datetime(df['observation_date'])
        
        # Sort by date descending and take the first record per neighbourhood
        df = df.sort_values('observation_date', ascending=False)
        df = df.groupby('neighbourhood_id').first().reset_index()
        
        # Rename to latest_temperature_c to be explicit
        df = df.rename(columns={'temperature_c': 'latest_temperature_c'})
        return df

    def _handle_missing_data(self, df: pd.DataFrame, report: Any) -> Tuple[pd.DataFrame, int]:
        """Safely imputes missing values and generates _was_missing indicators."""
        df_clean = df.copy()
        handled_count = 0
        
        for col, detail in report.field_details.items():
            # Generate indicator
            indicator_col = f"{col}_was_missing"
            df_clean[indicator_col] = df_clean[col].isna()
            
            if detail.imputation_strategy == "preserve":
                continue # Do not impute (e.g. temperature)
                
            if detail.imputation_strategy == "impute_median":
                if pd.api.types.is_numeric_dtype(df_clean[col]):
                    median_val = df_clean[col].median()
                    if pd.notna(median_val):
                        df_clean[col] = df_clean[col].fillna(median_val)
                        handled_count += detail.missing_count
                        
        return df_clean, handled_count

    def _handle_outliers(self, df: pd.DataFrame, report: Any) -> pd.DataFrame:
        """Clips invalid outliers, preserves plausible extremes."""
        df_clean = df.copy()
        
        for col, detail in report.field_details.items():
            if detail.invalid_count > 0 and col in df_clean.columns:
                # Basic invalid cleaning based on domain knowledge
                if col in ["healthcare_distance_km", "travel_time_minutes", "service_time_minutes", "total_population", "mobile_population"]:
                    df_clean.loc[df_clean[col] < 0, col] = np.nan
                if col == "latest_temperature_c":
                    df_clean.loc[df_clean[col] < -10, col] = np.nan
                    
        return df_clean

    def _standardise_formats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardises types and percentage formats."""
        # Ensure percentages are uniformly 0-100 or 0-1. generated 0-100 for some, 0-1 for others.
        # We will standardise all _percent columns to 0.0-1.0 (float) for consistency in risk engine.
        for col in df.columns:
            if col.endswith("_percent"):
                if df[col].max() > 1.0:
                    df[col] = df[col] / 100.0
                    
        # Ensure ID is string
        if "neighbourhood_id" in df.columns:
            df["neighbourhood_id"] = df["neighbourhood_id"].astype(str)
            
        # Standardise booleans
        bool_cols = ["low_income_indicator", "group_mobile", "group_low_service_access"]
        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].astype(bool)
                
        return df

    def _save_reports(self, result: PreprocessingResult):
        """Saves reports to data/processed as JSON."""
        safe_write_json(result.missing_data_report.model_dump(), os.path.join(settings.processed_data_dir, "missing_data_report.json"))
        safe_write_json(result.outlier_report.model_dump(), os.path.join(settings.processed_data_dir, "outlier_report.json"))
        safe_write_json(result.metadata.model_dump(), os.path.join(settings.processed_data_dir, "preprocessing_metadata.json"))
        
        # Summary for general review
        summary = {
            "status": result.status.value,
            "records_input": result.records_input,
            "records_output": result.records_output,
            "missing_values_handled": result.missing_values_handled,
            "outliers_detected": result.outliers_detected,
            "critical_missing_fields": result.missing_data_report.critical_missing_fields
        }
        safe_write_json(summary, os.path.join(settings.processed_data_dir, "preprocessing_summary.json"))

    def _build_failed_result(self, reason: str) -> PreprocessingResult:
        return PreprocessingResult(
            status=DataQualityStatus.FAILED,
            records_input=0, records_output=0, records_removed=0, missing_values_handled=0, outliers_detected=0,
            errors=[reason],
            missing_data_report=MissingDataReport(), outlier_report=OutlierReport(),
            metadata=PreprocessingMetadata(dataset_version="none", preprocessing_version="none")
        )

if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    result = preprocessor.run_pipeline()
    
    print(f"\n{'='*60}")
    print(f"  PREPROCESSING PIPELINE SUMMARY")
    print(f"{'='*60}")
    print(f"  Input records          : {result.records_input}")
    print(f"  Missing values handled : {result.missing_values_handled}")
    print(f"  Outliers detected      : {result.outliers_detected}")
    print(f"  Processed records      : {result.records_output}")
    print(f"  Overall status         : {result.status.value}")
    print(f"{'='*60}\n")
