"""Execution report construction for mtp-run."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from mtp_run.io_utils import utc_now_iso


def _compute_hash(report_body: dict[str, Any]) -> str:
    canonical = json.dumps(report_body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def build_execution_report(package: dict[str, Any], runtime_output: dict[str, Any]) -> dict[str, Any]:
    execution_report = {
        "mtp_package_id": package["package"]["id"],
        "mtp_package_version": package["package"]["version"],
        "mtp_spec_version": package["mtp_version"],
        "target_platform": runtime_output["target_platform"],
        "executor": runtime_output["executor"],
        "timestamp": utc_now_iso(),
        "duration_seconds": runtime_output["duration_seconds"],
        "overall_status": runtime_output["overall_status"],
        "overall_confidence": runtime_output["overall_confidence"],
        "steps": runtime_output["steps"],
        "edge_cases_encountered": runtime_output["edge_cases_encountered"],
        "novel_situations": runtime_output["novel_situations"],
        "dead_ends_prevented": runtime_output["dead_ends_prevented"],
        "quality_checks": runtime_output["quality_checks"],
        "policy_compliance": runtime_output["policy_compliance"],
        "drift_score": runtime_output["drift_score"],
    }
    execution_report["report_hash"] = _compute_hash(execution_report)
    return {"execution_report": execution_report}
