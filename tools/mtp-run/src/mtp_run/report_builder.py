"""Execution report builder for standardized MTP execution reports."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import yaml

from mtp_run import __version__
from mtp_run.drift import compare_reports, compute_report_drift

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


# --- Report assembly ---

def build_execution_report(
    package: dict,
    raw_results: dict,
    duration_seconds: float,
    executor_id: str = f"mtp-run v{__version__}",
    quality_checks: list[dict] | None = None,
    baseline_ref: str | None = None,
    baseline_type: str | None = None,
    baseline_report: dict[str, Any] | None = None,
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
        baseline_report: Optional loaded execution report for cross-report drift comparison
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

    execution_report = {
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
    report = {"execution_report": execution_report}

    if raw_results.get("dead_ends_repeated"):
        execution_report.setdefault("drift_score", {})
        execution_report["drift_score"] = {
            "components": {
                "dead_end_avoidance": 0.0,
            }
        }

    if baseline_report:
        drift = compare_reports(baseline_report, report)["comparison_drift"]
    else:
        drift = compute_report_drift(report)

    if baseline_ref:
        drift["baseline_type"] = baseline_type or "reference_run"
        drift["baseline_ref"] = baseline_ref

    execution_report["drift_score"] = drift

    # Report hash
    content = json.dumps(report, sort_keys=True, default=str)
    execution_report["report_hash"] = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

    return report


def mock_quality_checks(package: dict) -> list[dict]:
    """Generate mock quality check results for deterministic testing.

    When using the mock adapter, all quality checks defined in the package
    are automatically marked as passed.
    """
    checks = []
    for quality_check in package.get("output", {}).get("quality_checks", []):
        checks.append({
            "check": quality_check.get("check", ""),
            "result": "pass",
            "is_blocking": bool(quality_check.get("is_blocking", False)),
            "notes": "Mock adapter reference run marked this quality check as passed.",
        })
    return checks


def format_report_yaml(report: dict) -> str:
    """Format execution report as YAML."""
    return yaml.dump(report, default_flow_style=False, sort_keys=False, allow_unicode=True)


def format_report_json(report: dict) -> str:
    """Format execution report as JSON."""
    return json.dumps(report, indent=2, default=str)
