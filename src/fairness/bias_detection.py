import pandas as pd
from typing import List, Dict, Any
from src.utils.logger import get_logger
from src.config.settings import settings
from src.fairness.metrics import calculate_fairness_metrics

logger = get_logger("fairness_auditor")

class FairnessAuditor:
    """Audits outreach plans for systemic bias against vulnerable groups."""
    
    def __init__(self, target_groups: List[str] = None):
        if target_groups is None:
            self.target_groups = ['group_mobile', 'group_low_service_access']
        else:
            self.target_groups = target_groups
            
    def generate_fairness_report(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Generates a detailed fairness report with all mathematical metrics.
        """
        report = []
        for group in self.target_groups:
            if group in df.columns:
                metrics = calculate_fairness_metrics(df, group)
                report.append(metrics)
        return report
            
    def audit_plan(self, df: pd.DataFrame) -> List[Dict]:
        """
        Runs coverage parity checks on the outreach plan.
        Returns a list of warnings if the gap exceeds the allowed threshold.
        """
        logger.info(f"Auditing fairness for groups: {self.target_groups}")
        warnings = []
        
        for group in self.target_groups:
            if group not in df.columns:
                logger.warning(f"Group '{group}' not found in data. Skipping audit.")
                continue
                
            metrics = calculate_fairness_metrics(df, group)
            
            # If the group doesn't exist in this dataset, skip
            if metrics['sample_size'] == 0:
                continue
                
            global_cov = metrics['overall_coverage']
            group_cov = metrics['group_coverage']
            coverage_gap = group_cov - global_cov  # Original logic expected positive = underserved? Wait.
            # The original logic used global_cov - group_cov for gap. 
            # If group < global, gap is positive.
            legacy_gap = global_cov - group_cov
            
            # Check against thresholds from settings
            if legacy_gap > settings.maximum_coverage_gap:
                warning_msg = (f"Bias Warning: '{group}' is underserved. "
                               f"Global coverage is {global_cov:.1%}, but group coverage is {group_cov:.1%}. "
                               f"Gap: {legacy_gap:.1%} (Exceeds {settings.maximum_coverage_gap:.1%})")
                logger.warning(warning_msg)
                warnings.append({
                    "group": group,
                    "global_coverage": global_cov,
                    "group_coverage": group_cov,
                    "coverage_gap": legacy_gap,
                    "message": warning_msg
                })
            else:
                logger.info(f"Fairness check passed for '{group}'. Gap: {legacy_gap:.1%}")
                
            # Geographic Bias Check
            if "is_valid_geo" in df.columns:
                invalid_geo_df = df[~df["is_valid_geo"]]
                if not invalid_geo_df.empty:
                    global_invalid_rate = len(invalid_geo_df) / len(df)
                    group_df = df[df[group] == True]
                    if not group_df.empty:
                        group_invalid_rate = len(group_df[~group_df["is_valid_geo"]]) / len(group_df)
                        geo_gap = group_invalid_rate - global_invalid_rate
                        
                        if geo_gap > 0.05: # Arbitrary threshold for geographic bias
                            warning_msg = (f"Geographic Bias Warning: '{group}' is disproportionately missing valid coordinates. "
                                           f"Global invalid rate is {global_invalid_rate:.1%}, but group invalid rate is {group_invalid_rate:.1%}.")
                            logger.warning(warning_msg)
                            warnings.append({
                                "group": group,
                                "type": "GEOGRAPHIC_BIAS",
                                "global_invalid_rate": global_invalid_rate,
                                "group_invalid_rate": group_invalid_rate,
                                "message": warning_msg
                            })
                            
        return warnings
