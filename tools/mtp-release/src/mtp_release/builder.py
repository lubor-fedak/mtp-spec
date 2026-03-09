"""Builders for v1.0 release artifacts."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from mtp_release.artifacts import REPO_ROOT, utc_now_iso, validate_artifact


TOOL_DIRS = [
    "mtp-lint",
    "mtp-run",
    "mtp-conformance",
    "mtp-registry",
    "mtp-extract",
    "mtp-benchmark",
    "mtp-release",
]


def build_provider_matrix(
    benchmark_result: dict[str, Any],
    benchmark_result_ref: str,
    certifications: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    if "benchmark_result" not in benchmark_result:
        raise ValueError("Expected a benchmark result artifact with top-level 'benchmark_result'.")
    result_body = benchmark_result["benchmark_result"]
    cert_index = {
        (
            cert["adapter_certification"]["adapter"],
            cert["adapter_certification"]["variant"],
        ): (ref, cert)
        for ref, cert in certifications
    }

    entries: list[dict[str, Any]] = []
    for adapter_result in result_body["adapter_results"]:
        key = (adapter_result["adapter"], adapter_result["variant"])
        certification_ref, certification = cert_index.get(key, (None, None))
        if certification is None:
            if adapter_result["executed"]:
                status = "not_certified"
            elif adapter_result.get("available"):
                status = "skipped"
            else:
                status = "not_evaluated"
        else:
            status = certification["adapter_certification"]["status"]

        entry = {
            "provider": adapter_result["adapter"],
            "variant": adapter_result["variant"],
            "status": status,
            "benchmark_result_ref": benchmark_result_ref,
        }
        executed = bool(adapter_result.get("executed"))
        optional_fields = {
            "model": adapter_result.get("model"),
            "certification_ref": certification_ref,
            "available": adapter_result.get("available"),
            "executed": adapter_result.get("executed"),
            "passed_thresholds": adapter_result.get("passed_thresholds") if executed else None,
            "comparison_drift": adapter_result.get("comparison_drift"),
            "state_agreement": adapter_result.get("state_agreement"),
            "overall_status": adapter_result.get("overall_status"),
        }
        for field, value in optional_fields.items():
            if value is not None:
                entry[field] = value
        entries.append(entry)

    matrix = {
        "mtp_provider_matrix_version": "1.0",
        "provider_matrix": {
            "generated_at": utc_now_iso(),
            "benchmark_suite_id": result_body["suite_id"],
            "benchmark_result_ref": benchmark_result_ref,
            "entries": entries,
            "summary": {
                "total": len(entries),
                "certified": sum(1 for entry in entries if entry["status"] == "certified"),
                "not_certified": sum(1 for entry in entries if entry["status"] == "not_certified"),
                "skipped": sum(1 for entry in entries if entry["status"] == "skipped"),
                "not_evaluated": sum(1 for entry in entries if entry["status"] == "not_evaluated"),
            },
        },
    }
    errors = validate_artifact(matrix)
    if errors:
        raise ValueError(f"Generated provider matrix is not schema-valid: {errors}")
    return matrix


def build_compatibility_contract(
    release_version: str,
    provider_matrix_ref: str,
    conformance_level: str,
    architecture_ref: str,
    core_spec_ref: str,
    registry_spec_ref: str,
    compatibility_spec_ref: str,
    conformance_summary_hash: str | None = None,
    conformance_summary_ref: str | None = None,
) -> dict[str, Any]:
    tooling = [_read_tool_version(name) for name in TOOL_DIRS]
    contract = {
        "mtp_compatibility_contract_version": "1.0",
        "compatibility_contract": {
            "release": {
                "version": release_version,
                "status": "production",
                "generated_at": utc_now_iso(),
            },
            "normative_layers": {
                "package_schema": "0.2",
                "execution_report_schema": "0.2",
                "registry_extension": "0.6",
                "benchmark_artifacts": "0.7",
                "release_artifacts": "1.0",
                "key_provider_manifest": "1.0",
            },
            "tooling": tooling,
            "compatibility": {
                "guarantees": [
                    "MTP 1.0 keeps the stable package and execution-report contract on v0.2 artifacts.",
                    "Registry trust artifacts remain detached from core packages and reports.",
                    "Production release evidence requires conformance plus a provider certification matrix.",
                ],
                "backward_compatibility": {
                    "accepts_package_versions": ["0.1", "0.2"],
                    "emits_package_version": "0.2",
                    "accepts_execution_report_versions": ["0.2"],
                    "registry_signature_profiles": ["hmac-sha256", "ed25519"],
                },
                "deprecation_policy": (
                    "Legacy v0.1 packages remain readable for validation and migration, "
                    "but all newly generated packages, reports, and release artifacts must use the stable v0.2/v0.6/v0.7/v1.0 contracts."
                ),
            },
            "evidence": {
                "conformance_level": conformance_level,
                "provider_matrix_ref": provider_matrix_ref,
            },
            "documentation": {
                "core_spec_ref": core_spec_ref,
                "registry_spec_ref": registry_spec_ref,
                "architecture_ref": architecture_ref,
                "compatibility_spec_ref": compatibility_spec_ref,
            },
        },
    }
    if conformance_summary_hash:
        contract["compatibility_contract"]["evidence"]["conformance_summary_hash"] = conformance_summary_hash
    if conformance_summary_ref:
        contract["compatibility_contract"]["evidence"]["conformance_summary_ref"] = conformance_summary_ref

    errors = validate_artifact(contract)
    if errors:
        raise ValueError(f"Generated compatibility contract is not schema-valid: {errors}")
    return contract


def _read_tool_version(tool_name: str) -> dict[str, str]:
    pyproject = REPO_ROOT / "tools" / tool_name / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return {
        "name": data["project"]["name"],
        "version": data["project"]["version"],
    }
