"""Policy gate for MTP packages.

Verifies that the policy envelope exists, all scans have been run,
and none have failed. This is the enterprise readiness check.
"""

from __future__ import annotations


REQUIRED_SCANS = [
    "redaction",
    "pii_scan",
    "secrets_scan",
    "client_identifier_scan",
    "regulated_content",
]


def check_policy(data: dict) -> dict:
    """Check the policy envelope of an MTP package.

    Returns a structured result with pass/fail per scan and overall gate status.
    """
    policy = data.get("policy")

    if not policy:
        return {
            "gate_passed": False,
            "reason": "No policy section found in package",
            "scans": {},
            "has_classification": False,
            "has_approval": False,
        }

    has_classification = bool(policy.get("data_classification"))

    scan_results = {}
    all_passed = True
    all_run = True

    for scan_name in REQUIRED_SCANS:
        scan = policy.get(scan_name, {})
        status = scan.get("status", "not_run")
        findings = scan.get("findings", [])

        scan_result = {
            "status": status,
            "findings_count": len(findings),
            "has_evidence": bool(scan.get("report_hash") or scan.get("evidence_ref")),
            "checker": scan.get("checker", "unknown"),
            "checker_version": scan.get("checker_version", "unknown"),
        }
        scan_results[scan_name] = scan_result

        if status == "not_run":
            all_run = False
            all_passed = False
        elif status == "failed":
            all_passed = False

    # Approval check
    approval = policy.get("approval", {})
    has_approval = bool(approval.get("approver") and approval.get("approved_at"))
    approval_required = approval.get("required", False)

    gate_passed = all_passed and all_run and has_classification
    if approval_required and not has_approval:
        gate_passed = False

    reason = "All policy checks passed" if gate_passed else []
    if not gate_passed:
        reasons = []
        if not has_classification:
            reasons.append("Missing data_classification")
        if not all_run:
            not_run = [s for s, r in scan_results.items() if r["status"] == "not_run"]
            reasons.append(f"Scans not run: {', '.join(not_run)}")
        if not all_passed:
            failed = [s for s, r in scan_results.items() if r["status"] == "failed"]
            if failed:
                reasons.append(f"Scans failed: {', '.join(failed)}")
        if approval_required and not has_approval:
            reasons.append("Approval required but not present")
        reason = "; ".join(reasons)

    return {
        "gate_passed": gate_passed,
        "reason": reason,
        "scans": scan_results,
        "has_classification": has_classification,
        "has_approval": has_approval,
        "approval_required": approval_required,
    }
