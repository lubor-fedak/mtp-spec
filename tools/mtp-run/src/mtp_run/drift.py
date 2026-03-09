"""Drift measurement for MTP execution reports.

Two capabilities:
  - compute_drift_score(): Weighted composite drift per spec §8.3
  - compare_reports(): Cross-report step-state comparison
"""

from __future__ import annotations

from typing import Any


# Default weights per spec §8.3
DEFAULT_WEIGHTS = {
    "step_fidelity": 0.25,
    "deviation_rate": 0.15,
    "validation_pass_rate": 0.25,
    "output_quality": 0.20,
    "edge_case_coverage": 0.10,
    "novel_situation_rate": 0.03,
    "dead_end_avoidance": 0.02,
}


def compute_drift_score(
    steps: list[dict],
    quality_checks: list[dict],
    edge_cases_encountered: list[dict],
    novel_situations: list[dict],
    dead_ends_repeated: bool = False,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute composite drift score per MTP spec §8.3.

    All components normalized to 0.0–1.0 where 1.0 = perfect (no drift).
    Inverted-polarity metrics use 1.0 - raw.
    Missing components excluded, weights redistributed proportionally.
    """
    w = weights or DEFAULT_WEIGHTS.copy()
    total_steps = len(steps)

    if total_steps == 0:
        return {
            "composite": 0.0,
            "components": {},
            "weights_used": {},
        }

    states = [s["state"] for s in steps]
    validations = [
        s["validation_result"]
        for s in steps
        if s.get("validation_result") in ("pass", "fail")
    ]

    components: dict[str, float | None] = {}

    # Step fidelity — natural polarity (higher = better)
    components["step_fidelity"] = states.count("success") / total_steps

    # Deviation rate — inverted (lower raw = better → 1.0 - raw)
    components["deviation_rate"] = 1.0 - (states.count("deviation") / total_steps)

    # Validation pass rate — natural polarity
    if validations:
        components["validation_pass_rate"] = validations.count("pass") / len(validations)
    else:
        components["validation_pass_rate"] = None

    # Output quality — natural polarity
    if quality_checks:
        passed_qc = sum(1 for qc in quality_checks if qc.get("result") == "pass")
        components["output_quality"] = passed_qc / len(quality_checks)
    else:
        components["output_quality"] = None

    # Edge case coverage — natural polarity
    if edge_cases_encountered:
        handled = sum(
            1 for ec in edge_cases_encountered
            if ec.get("matched_edge_case") != "novel"
        )
        components["edge_case_coverage"] = handled / len(edge_cases_encountered)
    else:
        components["edge_case_coverage"] = None

    # Novel situation rate — inverted
    components["novel_situation_rate"] = 1.0 - (len(novel_situations) / total_steps)

    # Dead end avoidance — binary
    components["dead_end_avoidance"] = 0.0 if dead_ends_repeated else 1.0

    # Weighted average with redistribution for None components
    active: dict[str, float] = {}
    for key, val in components.items():
        if val is not None and key in w:
            active[key] = val

    weight_sum = sum(w[k] for k in active)
    if weight_sum == 0:
        return {
            "composite": 0.0,
            "components": {k: round(v, 4) if v is not None else None for k, v in components.items()},
            "weights_used": {},
        }

    # Redistribute weights proportionally so they sum to 1.0
    normalized_weights = {k: w[k] / weight_sum for k in active}
    composite = sum(normalized_weights[k] * active[k] for k in active)

    return {
        "composite": round(composite, 4),
        "components": {k: round(v, 4) if v is not None else None for k, v in components.items()},
        "weights_used": {k: round(v, 4) for k, v in normalized_weights.items()},
    }


def compare_reports(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare two execution reports — step-state agreement and weighted drift.

    Returns a structured comparison with per-step matching, state agreement,
    and per-report drift scores if available.
    """
    left_er = left["execution_report"]
    right_er = right["execution_report"]

    left_steps = {s["step"]: s for s in left_er["steps"]}
    right_steps = {s["step"]: s for s in right_er["steps"]}
    all_step_numbers = sorted(set(left_steps) | set(right_steps))

    total = len(all_step_numbers)
    matches = 0
    differences = []
    step_comparison = []

    for snum in all_step_numbers:
        ls = left_steps.get(snum)
        rs = right_steps.get(snum)
        l_state = ls["state"] if ls else "missing"
        r_state = rs["state"] if rs else "missing"
        match = l_state == r_state

        if match:
            matches += 1
        else:
            differences.append({
                "step": snum,
                "left_state": l_state,
                "right_state": r_state,
            })

        step_comparison.append({
            "step": snum,
            "left_state": l_state,
            "right_state": r_state,
            "match": match,
        })

    agreement = (matches / total) if total else 0.0

    # Include per-report drift scores if present
    left_drift = left_er.get("drift_score", {}).get("composite")
    right_drift = right_er.get("drift_score", {}).get("composite")

    result = {
        "left_platform": left_er.get("target_platform", "unknown"),
        "right_platform": right_er.get("target_platform", "unknown"),
        "left_status": left_er.get("overall_status", "unknown"),
        "right_status": right_er.get("overall_status", "unknown"),
        "matching_steps": matches,
        "total_steps": total,
        "step_state_agreement": round(agreement, 4),
        "differences": differences,
        "step_comparison": step_comparison,
    }

    if left_drift is not None:
        result["left_drift_score"] = left_drift
    if right_drift is not None:
        result["right_drift_score"] = right_drift

    return result
