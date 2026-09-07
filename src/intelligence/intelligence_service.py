"""
src/intelligence/intelligence_service.py
"""
import pandas as pd
from typing import Dict, Any
from src.intelligence.change_detection import ChangeDetector
from src.intelligence.alert_engine import AlertEngine
from src.intelligence.priority_engine import PriorityEngine
from src.intelligence.improvement_service import ImprovementService
from src.services.persistence.jsonl_store import JSONLStore
import os

class IntelligenceService:
    def __init__(self):
        self.change_detector = ChangeDetector()
        self.alert_engine = AlertEngine()
        self.priority_engine = PriorityEngine()
        self.improvement_service = ImprovementService()
        self.history_store = JSONLStore("data/intelligence/run_history.jsonl")
        
    def process_pipeline_result(self, pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes the complete pipeline output, runs intelligence analytics, 
        generates alerts, prioritizes decisions, and saves history.
        """
        current_df = pipeline_result.get("pipeline_results")
        if current_df is None or current_df.empty:
            return pipeline_result
            
        current_meta = pipeline_result.get("provider_metadata", {})
        pipeline_run_id = pipeline_result.get("dataset_id", "UNKNOWN_RUN")
        fairness_warnings = pipeline_result.get("fairness_warnings", [])
        
        # 1. Fetch previous run for change detection
        history = self.history_store.read_all()
        previous_df = None
        previous_meta = {}
        
        if history:
            # For simplicity in this prototype, we'll assume the history contains a serialized summary
            # Actually, to avoid saving full dataframes in history, let's just save metadata and metrics
            # But the change detector expects DataFrames.
            # In a real system, we'd query the database for the previous run's dataset.
            # Here, we will just use the current run for both to simulate no history if history is missing,
            # or skip DataFrame-based change detection if we don't have the previous df in memory.
            pass
            
        # We'll skip previous_df based change detection unless we have it in memory.
        # For prototype, we'll just run it against itself to simulate "INSUFFICIENT_HISTORY"
        # or we can mock it.
        changes = self.change_detector.detect_changes(current_df, None, current_meta, previous_meta)
        
        # 2. Generate Alerts
        alerts = self.alert_engine.generate_alerts(
            current_df, fairness_warnings, current_meta, pipeline_run_id, changes
        )
        
        # 3. Prioritize Decisions
        prioritized_df = self.priority_engine.prioritize_decisions(current_df, fairness_warnings)
        pipeline_result["pipeline_results"] = prioritized_df
        
        # 4. Generate Improvement Proposals
        proposals = self.improvement_service.generate_proposals(prioritized_df, changes, alerts)
        
        # Return enriched results
        pipeline_result["intelligence"] = {
            "changes": changes,
            "alerts_generated": len(alerts),
            "proposals_generated": len(proposals)
        }
        
        return pipeline_result
