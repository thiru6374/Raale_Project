import os
import json
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("stakeholder_validation")

class StakeholderFeedbackManager:
    """
    Manages the storage and retrieval of stakeholder validation feedback.
    Saves data to data/feedback/feedback.jsonl
    """
    
    def __init__(self, feedback_dir: str = "data/feedback"):
        self.feedback_dir = feedback_dir
        self.feedback_file = os.path.join(feedback_dir, "feedback.jsonl")
        self._ensure_directory()
        
    def _ensure_directory(self):
        try:
            if not os.path.exists(self.feedback_dir):
                os.makedirs(self.feedback_dir)
        except Exception as e:
            logger.error(f"Failed to create feedback directory {self.feedback_dir}: {e}")
            
    def save_feedback(self, feedback_record: Dict[str, Any]) -> bool:
        """
        Saves a single feedback record to the JSONL file.
        """
        try:
            feedback_record["timestamp"] = datetime.now().isoformat()
            
            with open(self.feedback_file, "a") as f:
                f.write(json.dumps(feedback_record) + "\n")
            logger.info("Stakeholder feedback saved successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to save stakeholder feedback: {e}")
            return False
            
    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """
        Retrieves all stored feedback records.
        Returns an empty list if file doesn't exist or fails to read.
        """
        records = []
        if not os.path.exists(self.feedback_file):
            return records
            
        try:
            with open(self.feedback_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped invalid JSON line in feedback: {line}")
        except Exception as e:
            logger.error(f"Failed to read stakeholder feedback: {e}")
            
        return records
        
    def get_aggregated_metrics(self) -> Dict[str, float]:
        """
        Calculates average scores across all feedback.
        """
        records = self.get_all_feedback()
        if not records:
            return {}
            
        df = pd.DataFrame(records)
        
        metrics = {}
        score_columns = [
            "prioritization_clarity", 
            "recommendation_usefulness",
            "capacity_realism",
            "fairness_understanding",
            "override_clarity",
            "recommendation_trust"
        ]
        
        for col in score_columns:
            if col in df.columns:
                # Convert to numeric, ignoring invalid strings
                series = pd.to_numeric(df[col], errors='coerce').dropna()
                if not series.empty:
                    metrics[f"avg_{col}"] = float(series.mean())
                else:
                    metrics[f"avg_{col}"] = 0.0
                    
        metrics["total_responses"] = len(records)
        return metrics
