"""Core conformance execution engine."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
for source_path in (
    REPO_ROOT / "tools" / "mtp-lint" / "src",
    REPO_ROOT / "tools" / "mtp-run" / "src",
):
    source_str = str(source_path)
    if source_str not in sys.path:
        sys.path.insert(0, source_str)

from mtp_conformance.fixtures import FixtureManifest, discover_fixtures  # noqa: E402
from mtp_lint.policy_gate import check_policy  # noqa: E402
from mtp_lint.redaction_scanner import scan_all  # noqa: E402
from mtp_lint.schema_validator import (  # noqa: E402
    detect_artifact_type,
    detect_version,
    load_package,
    validate_schema,
)
from mtp_run.adapters import get_adapter  # noqa: E402
from mtp_run.drift import compare_reports, compute_report_drift  # noqa: E402
from mtp_run.executor import execute_package  # noqa: E402
from mtp_run.io_utils import load_artifact, validate_execution_report, validate_package  # noqa: E402
from mtp_run.report_builder import build_execution_report  # noqa: E402


LEVEL_ORDER = {"l1": 1, "l2": 2, "l3": 3}


@dataclass
class FixtureResult:
    id: str
    level: str
    kind: str
    passed: bool
    details: dict[str, Any]
    duration_ms: int


def run_conformance(level: str, fixtures_root: Path | None = None) -> dict[str, Any]:
    if level not in {"l1", "l2", "l3", "all"}:
        raise ValueError(f"Unsupported level '{level}'. Use l1, l2, l3, or all.")

    fixtures = discover_fixtures(fixtures_root)
    if level != "all":
        fixtures = [fixture for fixture in fixtures if LEVEL_ORDER[fixture.level] <= LEVEL_ORDER[level]]

    if not fixtures:
        raise ValueError("No fixtures discovered for the selected level.")

    results = [run_fixture(fixture) for fixture in fixtures]
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed

    summary = {
        "level": level,
        "total_fixtures": len(results),
        "passed": passed,
        "failed": failed,
        "fixtures": [asdict(result) for result in results],
    }
    summary["summary_hash"] = _summary_hash(summary)
    return summary


def run_fixture(fixture: FixtureManifest) -> FixtureResult:
    t0 = time.time()
    try:
        details = _run_fixture_impl(fixture)
        passed = bool(details.get("passed", False))
    except Exception as exc:
        passed = False
        details = {
            "passed": False,
            "error": str(exc),
        }

    duration_ms = int((time.time() - t0) * 1000)
    return FixtureResult(
        id=fixture.id,
        level=fixture.level,
        kind=fixture.kind,
        passed=passed,
        details=details,
        duration_ms=duration_ms,
    )


def _run_fixture_impl(fixture: FixtureManifest) -> dict[str, Any]:
    if fixture.kind == "package_validation":
        return _run_package_validation(fixture)
    if fixture.kind == "execution":
        return _run_execution_fixture(fixture)
    if fixture.kind == "redaction":
        return _run_redaction_fixture(fixture)
    if fixture.kind == "drift_self":
        return _run_drift_self_fixture(fixture)
    if fixture.kind == "drift_compare":
        return _run_drift_compare_fixture(fixture)
    if fixture.kind == "provenance":
        return _run_provenance_fixture(fixture)
    raise ValueError(f"Unknown fixture kind '{fixture.kind}' in {fixture.manifest_path}")


def _run_package_validation(fixture: FixtureManifest) -> dict[str, Any]:
    artifact_path = _required_path(fixture, "artifact")
    data = load_package(artifact_path)
    artifact_type = detect_artifact_type(data)
    version = detect_version(data, artifact_type)
    errors = validate_schema(data, artifact_type, version)
    expected_valid = bool(fixture.data["expect"]["valid"])
    actual_valid = not errors
    passed = actual_valid == expected_valid
    return {
        "passed": passed,
        "artifact": str(artifact_path),
        "artifact_type": artifact_type,
        "version": version,
        "actual_valid": actual_valid,
        "expected_valid": expected_valid,
        "error_count": len(errors),
        "errors": errors,
    }


def _run_execution_fixture(fixture: FixtureManifest) -> dict[str, Any]:
    package_path = _required_path(fixture, "package")
    data_path = _required_path(fixture, "data")
    package = load_artifact(package_path)
    with open(data_path, encoding="utf-8") as handle:
        data = handle.read()

    package_errors = validate_package(package)
    if package_errors:
        raise ValueError(f"Fixture package is not schema-valid: {package_errors}")

    adapter_name = str(fixture.data.get("adapter", "mock"))
    azure = bool(fixture.data.get("azure", False))
    model = fixture.data.get("model")
    adapter = get_adapter(adapter_name, model=model, azure=azure)
    raw_results = execute_package(package=package, data=data, adapter=adapter)
    quality_checks = _quality_checks_for_fixture(package, adapter_name)
    report = build_execution_report(
        package=package,
        raw_results=raw_results,
        duration_seconds=0.0,
        executor_id="mtp-conformance v0.5.0",
        quality_checks=quality_checks,
    )
    report_errors = validate_execution_report(report)
    execution_report = report["execution_report"]

    expected = fixture.data["expect"]
    expected_overall = str(expected["overall_status"])
    expected_step_states = {
        int(step): str(state)
        for step, state in (expected.get("step_states") or {}).items()
    }
    actual_step_states = {
        int(step["step"]): step["state"]
        for step in execution_report.get("steps", [])
    }

    mismatches = []
    for step, expected_state in expected_step_states.items():
        actual_state = actual_step_states.get(step)
        if actual_state != expected_state:
            mismatches.append({
                "step": step,
                "expected": expected_state,
                "actual": actual_state,
            })

    passed = (
        not report_errors
        and execution_report.get("overall_status") == expected_overall
        and not mismatches
    )
    return {
        "passed": passed,
        "report_valid": not report_errors,
        "report_errors": report_errors,
        "expected_overall_status": expected_overall,
        "actual_overall_status": execution_report.get("overall_status"),
        "expected_step_states": expected_step_states,
        "actual_step_states": actual_step_states,
        "mismatches": mismatches,
    }


def _run_redaction_fixture(fixture: FixtureManifest) -> dict[str, Any]:
    artifact_path = _required_path(fixture, "artifact")
    data = load_package(artifact_path)
    client_dictionary = fixture.data.get("client_dictionary")
    if isinstance(client_dictionary, list):
        dictionary = [str(item) for item in client_dictionary]
    else:
        dictionary = None

    scan_result = scan_all(data, dictionary)
    categories_found = sorted({finding["category"] for finding in scan_result["findings"]})
    expected_categories = sorted(fixture.data["expect"].get("categories", []))
    expected_passed = bool(fixture.data["expect"]["passed"])

    category_match = all(category in categories_found for category in expected_categories)
    passed = scan_result["passed"] == expected_passed and category_match

    policy_expectation = fixture.data["expect"].get("policy_gate_passed")
    policy_result = None
    if policy_expectation is not None:
        policy_result = check_policy(data)
        passed = passed and (policy_result["gate_passed"] == bool(policy_expectation))

    return {
        "passed": passed,
        "scan_passed": scan_result["passed"],
        "expected_passed": expected_passed,
        "categories_found": categories_found,
        "expected_categories": expected_categories,
        "total_findings": scan_result["total_findings"],
        "policy_gate": policy_result,
    }


def _run_drift_self_fixture(fixture: FixtureManifest) -> dict[str, Any]:
    report_path = _required_path(fixture, "report")
    report = load_artifact(report_path)
    errors = validate_execution_report(report)
    if errors:
        raise ValueError(f"Report fixture is not schema-valid: {errors}")

    actual = compute_report_drift(report)
    expected = fixture.data["expect"]
    tolerance = float(expected.get("tolerance", 0.0001))
    passed = _approx_equal(actual["composite"], float(expected["composite"]), tolerance)

    component_expectations = expected.get("components", {})
    component_mismatches = []
    for component, expected_value in component_expectations.items():
        actual_value = actual["components"].get(component)
        if expected_value is None:
            if actual_value is not None:
                component_mismatches.append({
                    "component": component,
                    "expected": None,
                    "actual": actual_value,
                })
            continue
        if actual_value is None or not _approx_equal(float(actual_value), float(expected_value), tolerance):
            component_mismatches.append({
                "component": component,
                "expected": expected_value,
                "actual": actual_value,
            })
    passed = passed and not component_mismatches

    return {
        "passed": passed,
        "actual": actual,
        "expected": expected,
        "component_mismatches": component_mismatches,
    }


def _run_drift_compare_fixture(fixture: FixtureManifest) -> dict[str, Any]:
    baseline_path = _required_path(fixture, "baseline_report")
    candidate_path = _required_path(fixture, "candidate_report")
    baseline_report = load_artifact(baseline_path)
    candidate_report = load_artifact(candidate_path)

    baseline_errors = validate_execution_report(baseline_report)
    candidate_errors = validate_execution_report(candidate_report)
    if baseline_errors or candidate_errors:
        raise ValueError(
            f"Drift fixture reports must be schema-valid. "
            f"baseline={baseline_errors} candidate={candidate_errors}"
        )

    actual = compare_reports(baseline_report, candidate_report)
    expected = fixture.data["expect"]
    tolerance = float(expected.get("tolerance", 0.0001))

    passed = True
    mismatches = []

    if not _approx_equal(actual["comparison_drift"]["composite"], float(expected["composite"]), tolerance):
        passed = False
        mismatches.append({
            "field": "comparison_drift.composite",
            "expected": expected["composite"],
            "actual": actual["comparison_drift"]["composite"],
        })

    expected_agreement = float(expected["state_agreement"])
    if not _approx_equal(float(actual["state_agreement"]), expected_agreement, tolerance):
        passed = False
        mismatches.append({
            "field": "state_agreement",
            "expected": expected_agreement,
            "actual": actual["state_agreement"],
        })

    expected_diff_steps = sorted(int(step) for step in expected.get("difference_steps", []))
    actual_diff_steps = sorted(int(diff["step"]) for diff in actual["differences"])
    if actual_diff_steps != expected_diff_steps:
        passed = False
        mismatches.append({
            "field": "difference_steps",
            "expected": expected_diff_steps,
            "actual": actual_diff_steps,
        })

    return {
        "passed": passed,
        "actual": actual,
        "expected": expected,
        "mismatches": mismatches,
    }


def _run_provenance_fixture(fixture: FixtureManifest) -> dict[str, Any]:
    artifact_path = _required_path(fixture, "artifact")
    package = load_artifact(artifact_path)
    package_errors = validate_package(package)
    if package_errors:
        raise ValueError(f"Provenance fixture package must be schema-valid: {package_errors}")

    missing = []
    for step in package.get("methodology", {}).get("steps", []):
        if not step.get("provenance"):
            missing.append(f"methodology.steps[{step.get('step')}]")
        if not step.get("execution_semantics"):
            missing.append(f"methodology.steps[{step.get('step')}].execution_semantics")

    for idx, edge_case in enumerate(package.get("edge_cases", [])):
        if not edge_case.get("provenance"):
            missing.append(f"edge_cases[{idx}]")

    for idx, dead_end in enumerate(package.get("dead_ends", [])):
        if not dead_end.get("provenance"):
            missing.append(f"dead_ends[{idx}]")

    expected = fixture.data.get("expect", {})
    expected_steps = bool(expected.get("steps", True))
    expected_edge_cases = bool(expected.get("edge_cases", True))
    expected_dead_ends = bool(expected.get("dead_ends", True))
    expected_exec_semantics = bool(expected.get("execution_semantics", True))

    passed = True
    if expected_steps and any(item.startswith("methodology.steps[") and ".execution_semantics" not in item for item in missing):
        passed = False
    if expected_exec_semantics and any(".execution_semantics" in item for item in missing):
        passed = False
    if expected_edge_cases and any(item.startswith("edge_cases[") for item in missing):
        passed = False
    if expected_dead_ends and any(item.startswith("dead_ends[") for item in missing):
        passed = False

    return {
        "passed": passed,
        "missing": missing,
    }


def _quality_checks_for_fixture(package: dict[str, Any], adapter_name: str) -> list[dict[str, Any]]:
    if adapter_name != "mock":
        return []
    quality_checks = []
    for quality_check in package.get("output", {}).get("quality_checks", []):
        quality_checks.append({
            "check": quality_check.get("check", ""),
            "result": "pass",
            "is_blocking": bool(quality_check.get("is_blocking", False)),
            "notes": "Conformance mock execution marked this quality check as passed.",
        })
    return quality_checks


def _required_path(fixture: FixtureManifest, key: str) -> Path:
    path = fixture.resolve_path(key)
    if path is None:
        raise ValueError(f"Fixture {fixture.id} missing required path '{key}'")
    return path


def _approx_equal(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def _summary_hash(summary: dict[str, Any]) -> str:
    hash_input = _normalize_for_hash(summary)
    canonical = json.dumps(hash_input, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _normalize_for_hash(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"summary_hash", "duration_ms"}:
                continue
            normalized[key] = _normalize_for_hash(item)
        return normalized

    if isinstance(value, list):
        return [_normalize_for_hash(item) for item in value]

    if isinstance(value, str):
        return _normalize_string_for_hash(value)

    return value


def _normalize_string_for_hash(value: str) -> str:
    try:
        candidate = Path(value)
    except Exception:
        return value

    if not candidate.is_absolute():
        return value

    try:
        relative = candidate.relative_to(REPO_ROOT)
    except ValueError:
        return value

    return relative.as_posix()
