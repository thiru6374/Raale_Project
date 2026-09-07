# Neighbourhood Heat-Risk Communication and Response Planner

A complete, AI-assisted decision-support system for district-level public health outreach planning, targeting high-risk populations during heat events in Chennai, Tamil Nadu.

---

## Problem Statement

Generic public advisories are ineffective because every neighbourhood differs in temperature exposure, green cover, healthcare access, population vulnerability, and service capacity. Heat illness disproportionately affects mobile workers, elderly residents, and communities with poor service access — exactly the groups least likely to be reached by a generic city-wide alert.

## Solution

A neighbourhood-specific, multi-objective outreach planning system that:
- Identifies **which** neighbourhoods are high-risk and **why**
- Selects the **best** outreach targets given real capacity constraints
- Ensures **fairness** across population groups
- Compares results against a simple **baseline**
- Provides **defensible evidence** for every recommendation
- Supports **human override** with complete audit logging

---

## Features

| Phase | Feature |
|-------|---------|
| Phase 1 | Configuration, logging, utilities, core models |
| Phase 2 | Synthetic data generation, schema validation, data quality reports |
| Phase 3 | Preprocessing, outlier handling, missing value imputation, feature engineering |
| Phase 4 | Heat-risk scoring, confidence assessment, safe fallback, baseline model, multi-objective MIP optimization, fairness auditing, communication recommendations, human override, audit logging |
| Phase 5 | Experiment runner, strategy comparison, failure mode analysis, stakeholder validation, evidence generation |
| Phase 6 | System health validation, executive dashboard, end-to-end integration test, reproducibility, technical documentation |
| Phase 7 | Explainability (Risk, Recommendations, Decision Traces), Monitoring (Data Quality, Fairness), Governance (Lineage) |
| Phase 8 | Operational Readiness, Scenario Simulation Engine, Release Hardening, E2E Testing, Release Readiness UI |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.9+ |
| UI | Streamlit |
| Optimization | PuLP (Mixed-Integer Programming) |
| Data | Pandas, NumPy |
| Validation | Pydantic v2 |
| Configuration | pydantic-settings |
| Visualization | Plotly Express |
| Testing | Pytest |
| Logging | Python logging (loguru-style) |

---

## Project Architecture

```
neighbourhood-heat-risk-planner/
│
├── app/                          # Streamlit application
│   ├── main.py                   # Final Executive Dashboard (landing page)
│   └── pages/
│       ├── baseline.py           # Baseline strategy analysis
│       ├── dashboard.py          # Data pipeline dashboard
│       ├── experiment_evaluation.py  # Phase 5 experiment runner
│       ├── evidence_report.py    # Evidence reports
│       ├── failure_analysis.py   # Failure mode testing
│       ├── fairness_analysis.py  # Fairness auditing
│       ├── outreach_planner.py   # Outreach plan + human override
│       ├── override_audit.py     # Audit log viewer
│       ├── risk_map.py           # Interactive risk map
│       ├── stakeholder_validation.py  # Feedback collection
│       └── system_health.py      # Phase 6 system health check
│
├── src/                          # Business logic
│   ├── config/settings.py        # Centralised configuration
│   ├── data/                     # Phase 2: data generation & ingestion
│   ├── features/                 # Phase 3: feature engineering
│   ├── risk/                     # Phase 4: risk scoring, confidence, baseline
│   ├── optimisation/             # Phase 4: MIP planner, objective functions
│   ├── fairness/                 # Phase 4: fairness auditing
│   ├── communication/            # Phase 4: message generation
│   ├── governance/               # Phase 4: fallback, overrides, audit
│   ├── evaluation/               # Phase 5: experiments, failure analysis, evidence
│   ├── services/                 # Application services (pipeline, state, health)
│   └── validation/               # Phase 6: system validator
│
├── data/
│   ├── raw/                      # Raw generated data
│   ├── processed/                # Canonical preprocessed CSV
│   ├── results/baseline/         # Baseline model outputs
│   ├── experiments/              # Experiment evidence reports
│   └── feedback/                 # Stakeholder JSONL feedback
│
├── tests/                        # Pytest test suite
├── docs/                         # Documentation
├── notebooks/                    # Jupyter notebooks
├── logs/                         # Application logs + audit trail
├── requirements.txt
└── Launch App.bat                # One-click startup script
```

---

## Installation

### Prerequisites
- Python 3.9 or later
- Windows OS (for `Launch App.bat`)
- Internet connection for map tiles

### Setup

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the Application

**Easiest method:**

```
Double-click Launch App.bat
```

The bat file will:
1. Activate the virtual environment
2. Kill any previous Streamlit instances on the port
3. Set the `PYTHONPATH` correctly
4. Start Streamlit and open the browser

**Manual method:**

```powershell
venv\Scripts\activate
streamlit run app/main.py
```

---

## Navigating the Application

| Page | Description |
|------|-------------|
| **Executive Dashboard** (home) | KPIs, risk map, attention alerts, strategy comparison |
| **Risk Map** | Interactive neighbourhood map with filters |
| **Outreach Planner** | Full outreach table, human override controls |
| **Baseline Analysis** | Temperature-only baseline model outputs |
| **Experiment & Evaluation** | Phase 5 strategy comparison experiments |
| **Fairness Analysis** | Population group coverage parity analysis |
| **Failure Analysis** | Simulate 5 failure modes |
| **Evidence Report** | Saved experiment reports |
| **Stakeholder Validation** | Submit and view stakeholder feedback |
| **Override Audit** | Full audit log of manual overrides |
| **Decision Explainability** | Transparent plain-language decision breakdown |
| **System Monitoring** | Operational monitoring of pipeline health |
| **Data Lineage & Governance** | Dataset tracking and continuous improvement loop |
| **Scenario Simulation** | Stress-test the system with what-if scenarios |
| **Release Readiness** | Pre-flight validation checks |
| **System Health** | Phase 1-6 pass/fail status |

---

## Running Tests

```powershell
venv\Scripts\activate

# All tests
pytest tests/ -v

# End-to-end only
pytest tests/test_end_to_end.py -v

# Phase 5 evaluation tests
pytest tests/test_evaluation.py tests/test_failure_modes.py -v
```

---

## Configuration

All settings are centralised in `src/config/settings.py` and can be overridden via `.env` file:

```ini
# .env (copy from .env.example)
RANDOM_SEED=42
NUMBER_OF_TEAMS=5
MAXIMUM_VISITS_PER_TEAM=10
OPTIMIZATION_STRATEGY=COVERAGE_FOCUSED
MAXIMUM_COVERAGE_GAP=0.1
```

---

## Known Limitations

1. **Synthetic Data:** All data is synthetically generated for Chennai. Real deployment requires live data pipelines.
2. **Map Accuracy:** Coordinates are randomly generated within Chennai's bounding box. A real deployment needs actual neighbourhood centroid data.
3. **Optimization Speed:** The MIP solver is not production-optimized for very large inputs (>10,000 records). Approximation techniques may be needed at scale.
4. **Reproducibility:** Results are reproducible with a fixed `RANDOM_SEED`. Different seeds produce different synthetic datasets.

---

## License

This project is for academic and research demonstration purposes.
