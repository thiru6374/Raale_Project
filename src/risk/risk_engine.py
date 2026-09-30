import pandas as pd
import numpy as np
import json
from pydantic import BaseModel, field_validator
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("multi_factor_risk")

class RiskModelWeights(BaseModel):
    temperature: float
    environmental: float
    vulnerability: float
    service_access: float
    mobility: float
    
    @field_validator('*')
    @classmethod
    def check_weights(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Weight must be between 0 and 1. Got {v}")
        return v
        
    def validate_sum(self):
        total = self.temperature + self.environmental + self.vulnerability + self.service_access + self.mobility
        if not np.isclose(total, 1.0, atol=1e-5):
            raise ValueError(f"Weights must sum to 1.0. Current sum is {total}")

class MultiFactorRiskModel:
    """
    Calculates the weighted multi-factor heat-risk score using a formal mathematical model.
    """
    MODEL_VERSION = "2.0.0"
    
    def __init__(self, weights_dict=None):
        if weights_dict is None:
            # Fallback to existing settings
            weights_dict = {
                "temperature": getattr(settings, "temperature_weight", 0.3),
                "environmental": getattr(settings, "built_environment_weight", 0.2),
                "vulnerability": getattr(settings, "vulnerability_weight", 0.2),
                "service_access": getattr(settings, "service_access_weight", 0.15),
                "mobility": getattr(settings, "mobility_weight", 0.15)
            }
        
        self.weights = RiskModelWeights(**weights_dict)
        self.weights.validate_sum()
        
    def _normalize(self, series: pd.Series, invert=False) -> pd.Series:
        """Min-Max normalizes a series to [0, 1]. Inverts if required."""
        if series.isna().all():
            return pd.Series(0.0, index=series.index)
            
        series = series.astype(float)
        s_min = series.min()
        s_max = series.max()
        
        if np.isclose(s_min, s_max):
            normalized = pd.Series(0.0, index=series.index)
        else:
            normalized = (series - s_min) / (s_max - s_min)
            
        if invert:
            normalized = 1.0 - normalized
            
        return normalized.clip(0.0, 1.0).fillna(0.0)
        
    def calculate_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info(f"Calculating multi-factor risk scores with formal model v{self.MODEL_VERSION}...")
        result_df = df.copy()
        
        # We need explainability outputs for every neighbourhood
        explainability = []
        
        # 1. Temperature Risk
        temp_col = 'heat_index' if 'heat_index' in result_df.columns else ('latest_temperature_c' if 'latest_temperature_c' in result_df.columns else 'temperature_c')
        if temp_col in result_df.columns:
            temp_norm = self._normalize(result_df[temp_col])
            temp_raw = result_df[temp_col].fillna(0.0)
        else:
            temp_norm = pd.Series(0.0, index=result_df.index)
            temp_raw = pd.Series(0.0, index=result_df.index)
            
        # 2. Environmental Exposure (built_density, impervious_surface_percent, green_cover_percent inverted)
        env_raw_list = []
        for col, inv in [('built_density', False), ('impervious_surface_percent', False), ('green_cover_percent', True)]:
            if col in result_df.columns:
                env_raw_list.append(self._normalize(result_df[col], invert=inv))
        env_norm = pd.concat(env_raw_list, axis=1).mean(axis=1) if env_raw_list else pd.Series(0.0, index=result_df.index)
        
        # 3. Vulnerability (vulnerability_index, elderly_population_percent, low_income_indicator)
        vuln_raw_list = []
        for col in ['vulnerability_index', 'elderly_population_percent', 'low_income_indicator']:
            if col in result_df.columns:
                vuln_raw_list.append(self._normalize(result_df[col]))
        vuln_norm = pd.concat(vuln_raw_list, axis=1).mean(axis=1) if vuln_raw_list else pd.Series(0.0, index=result_df.index)
        
        # 4. Service Access Gap (healthcare_distance_km, transport_access_score inverted)
        serv_raw_list = []
        for col, inv in [('healthcare_distance_km', False), ('transport_access_score', True)]:
            if col in result_df.columns:
                serv_raw_list.append(self._normalize(result_df[col], invert=inv))
        serv_norm = pd.concat(serv_raw_list, axis=1).mean(axis=1) if serv_raw_list else pd.Series(0.0, index=result_df.index)
        
        # 5. Mobility Risk (mobile_population)
        if 'mobile_population' in result_df.columns:
            mob_norm = self._normalize(result_df['mobile_population'])
        else:
            mob_norm = pd.Series(0.0, index=result_df.index)
            
        # Calculate Risk Score
        risk_score = (
            temp_norm * self.weights.temperature +
            env_norm * self.weights.environmental +
            vuln_norm * self.weights.vulnerability +
            serv_norm * self.weights.service_access +
            mob_norm * self.weights.mobility
        ).fillna(0.0)
        
        result_df['multi_factor_risk_score'] = risk_score
        
        # Thresholds defined explicitly
        # VERY HIGH: >= 0.75, HIGH: >= 0.50, MODERATE: >= 0.25, LOW: < 0.25
        conditions = [
            (risk_score >= 0.75),
            (risk_score >= 0.50),
            (risk_score >= 0.25),
            (risk_score < 0.25)
        ]
        choices = ['VERY HIGH', 'HIGH', 'MODERATE', 'LOW']
        result_df['multi_factor_risk_category'] = np.select(conditions, choices, default='UNKNOWN')
        
        # Build explainability json string for each row
        w = self.weights
        for idx, row in result_df.iterrows():
            expl = {
                "model_version": self.MODEL_VERSION,
                "factors": {
                    "temperature": {"raw": float(temp_raw.loc[idx]), "normalized": float(temp_norm.loc[idx]), "weight": w.temperature, "contribution": float(temp_norm.loc[idx] * w.temperature)},
                    "environmental": {"normalized": float(env_norm.loc[idx]), "weight": w.environmental, "contribution": float(env_norm.loc[idx] * w.environmental)},
                    "vulnerability": {"normalized": float(vuln_norm.loc[idx]), "weight": w.vulnerability, "contribution": float(vuln_norm.loc[idx] * w.vulnerability)},
                    "service_access": {"normalized": float(serv_norm.loc[idx]), "weight": w.service_access, "contribution": float(serv_norm.loc[idx] * w.service_access)},
                    "mobility": {"normalized": float(mob_norm.loc[idx]), "weight": w.mobility, "contribution": float(mob_norm.loc[idx] * w.mobility)}
                },
                "final_score": float(risk_score.loc[idx]),
                "risk_level": result_df.loc[idx, 'multi_factor_risk_category']
            }
            explainability.append(json.dumps(expl))
            
        result_df['risk_explainability'] = explainability
        
        return result_df
        
    def sensitivity_analysis(self, df: pd.DataFrame, weight_variances: list = [-0.1, 0.0, 0.1]) -> pd.DataFrame:
        """
        Runs the risk model with variations in weights to check the robustness of the risk categories.
        Returns a DataFrame showing how many neighbourhoods changed risk categories under variance.
        """
        base_result = self.calculate_risk(df)
        base_categories = base_result['multi_factor_risk_category']
        
        sensitivity_results = []
        original_weights = self.weights.model_dump()
        
        # We vary each weight by the variances and re-normalize the others
        for factor in original_weights.keys():
            for variance in weight_variances:
                if variance == 0.0:
                    continue
                    
                new_w = original_weights.copy()
                new_w[factor] += variance
                
                # Cannot drop below 0 or above 1
                new_w[factor] = max(0.0, min(1.0, new_w[factor]))
                
                # Re-normalize other weights
                remainder = 1.0 - new_w[factor]
                other_factors_sum = sum(v for k, v in original_weights.items() if k != factor)
                
                if other_factors_sum > 0:
                    for k in new_w.keys():
                        if k != factor:
                            new_w[k] = original_weights[k] / other_factors_sum * remainder
                
                # Check for validity
                try:
                    test_model = MultiFactorRiskModel(weights_dict=new_w)
                    test_result = test_model.calculate_risk(df)
                    
                    changes = (base_categories != test_result['multi_factor_risk_category']).sum()
                    sensitivity_results.append({
                        "varied_factor": factor,
                        "variance": variance,
                        "new_weight": new_w[factor],
                        "category_changes": changes,
                        "change_percent": (changes / len(df)) * 100 if len(df) > 0 else 0
                    })
                except ValueError:
                    # Invalid weight sum due to rounding, skip
                    continue
                    
        return pd.DataFrame(sensitivity_results)
