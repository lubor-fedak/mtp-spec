"""Report generation for mtp-lint results."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any

from mtp_lint import __version__


def generate_report(
    file_path: str,
    artifact_type: str,
    version: str,
    schema_errors: list[dict],
    redaction_results: dict | None,
    completeness_results: dict | None,
    policy_results: dict | None,
) -> dict:
    """Assemble all lint results into a single structured report."""

    schema_passed = len(schema_errors) == 0
    redaction_passed = redaction_results["passed"] if redaction_results else None
    completeness_score = completeness_results["composite_score"] if completeness_results else None
    policy_passed = policy_results["gate_passed"] if policy_results else None

    # Overall status
    if not schema_passed:
        overall = "fail"
    elif redaction_passed is False:
        overall = "fail"
    elif policy_passed is False:
        overall = "fail"
    elif completeness_score is not None and completeness_score < 0.6:
        overall = "warn"
    else:
        overall = "pass"

    report = {
        "mtp_lint_version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file": file_path,
        "artifact_type": artifact_type,
        "mtp_version": version,
        "overall_status": overall,
        "summary": {
            "schema_valid": schema_passed,
            "schema_error_count": len(schema_errors),
            "redaction_passed": redaction_passed,
            "redaction_finding_count": redaction_results["total_findings"] if redaction_results else 0,
            "completeness_score": completeness_score,
            "completeness_rating": completeness_results["rating"] if completeness_results else None,
            "policy_gate_passed": policy_passed,
        },
        "details": {
            "schema_errors": schema_errors,
            "redaction": redaction_results,
            "completeness": completeness_results,
            "policy": policy_results,
        },
    }

    # Add report hash
    content = json.dumps(report, sort_keys=True, default=str)
    report["report_hash"] = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"

    return report


def format_text(report: dict) -> str:
    """Format a lint report as human-readable text."""
    lines = []
    s = report["summary"]

    lines.append(f"MTP Lint Report — {report['file']}")
    lines.append(f"{'=' * 60}")
    lines.append(f"Artifact:     {report['artifact_type']} (MTP v{report['mtp_version']})")
    lines.append(f"Overall:      {report['overall_status'].upper()}")
    lines.append("")

    # Schema
    if s["schema_valid"]:
        lines.append(f"  Schema:       PASS")
    else:
        lines.append(f"  Schema:       FAIL ({s['schema_error_count']} errors)")
        for err in report["details"]["schema_errors"][:10]:
            lines.append(f"    - [{err['path']}] {err['message']}")
        if s["schema_error_count"] > 10:
            lines.append(f"    ... and {s['schema_error_count'] - 10} more")

    # Redaction
    if s["redaction_passed"] is not None:
        if s["redaction_passed"]:
            lines.append(f"  Redaction:    PASS")
        else:
            lines.append(f"  Redaction:    FAIL ({s['redaction_finding_count']} findings)")
            for f in report["details"]["redaction"]["findings"][:10]:
                lines.append(f"    - [{f['severity'].upper()}] {f['category']}/{f['pattern']} at {f['path']}")

    # Completeness
    if s["completeness_score"] is not None:
        pct = int(s["completeness_score"] * 100)
        lines.append(f"  Completeness: {pct}% ({s['completeness_rating']})")
        comp = report["details"]["completeness"]
        failed = [c for c in comp["checks"] if not c["passed"]]
        if failed:
            lines.append(f"    Missing ({len(failed)}):")
            for c in failed[:15]:
                lines.append(f"    - {c['area']}: {c['check']}")
            if len(failed) > 15:
                lines.append(f"    ... and {len(failed) - 15} more")

    # Policy
    if s["policy_gate_passed"] is not None:
        if s["policy_gate_passed"]:
            lines.append(f"  Policy gate:  PASS")
        else:
            reason = report["details"]["policy"]["reason"]
            lines.append(f"  Policy gate:  FAIL — {reason}")

    lines.append("")
    lines.append(f"Report hash: {report.get('report_hash', 'n/a')}")

    return "\n".join(lines)
