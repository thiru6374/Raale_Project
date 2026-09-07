# Project Presentation: Neighbourhood Heat-Risk Communication & Response Planner

---

## SLIDE 1 — Title

### NEIGHBOURHOOD HEAT-RISK COMMUNICATION AND RESPONSE PLANNER
**AI-Assisted Decision Support for Targeted, Timely, and Fair Neighbourhood Outreach**

Chennai, Tamil Nadu

---

## SLIDE 2 — Problem Statement

### The Problem: One Size Fits Nobody

During heat events, city authorities issue **generic public advisories**.

These advisories assume all neighbourhoods are the same.

**They are not.**

Neighbourhoods in Chennai differ dramatically in:
- **Temperature exposure** — some areas reach 41°C while others stay below 35°C
- **Built environment** — impervious surfaces trap heat; green cover cools
- **Healthcare access** — some areas have hospitals nearby; others are 8–12 km away
- **Vulnerability** — elderly residents, low-income households, and mobile workers face different risks
- **Population size** — outreach capacity is limited; choices must be prioritized

**The result:** High-risk populations receive the same alert as low-risk ones — and the most vulnerable may receive nothing targeted at all.

---

## SLIDE 3 — Why Generic Advisories Fail

| Problem | Consequence |
|---------|-------------|
| One message for all | Irrelevant to specific neighbourhoods |
| No risk prioritization | Limited outreach resources wasted |
| No capacity awareness | Overbooking or undercoverage |
| No fairness analysis | Vulnerable groups systematically underserved |
| No defensible evidence | Decisions cannot be audited or explained |
| No human override path | Planners cannot correct automated recommendations |

---

## SLIDE 4 — Proposed Solution

### A Neighbourhood-Specific Multi-Objective Outreach Planner

The system:

1. **Identifies** which neighbourhoods are high risk and why
2. **Prioritizes** outreach using a multi-factor risk model
3. **Optimizes** the selection given real operational constraints
4. **Ensures fairness** across mobile workers and low-service-access communities
5. **Compares** performance against a temperature-only baseline
6. **Provides defensible evidence** for every recommendation
7. **Supports human override** with complete audit logging
8. **Validates** through stakeholder feedback

---

## SLIDE 5 — End-to-End Architecture

```
[Phase 1: Foundation]
Configuration · Logging · Utilities · Core Models
        ↓
[Phase 2: Data Generation & Ingestion]
Synthetic Chennai Neighbourhoods · Schema Validation · Data Quality Reports
        ↓
[Phase 3: Preprocessing & Feature Engineering]
Missing Value Imputation · Outlier Handling · Normalisation · Composite Features
        ↓
[Phase 4: Risk, Planning, Fairness & Governance]
Multi-Factor Risk Scoring → Confidence Assessment → Safe Fallback
Baseline Model (temperature-only) → MIP Optimization → Fairness Audit
Communication Recommendations → Human Override → Audit Log
        ↓
[Phase 5: Experimentation & Evaluation]
Strategy Comparison · Failure Mode Analysis · Stakeholder Validation · Evidence
        ↓
[Phase 6: System Integration & Deployment]
System Health Validation · Executive Dashboard · Documentation
```

---

## SLIDE 6 — Data Inputs

| Indicator Group | Features |
|----------------|---------|
| **Temperature** | temperature_c, heat_index, latest_temperature_c |
| **Built Environment** | built_density, green_cover_percent, impervious_surface_percent |
| **Service Access** | healthcare_distance_km, healthcare_capacity |
| **Vulnerability** | vulnerability_index, elderly_population_percent, low_income_indicator |
| **Population Groups** | group_mobile (mobile workers), group_low_service_access |
| **Operations** | mobile_population (outreach size), district |
| **Spatial** | latitude, longitude |

All data is synthetically generated at a fixed random seed (default: 42) for reproducibility.

---

## SLIDE 7 — Heat-Risk Assessment Methodology

### Multi-Factor Risk Model

**Risk Score** = weighted combination of:

| Factor | Default Weight |
|--------|---------------|
| Temperature | 40% |
| Built Environment | 20% |
| Service Access | 20% |
| Vulnerability | 20% |

**Risk Categories:**
- **EXTREME** — top risk score tier → immediate priority
- **HIGH** — second tier → priority outreach
- **MODERATE** — third tier → scheduled advisory
- **LOW** — below threshold → standard communications

**Confidence Assessment:** Based on data completeness. Missing critical fields reduce confidence.
**Safe Fallback:** Records below confidence threshold get MANUAL_REVIEW or UNTRUSTED status.

---

## SLIDE 8 — Baseline vs Optimization

### Baseline: Temperature-Only Strategy

Selects the top-N hottest neighbourhoods, regardless of:
- Population size
- Vulnerability
- Capacity
- Fairness

### Optimized: Multi-Objective MIP Planner

Maximizes a combined objective:

```
Maximize: Σ (coverage_weight × risk_score × population) + 
          Σ (fairness_weight × group_membership)

Subject to: total_selected ≤ number_of_teams × max_visits_per_team
            for each group: selection_rate_difference ≤ max_coverage_gap
```

**Strategies:**
- **COVERAGE_FOCUSED** — maximize total high-risk population reached
- **BALANCED** — equal weight to coverage and fairness
- **FAIRNESS_AWARE** — prioritize equity across population groups

---

## SLIDE 9 — Coverage vs Fairness Trade-off

| Metric | COVERAGE_FOCUSED | FAIRNESS_AWARE |
|--------|-----------------|----------------|
| High-Risk Coverage | Higher | Slightly lower |
| Mobile Group Coverage | May be lower | More equitable |
| Low-Service-Access Coverage | May vary | Explicitly prioritized |
| Capacity Utilization | Full | Full |

**Key insight:** The COVERAGE_FOCUSED strategy produces the maximum total coverage in aggregate. The FAIRNESS_AWARE strategy sacrifices a small amount of aggregate coverage to ensure that underserved groups receive proportional attention.

**District planners can choose which strategy best fits their operational mandate.**

---

## SLIDE 10 — Capacity and Scheduling Constraints

### Operational Reality

The system enforces real-world constraints:

| Constraint | Default Value | Configurable |
|-----------|--------------|-------------|
| Number of outreach teams | 5 | Yes |
| Max visits per team per day | 10 | Yes |
| Total daily capacity | 50 | Derived |
| Max coverage gap per group | 10% | Yes |
| Working hours | 8 hours/day | Yes |

**If capacity is exhausted:**
- The optimizer selects the highest-priority uncovered neighbourhoods first
- Remaining high-risk neighbourhoods appear as WAITLIST_HIGH_RISK
- The system alerts the dashboard: "X high-risk neighbourhoods remain uncovered"

---

## SLIDE 11 — Failure Modes and Safe Fallback

### 5 Tested Failure Scenarios

| Failure | Detection | Response |
|---------|-----------|---------|
| Missing Temperature | Validation → baseline_status = DATA_INSUFFICIENT | Excluded from baseline; confidence reduced |
| Missing Coordinates | Map rendering filter | Excluded from map only; outreach unaffected |
| Low Capacity | Capacity constraint detected | All high-risk uncovered flagged on dashboard |
| Untrusted Data | >40% critical fields missing | UNTRUSTED status; fallback to manual review |
| Fairness Imbalance | FairnessAuditor detects >10% gap | Dashboard warning; FAIRNESS ANALYSIS page alert |

**Additional scenarios tested:**
- Missing audit log → auto-created
- Missing feedback directory → auto-created
- Corrupted input → Pydantic validation rejects invalid records; clean records continue

---

## SLIDE 12 — Stakeholder Validation

Stakeholders (District Planners, Outreach Coordinators, Health Officers) submit structured feedback across 6 dimensions:

| Dimension | Scale |
|-----------|-------|
| Prioritization Clarity | 1-5 |
| Recommendation Usefulness | 1-5 |
| Capacity Realism | 1-5 |
| Fairness Understanding | 1-5 |
| Override Clarity | 1-5 |
| Recommendation Trust | 1-5 |

Feedback is stored in `data/feedback/feedback.jsonl` (JSONL format, append-only, no overwrite).
Aggregate metrics are computed on demand from live data.

---

## SLIDE 13 — Final Dashboard and Evidence

### Executive Dashboard (app/main.py)

Designed for district planners and public health officials.

Sections:
1. System status badge (HEALTHY / ATTENTION REQUIRED)
2. KPI cards: High-Risk Areas, Areas Reached, Coverage %, Improvement, Fairness Status, Trust
3. Automatic attention alerts (uncovered areas, capacity limits, fairness gaps)
4. Interactive risk map
5. Baseline vs optimized performance table
6. Coverage vs fairness trade-off
7. Highest-priority recommended actions
8. Fairness snapshot
9. System trust and data quality
10. Stakeholder validation summary
11. System health (Phase 1–6 pass/fail)

### Evidence Reports

Saved as `data/experiments/EXP_*.json` — structured, auditable, machine-readable.

---

## SLIDE 14 — Measured Results (Typical Synthetic Run)

> Note: All results are from synthetic data with seed=42. Values vary by run configuration.

| Metric | Typical Value |
|--------|--------------|
| Total Neighbourhoods | 100 |
| High-Risk Identified | ~25–35 |
| Baseline High-Risk Coverage | ~30–40% |
| Optimized Coverage | ~60–80% |
| Coverage Improvement | ~20–40 percentage points |
| Capacity Utilization | 100% (50/50 slots) |
| Fairness Gap | <10% (within threshold) |
| Data Quality | ~95% (5% missing rate) |
| Confidence Score (avg) | ~0.92 |

---

## SLIDE 15 — Limitations, Future Work, and Conclusion

### Known Limitations

1. **Synthetic Data** — Real deployment requires live data feeds (weather APIs, GIS data, health service databases)
2. **Coordinate Accuracy** — Random generation within bounding box; real coordinates needed for production
3. **Solver Performance** — PuLP CBC solver is adequate for ≤1000 records; large-scale deployment needs a production solver (Gurobi, CPLEX)
4. **No Scheduling Constraints** — Current version plans for a single day; multi-day scheduling is future work
5. **Feedback Quality** — Stakeholder validation is voluntary; response bias possible

### Future Work

- Live weather API integration
- Actual Chennai GIS neighbourhood polygon data
- Multi-day scheduling optimization
- Mobile app for field coordinators
- Real-time dashboard (not just per-session)
- Explainability layer (SHAP values for risk scores)

### Conclusion

The Neighbourhood Heat-Risk Communication and Response Planner demonstrates that:
- **Targeted, neighbourhood-specific outreach is technically feasible**
- **Multi-objective optimization significantly outperforms temperature-only baselines**
- **Fairness can be explicitly enforced in operational planning**
- **Defensible evidence and audit trails enable accountable decisions**
- **Human oversight remains central — the system augments, not replaces, planner judgment**
