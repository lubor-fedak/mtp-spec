"""Execution report builder and drift calculator.

Assembles raw execution results into a standardized MTP execution report
and optionally computes drift scores against a baseline.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import yaml


# --- overall_status derivation (spec §7.2) ---

def _derive_overall_status(steps: list[dict], quality_checks: list[dict]) -> str:
    """Deterministic derivation per MTP spec §7.2.

    Priority: escalated > failure (blocking) > failure (blocking quality check) > deviation > partial/skipped > success
    """
    states = [s["state"] for s in steps]

    if "escalated" in states:
        return "escalated"

    for s in steps:
        if s["state"] == "failure" and s.get("failure_blocking", True):
            return "failure"

    for qc in quality_checks:
        if qc.get("is_blocking") and qc.get("result") == "fail":
            return "failure"

    if "deviation" in states:
        return "deviation"

    if "partial" in states or "skipped" in states:
        return "partial"

    return "success"


# --- Drift scoring ---

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
    dead_ends_prevented: list[dict],
    dead_ends_repeated: bool = False,
    weights: dict | None = None,
) -> dict:
    """Compute composite drift score per MTP spec §8.

    All components are normalized to 0.0-1.0 where 1.0 = perfect.
    Inverted-polarity metrics use 1.0 - raw.
    Missing components excluded and weights redistributed.
    """
    w = weights or DEFAULT_WEIGHTS.copy()

    total_steps = len(steps)
    if total_steps == 0:
        return {"composite": 0.0, "components": {}, "weights_used": {}}

    states = [s["state"] for s in steps]
    validations = [s.get("validation_result") for s in steps if s.get("validation_result") in ("pass", "fail")]

    components: dict[str, float | None] = {}

    # Step fidelity: ratio of success states (natural polarity)
    components["step_fidelity"] = states.count("success") / total_steps

    # Deviation rate: inverted (lower is better → 1.0 - raw)
    components["deviation_rate"] = 1.0 - (states.count("deviation") / total_steps)

    # Validation pass rate (natural polarity)
    if validations:
        components["validation_pass_rate"] = validations.count("pass") / len(validations)
    else:
        components["validation_pass_rate"] = None  # no validations to check

    # Output quality (natural polarity)
    if quality_checks:
        passed_qc = sum(1 for qc in quality_checks if qc.get("result") == "pass")
        components["output_quality"] = passed_qc / len(quality_checks)
    else:
        components["output_quality"] = None

    # Edge case coverage (natural polarity)
    if edge_cases_encountered:
        handled = sum(1 for ec in edge_cases_encountered if ec.get("matched_edge_case") != "novel")
        components["edge_case_coverage"] = handled / len(edge_cases_encountered)
    else:
        components["edge_case_coverage"] = None

    # Novel situation rate: inverted
    components["novel_situation_rate"] = 1.0 - (len(novel_situations) / total_steps)

    # Dead end avoidance: binary
    components["dead_end_avoidance"] = 0.0 if dead_ends_repeated else 1.0

    # Compute weighted average with redistribution for None components
    active_weights = {}
    active_values = {}
    for key, value in components.items():
        if value is not None and key in w:
            active_weights[key] = w[key]
            active_values[key] = value

    weight_sum = sum(active_weights.values())
    if weight_sum == 0:
        composite = 0.0
        normalized_weights = {}
    else:
        # Redistribute weights proportionally
        normalized_weights = {k: v / weight_sum for k, v in active_weights.items()}
        composite = sum(normalized_weights[k] * active_values[k] for k in active_values)

    return {
        "composite": round(composite, 4),
        "components": {k: round(v, 4) if v is not None else None for k, v in components.items()},
        "weights_used": {k: round(v, 4) for k, v in normalized_weights.items()},
    }


# --- Report assembly ---

def build_execution_report(
    package: dict,
    raw_results: dict,
    duration_seconds: float,
    executor_id: str = "mtp-run v0.4.0",
    quality_checks: list[dict] | None = None,
    baseline_ref: str | None = None,
    baseline_type: str | None = None,
) -> dict:
    """Assemble a complete MTP execution report.

    Args:
        package: The executed MTP package
        raw_results: Output from executor.execute_package()
        duration_seconds: Total execution wall time
        executor_id: Identifier for the executor tool
        quality_checks: Optional quality check results
        baseline_ref: Optional reference to baseline for drift comparison
        baseline_type: Type of baseline (reference_run, self_comparison, temporal_comparison)
    """
    steps = raw_results["steps"]
    qc = quality_checks or []

    overall_status = _derive_overall_status(steps, qc)

    # Confidence heuristic
    failure_count = sum(1 for s in steps if s["state"] in ("failure", "escalated"))
    deviation_count = sum(1 for s in steps if s["state"] == "deviation")
    total = len(steps)

    if failure_count > 0:
        confidence = "low"
    elif deviation_count > total * 0.3:
        confidence = "low"
    elif deviation_count > 0:
        confidence = "medium"
    else:
        confidence = "high"

    report = {
        "execution_report": {
            "mtp_package_id": package.get("package", {}).get("id", "unknown"),
            "mtp_package_version": package.get("package", {}).get("version", "0.0.0"),
            "mtp_spec_version": "0.2",
            "target_platform": raw_results["platform"],
            "executor": executor_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(duration_seconds, 2),
            "overall_status": overall_status,
            "overall_confidence": confidence,
            "steps": steps,
            "edge_cases_encountered": raw_results.get("edge_cases_encountered", []),
            "novel_situations": raw_results.get("novel_situations", []),
            "dead_ends_prevented": raw_results.get("dead_ends_prevented", []),
            "quality_checks": qc,
            "policy_compliance": {
                "data_leaked": False,
                "pii_detected": False,
                "notes": "",
            },
        }
    }

    # Drift score
    drift = compute_drift_score(
        steps=steps,
        quality_checks=qc,
        edge_cases_encountered=raw_results.get("edge_cases_encountered", []),
        novel_situations=raw_results.get("novel_situations", []),
        dead_ends_prevented=raw_results.get("dead_ends_prevented", []),
    )

    if baseline_ref:
        drift["baseline_type"] = baseline_type or "reference_run"
        drift["baseline_ref"] = baseline_ref

    report["execution_report"]["drift_score"] = drift

    # Report hash
    content = json.dumps(report, sort_keys=True, default=str)
    report["execution_report"]["report_hash"] = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

    return report


def format_report_yaml(report: dict) -> str:
    """Format execution report as YAML."""
    return yaml.dump(report, default_flow_style=False, sort_keys=False, allow_unicode=True)


def format_report_json(report: dict) -> str:
    """Format execution report as JSON."""
    return json.dumps(report, indent=2, default=str)
