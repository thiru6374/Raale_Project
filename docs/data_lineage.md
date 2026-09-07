# Data Lineage Documentation

## System: Neighbourhood Heat-Risk Communication and Response Planner

This document traces every important output back to its exact data source.

---

## 1. Risk Map Output

```
Risk Map (per neighbourhood risk category + coordinates)
    ← app/pages/risk_map.py
    ← AppState.get_pipeline_results()
    ← pipeline_service.PipelineService.run_full_pipeline()
        ← MultiFactorRiskModel.calculate_risk(featured_df)
            ← FeatureEngineer.generate_features(processed_df)
                ← DataPreprocessor.process_dataframe(valid_df)
                    ← load_synthetic_data() → SyntheticDataProvider.fetch_data()
                        ← SyntheticDataGenerator(seed=settings.random_seed)
```

---

## 2. Outreach Recommendations

```
Outreach Plan (selected_for_outreach, outreach_priority, localised_advisory)
    ← app/pages/outreach_planner.py
    ← AppState.get_pipeline_results()
    ← MessageGenerator.generate_messages(planned_df)
        ← OutreachPlanner.plan_outreach(confident_df, strategy=...)
            ← build_objective_function(strategy=settings.optimization_strategy)
            ← Constraints: settings.number_of_teams × settings.maximum_visits_per_team
            ← Fairness: settings.maximum_coverage_gap per group
            ← confident_df ← ConfidenceEvaluator.evaluate(raw_df, risk_df)
                ← MultiFactorRiskModel.calculate_risk(featured_df)
```

---

## 3. Baseline vs Optimized Comparison

```
Baseline Plan (baseline_selected, baseline_rank, baseline_priority)
    ← app/pages/baseline.py
    ← AppState results["baseline_results"] (BaselineRunResult object)
    ← BaselinePrioritisationModel.run()
        ← DataLoader.load_processed_dataset() (reads canonical CSV)
            ← data/processed/neighbourhood_dataset.csv
                ← DataPreprocessor.process_dataframe()

Optimized Plan (selected_for_outreach)
    ← OutreachPlanner (COVERAGE_FOCUSED or FAIRNESS_AWARE)
    
Comparison (improvement_pct)
    ← app/main.py (Executive Dashboard)
    ← Derived: optimized_coverage_pct - baseline_coverage_pct
```

---

## 4. Evidence Report

```
Evidence Report (JSON, data/experiments/EXP_*.json)
    ← app/pages/evidence_report.py
    ← EvidenceGenerator.generate_report(experiment_results)
        ← ExperimentRunner.run_comparison()
            ← PipelineService.run_full_pipeline(strategy="COVERAGE_FOCUSED")
            ← PipelineService.run_full_pipeline(strategy="FAIRNESS_AWARE")
            ← BaselinePrioritisationModel.run()
            ← calculate_evaluation_metrics(...)
```

---

## 5. Human Override

```
Updated Outreach Plan (override_applied, override_reason columns added)
    ← app/pages/outreach_planner.py
    ← OverrideManager.force_selection(...)
        ← Original: AppState.get_pipeline_results()
        ← Authorization: user_id, reason (free text)
        ← Logged: AuditLogger → logs/audit.jsonl

Override Audit View
    ← app/pages/override_audit.py
    ← AuditLogger.load_logs("logs/audit.jsonl")
```

---

## 6. System Health

```
System Health Status (HEALTHY / ATTENTION REQUIRED / FAILED)
    ← app/pages/system_health.py
    ← SystemHealthService.get_system_health()
        ← SystemValidator.validate(app_state_results)
            ← AppState.get_full_results()
            ← Checks: preprocessing_summary.json, data/experiments/, data/feedback/
```

---

## 7. Stakeholder Feedback

```
Aggregate Feedback Metrics (avg clarity, usefulness, trust)
    ← app/pages/stakeholder_validation.py
    ← StakeholderFeedbackManager.get_aggregated_metrics()
        ← data/feedback/feedback.jsonl (JSONL, appended per submission)
```

---

## 8. Fairness Analysis

```
Fairness Audit (coverage parity gaps per group)
    ← app/pages/fairness_analysis.py
    ← AppState.get_fairness_warnings()
    ← FairnessAuditor.audit_plan(planned_df)
        ← Groups: group_mobile, group_low_service_access
        ← Threshold: settings.maximum_coverage_gap = 0.1
        ← planned_df ← OutreachPlanner
```

---

## Column Schema Reference (pipeline_results DataFrame)

| Column | Source Phase | Description |
|--------|-------------|-------------|
| `neighbourhood_id` | Phase 2 | Unique neighbourhood identifier |
| `neighbourhood_name` | Phase 2 | Human-readable name |
| `district` | Phase 2 | Chennai district |
| `latitude`, `longitude` | Phase 2 | Spatial coordinates |
| `temperature_c` | Phase 2 | Raw temperature reading |
| `built_density` | Phase 2 | Built area density |
| `green_cover_percent` | Phase 2 | Green cover fraction |
| `healthcare_distance_km` | Phase 2 | Distance to nearest HC |
| `vulnerability_index` | Phase 2 | Composite vulnerability score |
| `group_mobile` | Phase 2 | Mobile population flag |
| `group_low_service_access` | Phase 2 | Low service access flag |
| `multi_factor_risk_score` | Phase 4 | Composite weighted risk score |
| `multi_factor_risk_category` | Phase 4 | EXTREME / HIGH / MODERATE / LOW |
| `confidence_score` | Phase 4 | Data completeness ratio (0–1) |
| `fallback_status` | Phase 4 | APPROVED / MANUAL_REVIEW / UNTRUSTED |
| `selected_for_outreach` | Phase 4 | Boolean: selected by MIP optimizer |
| `outreach_priority` | Phase 4 | PRIMARY_OUTREACH / WAITLIST_HIGH_RISK / etc |
| `localised_advisory` | Phase 4 | Human-readable communication message |
| `recommended_action` | Phase 4 | Action string for outreach team |
