"""
src/evaluation/validation_engine.py

Phase 9: Quantitative Validation Engine.

Determines whether ground-truth labels exist. If they do, computes precision /
recall / F1 / confusion matrix. If they do NOT exist (which is the usual case
for an operational heat-risk dataset), computes proxy validation metrics:

  - top_risk_capture_rate   : fraction of top-N risk neighbourhoods selected
  - rule_based_agreement    : agreement with a deterministic threshold rule
  - rank_stability          : Kendall-τ rank correlation between risk score & selection order
  - sensitivity             : how many of the planner's selections change under ±5% risk perturbation
  - threshold_consistency   : fraction of selected neighbourhoods above the high-risk threshold

All metrics are documented with their mathematical definitions.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

logger = logging.getLogger("validation_engine")

# ── Ground-truth detection ─────────────────────────────────────────────────────
GT_LABEL_COLUMNS = ["ground_truth_selected", "expert_label", "verified_outreach"]

def _detect_ground_truth(df: pd.DataFrame) -> Optional[str]:
    """Returns the ground-truth column name if present, else None."""
    for col in GT_LABEL_COLUMNS:
        if col in df.columns:
            return col
    return None


# ── Supervised metrics (only used if ground truth exists) ─────────────────────
def _supervised_metrics(df: pd.DataFrame, gt_col: str) -> Dict[str, Any]:
    """
    Calculate precision, recall, F1, and confusion matrix.
    
    Definitions:
        TP = selected AND ground_truth_positive
        FP = selected AND ground_truth_negative
        FN = NOT selected AND ground_truth_positive
        TN = NOT selected AND ground_truth_negative
    
        Precision = TP / (TP + FP)
        Recall    = TP / (TP + FN)
        F1        = 2 × Precision × Recall / (Precision + Recall)
    """
    is_selected = df.get("selected_for_outreach", pd.Series(False, index=df.index)).astype(bool)
    gt          = df[gt_col].astype(bool)

    tp = int((is_selected & gt).sum())
    fp = int((is_selected & ~gt).sum())
    fn = int((~is_selected & gt).sum())
    tn = int((~is_selected & ~gt).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    return {
        "ground_truth_available": True,
        "ground_truth_column":    gt_col,
        "precision":   round(precision, 4),
        "recall":      round(recall, 4),
        "f1_score":    round(f1, 4),
        "true_positives":  tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives":  tn,
        "confusion_matrix": {
            "TP": tp, "FP": fp, "FN": fn, "TN": tn
        },
    }


# ── Proxy/unsupervised metrics (used when ground truth is absent) ──────────────
def _proxy_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Proxy validation metrics for operational datasets without ground truth.

    1. Top-Risk Capture Rate
       Definition: |Selected ∩ Top-N by risk score| / N
       N = number_selected. Measures whether the planner captures the highest-risk neighbourhoods.

    2. Rule-Based Agreement
       Definition: |Selected ∩ Rule-Positive| / |Rule-Positive|
       Rule-Positive = neighbourhoods with risk_category IN {VERY HIGH, HIGH, EXTREME}.
       Agreement measures alignment with a simple deterministic threshold rule.

    3. Rank Stability (Kendall-τ)
       Definition: Kendall rank correlation between multi_factor_risk_score and selected_for_outreach.
       τ ∈ [-1, 1]. Values close to 1 indicate the planner respects the risk ranking.

    4. Sensitivity (Perturbation Robustness)
       Definition: Fraction of selections that change when risk scores are randomly perturbed ±5%.
       Lower = more stable/consistent planner.

    5. Threshold Consistency
       Definition: |Selected ∩ Above-Threshold| / |Selected|
       Threshold = top-quartile risk score. Measures internal consistency.
    """
    results: Dict[str, Any] = {
        "ground_truth_available": False,
        "ground_truth_note": (
            "No ground-truth labels found in dataset. "
            "Supervised metrics (precision/recall/F1) are NOT calculated. "
            "Proxy validation metrics are computed instead."
        ),
    }

    is_selected = df.get("selected_for_outreach", pd.Series(False, index=df.index)).astype(bool)
    n_selected  = int(is_selected.sum())
    n_total     = len(df)

    if n_total == 0 or "multi_factor_risk_score" not in df.columns:
        results["error"] = "Insufficient data for proxy validation"
        return results

    risk_scores = df["multi_factor_risk_score"].fillna(0.0)

    # 1. Top-Risk Capture Rate
    if n_selected > 0:
        top_n_idx   = risk_scores.nlargest(n_selected).index
        top_n_mask  = df.index.isin(top_n_idx)
        captured    = int((is_selected & top_n_mask).sum())
        results["top_risk_capture_rate"] = round(captured / n_selected, 4)
        results["top_risk_capture_n"]    = n_selected
    else:
        results["top_risk_capture_rate"] = 0.0

    # 2. Rule-Based Agreement
    high_risk_cats = {"VERY HIGH", "EXTREME", "HIGH"}
    if "multi_factor_risk_category" in df.columns:
        rule_pos     = df["multi_factor_risk_category"].isin(high_risk_cats)
        rule_pos_n   = int(rule_pos.sum())
        agreed       = int((is_selected & rule_pos).sum())
        results["rule_based_agreement"] = round(agreed / rule_pos_n, 4) if rule_pos_n > 0 else 0.0
        results["rule_positive_count"]  = rule_pos_n
        results["rule_agreed_count"]    = agreed
    else:
        results["rule_based_agreement"] = None

    # 3. Rank Stability (Kendall-τ)
    try:
        from scipy.stats import kendalltau
        tau, p_val = kendalltau(risk_scores.values, is_selected.astype(int).values)
        results["rank_stability_kendall_tau"] = round(float(tau), 4)
        results["rank_stability_p_value"]     = round(float(p_val), 4)
    except Exception:
        results["rank_stability_kendall_tau"] = None
        results["rank_stability_p_value"]     = None

    # 4. Sensitivity (±5% perturbation)
    try:
        rng = np.random.default_rng(seed=42)
        perturbed = risk_scores * (1 + rng.uniform(-0.05, 0.05, size=len(risk_scores)))
        perturbed_series = pd.Series(perturbed, index=df.index)
        if n_selected > 0:
            perturbed_top = perturbed_series.nlargest(n_selected).index
            perturbed_mask = df.index.isin(perturbed_top)
            changed = int((is_selected != perturbed_mask).sum())
            results["sensitivity_change_rate"] = round(changed / n_total, 4)
            results["sensitivity_changed_n"]   = changed
        else:
            results["sensitivity_change_rate"] = 0.0
    except Exception:
        results["sensitivity_change_rate"] = None

    # 5. Threshold Consistency
    threshold = float(risk_scores.quantile(0.75))
    above_threshold = risk_scores >= threshold
    if n_selected > 0:
        consistent = int((is_selected & above_threshold).sum())
        results["threshold_consistency"] = round(consistent / n_selected, 4)
        results["threshold_value"]       = round(threshold, 4)
        results["threshold_consistent_n"] = consistent
    else:
        results["threshold_consistency"] = 0.0

    return results


# ── Public API ────────────────────────────────────────────────────────────────
def validate_experiment_results(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Entry point for validation. Auto-detects ground truth and routes to the
    appropriate metric calculator.
    """
    if df is None or df.empty:
        return {
            "ground_truth_available": False,
            "error": "Empty dataframe — no validation possible"
        }

    gt_col = _detect_ground_truth(df)
    if gt_col:
        logger.info("Ground-truth column '%s' detected. Running supervised metrics.", gt_col)
        return _supervised_metrics(df, gt_col)
    else:
        logger.info("No ground-truth labels found. Running proxy validation metrics.")
        return _proxy_metrics(df)
