"""Drift scoring and cross-report comparison for mtp-run."""

from __future__ import annotations

from typing import Any


DEFAULT_WEIGHTS = {
    "step_fidelity": 0.25,
    "deviation_rate": 0.15,
    "validation_pass_rate": 0.25,
    "output_quality": 0.20,
    "edge_case_coverage": 0.10,
    "novel_situation_rate": 0.03,
    "dead_end_avoidance": 0.02,
}


def compute_report_drift(report: dict[str, Any], weights: dict[str, float] | None = None) -> dict[str, Any]:
    """Compute spec §8.3 drift score from a single execution report."""
    execution_report = _execution_report(report)
    component_values = _component_values(execution_report)
    return _weighted_score(component_values, weights)


def compare_reports(
    baseline_report: dict[str, Any],
    candidate_report: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compare two execution reports using weighted methodology preservation scoring.

    The baseline and candidate are each scored on their own terms using spec §8.3.
    Cross-report drift is then computed as per-component closeness:

        closeness_i = 1.0 - abs(candidate_i - baseline_i)

    for every computable component on both sides. Missing components are excluded and
    their weights redistributed per spec §8.3.
    """
    baseline_execution = _execution_report(baseline_report)
    candidate_execution = _execution_report(candidate_report)

    baseline_self = compute_report_drift(baseline_execution, weights)
    candidate_self = compute_report_drift(candidate_execution, weights)
    state_comparison = _state_comparison(baseline_execution, candidate_execution)

    comparison_components: dict[str, float | None] = {}
    baseline_components = baseline_self["components"]
    candidate_components = candidate_self["components"]
    for component in DEFAULT_WEIGHTS:
        baseline_value = baseline_components.get(component)
        candidate_value = candidate_components.get(component)
        if baseline_value is None or candidate_value is None:
            comparison_components[component] = None
            continue
        comparison_components[component] = round(max(0.0, 1.0 - abs(candidate_value - baseline_value)), 4)

    comparison_drift = _weighted_score(comparison_components, weights)

    return {
        "baseline": {
            "target_platform": baseline_execution.get("target_platform", "unknown"),
            "overall_status": baseline_execution.get("overall_status", "unknown"),
            "drift_score": baseline_self,
        },
        "candidate": {
            "target_platform": candidate_execution.get("target_platform", "unknown"),
            "overall_status": candidate_execution.get("overall_status", "unknown"),
            "drift_score": candidate_self,
        },
        "comparison_drift": comparison_drift,
        "state_agreement": state_comparison["step_state_agreement"],
        "matching_steps": state_comparison["matching_steps"],
        "total_steps": state_comparison["total_steps"],
        "differences": state_comparison["differences"],
    }


def _execution_report(report: dict[str, Any]) -> dict[str, Any]:
    if "execution_report" in report:
        return report["execution_report"]
    return report


def _component_values(execution_report: dict[str, Any]) -> dict[str, float | None]:
    total_steps = max(len(execution_report.get("steps", [])), 1)
    steps = execution_report.get("steps", [])
    states = [step.get("state", "failure") for step in steps]
    validation_results = [
        step.get("validation_result")
        for step in steps
        if step.get("validation_result") in {"pass", "fail"}
    ]
    quality_checks = execution_report.get("quality_checks", [])
    edge_cases = execution_report.get("edge_cases_encountered", [])
    novel_situations = execution_report.get("novel_situations", [])

    components: dict[str, float | None] = {
        "step_fidelity": round(states.count("success") / total_steps, 4),
        "deviation_rate": round(1.0 - (states.count("deviation") / total_steps), 4),
        "validation_pass_rate": None,
        "output_quality": None,
        "edge_case_coverage": None,
        "novel_situation_rate": round(1.0 - (len(novel_situations) / total_steps), 4),
        "dead_end_avoidance": _dead_end_avoidance(execution_report),
    }

    if validation_results:
        components["validation_pass_rate"] = round(
            validation_results.count("pass") / len(validation_results), 4
        )
    else:
        components["validation_pass_rate"] = _stored_component(execution_report, "validation_pass_rate")

    if quality_checks:
        passed_checks = sum(1 for check in quality_checks if check.get("result") == "pass")
        components["output_quality"] = round(passed_checks / len(quality_checks), 4)
    else:
        components["output_quality"] = _stored_component(execution_report, "output_quality")

    if edge_cases:
        handled = sum(1 for edge_case in edge_cases if _edge_case_handled(edge_case))
        components["edge_case_coverage"] = round(handled / len(edge_cases), 4)
    else:
        components["edge_case_coverage"] = _stored_component(execution_report, "edge_case_coverage")

    return components


def _stored_component(execution_report: dict[str, Any], name: str) -> float | None:
    value = execution_report.get("drift_score", {}).get("components", {}).get(name)
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    return None


def _edge_case_handled(edge_case: dict[str, Any]) -> bool:
    matched = str(edge_case.get("matched_edge_case", "")).strip()
    handling = str(edge_case.get("handling_applied", "")).strip()
    return bool(matched and matched != "novel" and handling)


def _dead_end_avoidance(execution_report: dict[str, Any]) -> float | None:
    stored = _stored_component(execution_report, "dead_end_avoidance")
    if stored is not None:
        return stored
    return 1.0


def _weighted_score(
    component_values: dict[str, float | None],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    effective_weights = dict(weights or DEFAULT_WEIGHTS)
    active = {
        name: value
        for name, value in component_values.items()
        if value is not None and name in effective_weights
    }
    weight_sum = sum(effective_weights[name] for name in active)

    if weight_sum == 0:
        normalized_weights: dict[str, float] = {}
        composite = 0.0
    else:
        normalized_weights = {
            name: round(effective_weights[name] / weight_sum, 4)
            for name in active
        }
        composite = round(
            sum(normalized_weights[name] * active[name] for name in active),
            4,
        )

    return {
        "composite": composite,
        "components": component_values,
        "weights_used": normalized_weights,
    }


def _state_comparison(
    baseline_execution: dict[str, Any],
    candidate_execution: dict[str, Any],
) -> dict[str, Any]:
    baseline_steps = {
        step["step"]: step
        for step in baseline_execution.get("steps", [])
    }
    candidate_steps = {
        step["step"]: step
        for step in candidate_execution.get("steps", [])
    }
    all_step_numbers = sorted(set(baseline_steps) | set(candidate_steps))
    matches = 0
    differences = []

    for step_number in all_step_numbers:
        baseline_state = baseline_steps.get(step_number, {}).get("state", "missing")
        candidate_state = candidate_steps.get(step_number, {}).get("state", "missing")
        if baseline_state == candidate_state:
            matches += 1
            continue
        differences.append({
            "step": step_number,
            "baseline_state": baseline_state,
            "candidate_state": candidate_state,
        })

    total_steps = len(all_step_numbers)
    agreement = round(matches / total_steps, 4) if total_steps else 0.0
    return {
        "matching_steps": matches,
        "total_steps": total_steps,
        "step_state_agreement": agreement,
        "differences": differences,
    }
