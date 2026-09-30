"""
app/pages/methodology.py — Complete System Methodology

Documents the risk model, optimization, constraints, fairness,
confidence, fallback, and limitations for full transparency.
All descriptions match the actual implementation.
"""
import streamlit as st
from app.components.layout import apply_global_styles, page_header
from app.components.sidebar import render_sidebar
from src.config.settings import settings


apply_global_styles()
render_sidebar()

page_header(" System Methodology", "Transparent documentation of every component that drives the recommendations.", icon=":material/article:")

st.markdown("""
This page documents exactly how the Neighbourhood Heat-Risk Outreach Planner works.
All values, formulas, and thresholds shown here correspond directly to the live system implementation.
""")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 1. RISK MODEL
# ══════════════════════════════════════════════════════════════════════════════
st.header("1 · Risk Model (v2.0.0)")

st.markdown("""
### Formal Mathematical Definition

The composite heat-risk score **R** for each neighbourhood is:

> **R = α·T + β·E + γ·V + δ·S + ε·M**

| Symbol | Factor | Description | Normalization |
|--------|--------|-------------|---------------|
| **T** | Temperature Exposure | Heat index or ambient temperature | Min-Max to [0,1] |
| **E** | Environmental Exposure | Built density, impervious surface, green cover (inverted) | Average of normalized sub-components |
| **V** | Vulnerability | Vulnerability index, elderly %, low-income indicator | Average of normalized sub-components |
| **S** | Service Access Gap | Healthcare distance (km), transport access (inverted) | Average of normalized sub-components |
| **M** | Mobility Risk | Mobile/migrant worker population share | Min-Max to [0,1] |

### Risk Category Thresholds

| Category | Score Range |
|----------|-------------|
| **VERY HIGH** | R ≥ 0.75 |
| **HIGH** | 0.50 ≤ R < 0.75 |
| **MODERATE** | 0.25 ≤ R < 0.50 |
| **LOW** | R < 0.25 |
""")

w = settings
st.markdown(f"""
### Active Weight Configuration

| Weight | Symbol | Current Value |
|--------|--------|---------------|
| Temperature | α | **{w.temperature_weight:.2f}** |
| Environmental | β | **{w.built_environment_weight:.2f}** |
| Vulnerability | γ | **{w.vulnerability_weight:.2f}** |
| Service Access | δ | **{w.service_access_weight:.2f}** |
| Mobility | ε | **{w.mobility_weight:.2f}** |
| **Sum** | | **{w.temperature_weight+w.built_environment_weight+w.vulnerability_weight+w.service_access_weight+w.mobility_weight:.2f}** |

Weights must sum to exactly 1.0 (validated at runtime by `RiskModelWeights.validate_sum()`).
""")

st.markdown("""
### Normalization Method

All raw feature values are Min-Max normalized to [0, 1]:

> **x_norm = (x − x_min) / (x_max − x_min)**

For features where higher is safer (e.g., green cover, transport access score), the value is inverted:

> **x_norm = 1 − (x − x_min) / (x_max − x_min)**

When x_min ≈ x_max (no variation in the dataset), the normalized value is set to 0.0.
Missing values are imputed to 0.0 after normalization.
""")

st.info("Model version, weights, and per-neighbourhood factor contributions are stored in the `risk_explainability` JSON column of every pipeline output row.")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 2. OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════
st.header("2 · Multi-Objective Optimization (Planner v3.1.0)")

st.markdown("""
### Objective Function

> **Objective = α·RiskCoverage + β·MobileCoverage + γ·LowServiceCoverage + δ·Fairness − ε·TravelCost − ζ·OperationalPenalty**

The planner solves a Mixed Integer Program (MIP) using PuLP / CBC to maximise this objective
subject to hard capacity constraints.

### Strategies

| Strategy | Description | Emphasis |
|----------|-------------|----------|
| **COVERAGE_FOCUSED** | Maximise high-risk neighbourhood coverage | α=0.5, β=0.2, γ=0.2, δ=0.1 |
| **BALANCED** | Balance risk, fairness, and travel | α=0.3, β=0.25, γ=0.25, δ=0.2 |
| **FAIRNESS_AWARE** | Prioritise underserved groups | α=0.2, β=0.3, γ=0.3, δ=0.2 |

### Decision Variables

- **x_i ∈ {0, 1}**: whether neighbourhood i is selected for outreach

### Constraints (Hard)

All capacity constraints from Section 3 are enforced directly as MIP constraints.
The solver will return INFEASIBLE rather than violate them.
""")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 3. OPERATIONAL CONSTRAINTS
# ══════════════════════════════════════════════════════════════════════════════
st.header("3 · Operational Constraint Engine")

st.markdown(f"""
### Hard Constraints (MUST NOT be violated)

| Constraint | Current Limit |
|-----------|---------------|
| Maximum team capacity / day | {settings.maximum_visits_per_team} visits/team |
| Number of teams | {settings.number_of_teams} teams |
| Total daily capacity | {settings.number_of_teams * settings.maximum_visits_per_team} visits |
| Maximum shift duration | {settings.working_hours:.0f} hours |
| Maximum travel time / team / day | {settings.maximum_travel_time} minutes |
| Maximum travel distance / team / day | {settings.maximum_travel_distance:.0f} km |
| Neighbourhood service capacity | {settings.neighbourhood_service_capacity} people/neighbourhood |
| Maximum outreach events / day (network) | {settings.maximum_outreach_events_per_day} |

### Soft Constraints (Converted to Penalties)

- Geographic clustering preference: nearby neighbourhoods are batched together
- High-risk priority: risk score contributes positively to objective
- Underserved-group priority: group membership contributes to fairness term
- Balanced workload: team utilization variance is penalized
- Reduced route switching: routing continuity is encouraged

### If No Feasible Plan Exists

1. The system does **NOT** generate an invalid plan
2. Safe fallback is activated (baseline plan, high-risk shortlist, or manual review)
3. The reason for infeasibility is logged and surfaced to the operator
""")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 4. FAIRNESS
# ══════════════════════════════════════════════════════════════════════════════
st.header("4 · Fairness & Bias Analysis")

st.markdown(f"""
### Protected Groups

| Group | Definition |
|-------|-----------|
| **Mobile Population** | Neighbourhoods where `group_mobile = True` (mobile/migrant workers) |
| **Low-Service-Access** | Neighbourhoods where `group_low_service_access = True` |

### Fairness Metrics

| Metric | Formula |
|--------|---------|
| **Coverage Gap** | \|Group Coverage − Overall Coverage\| |
| **Coverage Ratio** | Group Coverage / Overall Coverage |
| **Opportunity Difference** | Group Selection Rate − Overall Selection Rate |
| **Population-Weighted Coverage** | Σ(selected_i × population_i) / Σ(population_i) |

### Thresholds

| Threshold | Current Value |
|-----------|---------------|
| Maximum Coverage Gap | {settings.maximum_coverage_gap:.0%} |
| Minimum Group Coverage | {settings.minimum_group_coverage:.0%} |

### Fairness Strategies

The FAIRNESS_AWARE optimizer explicitly adds group membership as a positive objective term.
If coverage gap exceeds the threshold, a fairness warning is logged and surfaced in the UI.
""")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 5. CONFIDENCE MODEL
# ══════════════════════════════════════════════════════════════════════════════
st.header("5 · Confidence & Failure-Safe System")

st.markdown(f"""
### Confidence Score Formula

> **Confidence = 1.0 − Σ(penalty_i)**

Penalties are applied for:

| Condition | Penalty |
|-----------|---------|
| Missing critical field (e.g., temperature_c) | −0.20 per field |
| Invalid geographic coordinates | −0.30 |
| Abnormal temperature (< 20°C or > 50°C) | −0.10 |
| Missing vulnerability / service data | −0.10 each |

### Confidence Tiers

| Tier | Score Range | Action |
|------|-------------|--------|
| **HIGH CONFIDENCE** | ≥ {settings.minimum_confidence_for_automatic_recommendation:.2f} | Automated recommendation proceeds |
| **MEDIUM CONFIDENCE** | {settings.warning_confidence_threshold:.2f} – {settings.minimum_confidence_for_automatic_recommendation:.2f} | Warning shown; recommendation proceeds with caution |
| **LOW CONFIDENCE** | < {settings.warning_confidence_threshold:.2f} | **Safe fallback activated — no automated recommendation** |

### Fallback Hierarchy

1. **STANDARD** — full confidence, automated recommendation
2. **BASELINE_PLAN** — revert to temperature-only baseline
3. **HIGH_RISK_SHORTLIST** — only VERY HIGH risk neighbourhoods
4. **MANUAL_REVIEW** — flag for human review; no automated scheduling
5. **FAILED** — pipeline error; no output generated
""")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 6. SENSITIVITY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
st.header("6 · Sensitivity Analysis Method")

st.markdown("""
### Purpose

Sensitivity analysis tests how robust the planner's output is to changes in configurable weights.
A plan that changes dramatically under small weight variations is less trustworthy.

### Method

For each of the 5 risk model weights:
1. The weight is increased or decreased by **±10 percentage points**
2. All other weights are **proportionally rescaled** to maintain the sum = 1.0
3. The risk model is re-run on the **same dataset**
4. The planner is re-run with COVERAGE_FOCUSED strategy
5. Metric-level impact is reported: coverage change (pp), fairness gap change (pp), category changes

For **Travel Penalty** and **Fairness Weight** (which are not risk model parameters):
- A synthetic scoring function re-ranks neighbourhoods
- The same n_selected as the baseline is chosen from the new ranking
- Impact is computed against the baseline metrics

### Interpretation

| Coverage Δ | Interpretation |
|------------|----------------|
| < ±5 pp | Robust — plan is stable |
| 5–15 pp | Moderate sensitivity — worth noting in the decision rationale |
| > 15 pp | High sensitivity — manual review recommended before deployment |
""")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 7. LIMITATIONS
# ══════════════════════════════════════════════════════════════════════════════
st.header("7 · Known Limitations")

st.warning("""
**The following limitations must be understood before using system outputs for operational decisions:**
""")

st.markdown("""
1. **No ground-truth validation**: The dataset does not contain verified outreach outcomes. 
  Proxy validation metrics (top-risk capture, rank stability) are used instead of precision/recall.
  Do NOT interpret proxy metrics as supervised performance scores.

2. **Normalization is dataset-dependent**: Risk scores are Min-Max normalized within the loaded dataset.
  A neighbourhood rated HIGH in one dataset may be MODERATE in a larger or different dataset.
  Scores are NOT comparable across datasets with different distributions.

3. **Synthetic travel estimates**: Travel time is estimated as distance / 30 km·h⁻¹.
  Actual road conditions, traffic, and routing are not modeled.

4. **Prototype authentication**: Role-based access control is simulated locally.
  No cryptographic authentication is implemented. Not suitable for production deployment.

5. **Static dataset**: The planner operates on a point-in-time snapshot. 
  Heat conditions change rapidly; stale data degrades plan quality.
  Freshness thresholds are enforced (warning at {warning}h, staleness at {stale}h).

6. **Confidence penalties are manually calibrated**: The penalty magnitudes were set by 
  subject-matter expert judgment, not by empirical optimization.

7. **MIP solver**: The CBC solver is used. For very large datasets (> 10,000 rows),
  solver runtime may be significant. Time limits are not currently enforced.

8. **Group membership is binary**: Protected groups are flagged True/False per neighbourhood.
  Intra-neighbourhood heterogeneity is not captured.
""".format(
  warning=settings.freshness_threshold_hours,
  stale=settings.staleness_threshold_hours
))

st.markdown("---")
st.caption(
  f"System: Neighbourhood Heat-Risk Outreach Planner · "
  f"Risk Model v2.0.0 · Optimizer v3.1.0 · "
  f"Active Dataset: {settings.active_csv_dataset}"
)
