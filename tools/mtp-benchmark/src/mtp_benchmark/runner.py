"""Benchmark suite execution for mtp-benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mtp_benchmark import __version__
from mtp_benchmark.artifacts import dump_yaml, utc_now_iso, validate_artifact
from mtp_run.adapters import get_adapter
from mtp_run.drift import compare_reports
from mtp_run.executor import execute_package
from mtp_run.io_utils import load_artifact, validate_execution_report, validate_package
from mtp_run.report_builder import build_execution_report, mock_quality_checks


def run_suite(suite: dict[str, Any], suite_path: Path, output_dir: Path, strict: bool = False) -> dict[str, Any]:
    errors = validate_artifact(suite)
    if errors:
        raise ValueError(f"Benchmark suite is not schema-valid: {errors}")

    suite_body = suite["suite"]
    package_path = _resolve_ref(suite_path, suite_body["package_ref"])
    data_path = _resolve_ref(suite_path, suite_body["data_ref"])
    baseline_path = _resolve_ref(suite_path, suite_body["baseline_report_ref"])

    package = load_artifact(package_path)
    package_errors = validate_package(package)
    if package_errors:
        raise ValueError(f"Benchmark package is not schema-valid: {package_errors}")
    baseline_report = load_artifact(baseline_path)
    baseline_errors = validate_execution_report(baseline_report)
    if baseline_errors:
        raise ValueError(f"Baseline report is not schema-valid: {baseline_errors}")

    data = data_path.read_text(encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    suite_slug = _slugify(str(suite_body["id"]))

    adapter_results = []
    for adapter_spec in suite_body["adapters"]:
        result = _run_adapter_case(
            adapter_spec=adapter_spec,
            package=package,
            data=data,
            baseline_report=baseline_report,
            output_dir=output_dir,
            suite_slug=suite_slug,
            strict=strict,
        )
        adapter_results.append(result)

    summary = _build_summary(adapter_results)
    result = {
        "mtp_benchmark_version": "0.7",
        "benchmark_result": {
            "suite_id": suite_body["id"],
            "suite_name": suite_body["name"],
            "generated_at": utc_now_iso(),
            "package_ref": suite_body["package_ref"],
            "data_ref": suite_body["data_ref"],
            "baseline_report_ref": suite_body["baseline_report_ref"],
            "adapter_results": adapter_results,
            "summary": summary,
        },
    }
    result_errors = validate_artifact(result)
    if result_errors:
        raise ValueError(f"Generated benchmark result is not schema-valid: {result_errors}")
    return result


def create_certification(
    benchmark_result: dict[str, Any],
    benchmark_result_ref: str,
    adapter_name: str,
    variant: str = "default",
) -> dict[str, Any]:
    errors = validate_artifact(benchmark_result)
    if errors:
        raise ValueError(f"Benchmark result is not schema-valid: {errors}")

    result_body = benchmark_result["benchmark_result"]
    selected = None
    for entry in result_body["adapter_results"]:
        if entry["adapter"] == adapter_name and entry["variant"] == variant:
            selected = entry
            break
    if selected is None:
        raise ValueError(f"No adapter result found for adapter='{adapter_name}' variant='{variant}'.")

    if not selected["available"] or not selected["executed"]:
        status = "skipped"
    elif selected["passed_thresholds"]:
        status = "certified"
    else:
        status = "not_certified"

    artifact = {
        "mtp_adapter_certification_version": "0.7",
        "adapter_certification": {
            "adapter": selected["adapter"],
            "variant": selected["variant"],
            "model": selected.get("model"),
            "suite_id": result_body["suite_id"],
            "benchmark_result_ref": benchmark_result_ref,
            "status": status,
            "certified_at": utc_now_iso(),
            "thresholds": selected["thresholds"],
            "achieved": {
                "available": selected["available"],
                "executed": selected["executed"],
                "passed_thresholds": selected["passed_thresholds"],
                "overall_status": selected.get("overall_status"),
                "comparison_drift": selected.get("comparison_drift"),
                "state_agreement": selected.get("state_agreement"),
            },
        },
    }
    artifact_errors = validate_artifact(artifact)
    if artifact_errors:
        raise ValueError(f"Generated adapter certification is not schema-valid: {artifact_errors}")
    return artifact


def write_result_bundle(result: dict[str, Any], output_dir: Path) -> Path:
    suite_slug = _slugify(str(result["benchmark_result"]["suite_id"]))
    result_path = output_dir / f"{suite_slug}-result-v0.7.yaml"
    dump_yaml(result_path, result)
    return result_path


def _run_adapter_case(
    adapter_spec: dict[str, Any],
    package: dict[str, Any],
    data: str,
    baseline_report: dict[str, Any],
    output_dir: Path,
    suite_slug: str,
    strict: bool,
) -> dict[str, Any]:
    adapter_name = str(adapter_spec["name"])
    model = adapter_spec.get("model")
    azure = bool(adapter_spec.get("azure", False))
    required = bool(adapter_spec.get("required", False))
    variant = "azure" if azure else "default"
    thresholds = adapter_spec["thresholds"]
    adapter = get_adapter(adapter_name, model=model, azure=azure)

    if not adapter.is_available():
        passed_thresholds = not required and not strict
        return {
            "adapter": adapter_name,
            "variant": variant,
            "model": model,
            "available": False,
            "executed": False,
            "required": required,
            "skipped_reason": "adapter_not_available",
            "thresholds": thresholds,
            "passed_thresholds": passed_thresholds,
        }

    raw_results = execute_package(package=package, data=data, adapter=adapter)
    report = build_execution_report(
        package=package,
        raw_results=raw_results,
        duration_seconds=0.0,
        executor_id=f"mtp-benchmark v{__version__}",
        quality_checks=mock_quality_checks(package) if adapter_name == "mock" else [],
        baseline_ref=None,
        baseline_type=None,
        baseline_report=baseline_report,
    )
    report_errors = validate_execution_report(report)
    report_slug = adapter_name if variant == "default" else f"{adapter_name}-{variant}"
    report_path = output_dir / f"{suite_slug}-{report_slug}-report-v0.7.yaml"
    dump_yaml(report_path, report)

    comparison = compare_reports(baseline_report, report)
    overall_status = report["execution_report"]["overall_status"]
    self_drift = report["execution_report"]["drift_score"]["composite"]
    comparison_drift = comparison["comparison_drift"]["composite"]
    state_agreement = comparison["state_agreement"]
    allowed_statuses = set(thresholds["allowed_statuses"])
    passed_thresholds = (
        not report_errors
        and overall_status in allowed_statuses
        and comparison_drift >= float(thresholds["min_comparison_drift"])
        and state_agreement >= float(thresholds["min_state_agreement"])
    )

    return {
        "adapter": adapter_name,
        "variant": variant,
        "model": model,
        "available": True,
        "executed": True,
        "required": required,
        "report_ref": report_path.name,
        "report_valid": not report_errors,
        "overall_status": overall_status,
        "self_drift": self_drift,
        "comparison_drift": comparison_drift,
        "state_agreement": state_agreement,
        "difference_steps": [diff["step"] for diff in comparison["differences"]],
        "thresholds": thresholds,
        "passed_thresholds": passed_thresholds,
    }


def _build_summary(adapter_results: list[dict[str, Any]]) -> dict[str, Any]:
    executed = sum(1 for result in adapter_results if result["executed"])
    skipped = sum(1 for result in adapter_results if not result["executed"])
    passed = sum(1 for result in adapter_results if result["executed"] and result["passed_thresholds"])
    failed = sum(
        1
        for result in adapter_results
        if (result["executed"] and not result["passed_thresholds"])
        or (not result["executed"] and not result["passed_thresholds"])
    )
    suite_passed = all(result["passed_thresholds"] for result in adapter_results)
    return {
        "total_adapters": len(adapter_results),
        "executed": executed,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "suite_passed": suite_passed,
    }


def _resolve_ref(base_path: Path, ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    return base_path.parent / path


def _slugify(value: str) -> str:
    chars = [ch.lower() if ch.isalnum() else "-" for ch in value]
    compact = "".join(chars)
    while "--" in compact:
        compact = compact.replace("--", "-")
    return compact.strip("-") or "benchmark"
