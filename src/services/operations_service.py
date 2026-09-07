"""
src/services/operations_service.py

Centralized operational orchestration layer for .
Tracks pipeline run history and analytics.
"""
import uuid
import logging
from typing import Dict, Any, List
from datetime import datetime

from src.services.pipeline_service import PipelineService
from src.services.persistence.jsonl_store import JSONLStore
from src.services.kpi_service import KPIService

logger = logging.getLogger(__name__)

RUN_HISTORY_FILE = "data/intelligence/run_history.jsonl"

class OperationsService:
    def __init__(self, history_file: str = RUN_HISTORY_FILE):
        self.store = JSONLStore(history_file)
        
    def execute_operational_run(self, capacity: int = 10, num_records: int = 100) -> Dict[str, Any]:
        """
        Orchestrates the full pipeline and records historical execution data.
        """
        run_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        status = "IN_PROGRESS"
        
        run_record = {
            "run_id": run_id,
            "start_time": start_time.isoformat() + "Z",
            "end_time": None,
            "status": status,
            "record_count": num_records,
            "high_risk_count": 0,
            "fairness_gap": 0.0,
            "capacity_utilization": 0.0,
            "fallback_rate": 0.0,
            "error_summary": ""
        }
        
        try:
            if num_records <= 0:
                raise ValueError("No data provided for operational run.")
                
            # Execute 11 Pipeline
            pipeline_result = PipelineService.run_full_pipeline(num_records=num_records)
            
            # Extract data for history
            df_opt = pipeline_result.get("optimized_schedule")
            fairness = pipeline_result.get("fairness_analysis", {})
            
            if df_opt is not None:
                nbhds = df_opt.to_dict(orient="records")
                # Using a mock decision logic step to populate KPIs for history
                from src.services.decision_intelligence_service import DecisionIntelligenceService
                decisions = DecisionIntelligenceService.generate_final_decisions(
                    nbhds, "HEALTHY", [], run_id, "v13"
                )
                
                kpis = KPIService.calculate_kpis(
                    decisions, {}, fairness, "HEALTHY", 
                    sum(1 for d in decisions if d.get("priority") in ["CRITICAL", "HIGH"]), 
                    capacity
                )
                
                run_record["high_risk_count"] = sum(1 for d in decisions if d.get("risk_level") == "HIGH")
                run_record["fairness_gap"] = fairness.get("disparity", 0.0)
                run_record["capacity_utilization"] = kpis.get("capacity_utilization", 0.0)
                run_record["fallback_rate"] = kpis.get("fallback_rate", 0.0)
                
            status = "SUCCESS"
            
        except Exception as e:
            logger.error(f"Operational run failed: {e}")
            status = "FAILED"
            run_record["error_summary"] = str(e)
            
        finally:
            run_record["end_time"] = datetime.utcnow().isoformat() + "Z"
            run_record["status"] = status
            self.store.append(run_record)
            
        return run_record

    def get_run_history(self) -> List[Dict[str, Any]]:
        return self.store.read_all()
        
    def get_historical_trends(self) -> Dict[str, Any]:
        """Calculates trend analytics if sufficient history exists."""
        history = self.get_run_history()
        successful_runs = [r for r in history if r["status"] == "SUCCESS"]
        
        if len(successful_runs) < 2:
            return {"status": "INSUFFICIENT HISTORY", "message": "Need at least 2 successful runs for trend analysis."}
            
        latest = successful_runs[-1]
        previous = successful_runs[-2]
        
        return {
            "status": "AVAILABLE",
            "risk_trend": latest["high_risk_count"] - previous["high_risk_count"],
            "fairness_trend": latest["fairness_gap"] - previous["fairness_gap"],
            "capacity_trend": latest["capacity_utilization"] - previous["capacity_utilization"],
            "latest_run_id": latest["run_id"],
            "previous_run_id": previous["run_id"]
        }
