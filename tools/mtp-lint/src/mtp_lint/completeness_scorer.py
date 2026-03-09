"""Completeness scoring for MTP packages.

Evaluates how thoroughly an MTP package is documented across
provenance, rationale, execution semantics, edge cases, and dead ends.
"""

from __future__ import annotations

from typing import Any


def _has(obj: dict, key: str) -> bool:
    """Check if key exists and has a non-empty value."""
    val = obj.get(key)
    if val is None:
        return False
    if isinstance(val, str) and not val.strip():
        return False
    if isinstance(val, list) and len(val) == 0:
        return False
    return True


def _check_provenance(prov: dict | None) -> dict:
    """Score a provenance block."""
    if prov is None:
        return {"present": False, "has_source_ref": False, "has_confidence": False, "has_notes": False}
    return {
        "present": True,
        "has_source_ref": _has(prov, "source_ref"),
        "has_confidence": _has(prov, "confidence"),
        "has_notes": _has(prov, "notes"),
    }


def score_package(data: dict) -> dict:
    """Compute completeness score for an MTP package.

    Returns a structured report with per-area scores and a composite score.
    """
    checks: list[dict] = []
    version = data.get("mtp_version", "0.1")

    # --- Intent completeness ---
    intent = data.get("intent", {})
    checks.append({"area": "intent", "check": "goal_present", "passed": _has(intent, "goal")})
    checks.append({"area": "intent", "check": "context_present", "passed": _has(intent, "context")})
    checks.append({"area": "intent", "check": "success_criteria_present", "passed": _has(intent, "success_criteria")})
    checks.append({"area": "intent", "check": "non_goals_present", "passed": _has(intent, "non_goals")})

    # --- Input completeness ---
    inp = data.get("input", {})
    checks.append({"area": "input", "check": "description_present", "passed": _has(inp, "description")})
    checks.append({"area": "input", "check": "schema_present", "passed": _has(inp, "schema")})
    checks.append({"area": "input", "check": "assumptions_present", "passed": _has(inp, "assumptions")})

    # --- Methodology completeness ---
    meth = data.get("methodology", {})
    steps = meth.get("steps", [])
    checks.append({"area": "methodology", "check": "approach_present", "passed": _has(meth, "approach")})
    checks.append({"area": "methodology", "check": "has_steps", "passed": len(steps) > 0})

    step_details = []
    for step in steps:
        step_num = step.get("step", "?")
        detail = {
            "step": step_num,
            "has_rationale": _has(step, "rationale"),
            "has_validation": _has(step, "validation"),
            "has_execution_semantics": _has(step, "execution_semantics"),
            "provenance": _check_provenance(step.get("provenance")),
        }
        step_details.append(detail)

        checks.append({"area": f"step_{step_num}", "check": "rationale_present", "passed": detail["has_rationale"]})
        checks.append({"area": f"step_{step_num}", "check": "validation_present", "passed": detail["has_validation"]})

        if version >= "0.2":
            checks.append({"area": f"step_{step_num}", "check": "execution_semantics_present", "passed": detail["has_execution_semantics"]})
            checks.append({"area": f"step_{step_num}", "check": "provenance_present", "passed": detail["provenance"]["present"]})
            if detail["provenance"]["present"]:
                checks.append({"area": f"step_{step_num}", "check": "provenance_has_source_ref", "passed": detail["provenance"]["has_source_ref"]})
                checks.append({"area": f"step_{step_num}", "check": "provenance_has_confidence", "passed": detail["provenance"]["has_confidence"]})

    # --- Edge cases ---
    edge_cases = data.get("edge_cases", [])
    checks.append({"area": "edge_cases", "check": "has_edge_cases", "passed": len(edge_cases) > 0})
    for i, ec in enumerate(edge_cases):
        checks.append({"area": f"edge_case_{i}", "check": "has_rationale", "passed": _has(ec, "rationale")})
        checks.append({"area": f"edge_case_{i}", "check": "has_severity", "passed": _has(ec, "severity")})
        if version >= "0.2":
            checks.append({"area": f"edge_case_{i}", "check": "has_provenance", "passed": _has(ec, "provenance")})

    # --- Dead ends ---
    dead_ends = data.get("dead_ends", [])
    checks.append({"area": "dead_ends", "check": "has_dead_ends", "passed": len(dead_ends) > 0})
    for i, de in enumerate(dead_ends):
        checks.append({"area": f"dead_end_{i}", "check": "has_reason", "passed": _has(de, "reason")})
        checks.append({"area": f"dead_end_{i}", "check": "has_lesson", "passed": _has(de, "lesson")})
        if version >= "0.2":
            checks.append({"area": f"dead_end_{i}", "check": "has_provenance", "passed": _has(de, "provenance")})

    # --- Output ---
    output = data.get("output", {})
    checks.append({"area": "output", "check": "description_present", "passed": _has(output, "description")})
    checks.append({"area": "output", "check": "schema_present", "passed": _has(output, "schema")})
    checks.append({"area": "output", "check": "quality_checks_present", "passed": _has(output, "quality_checks")})

    # --- Adaptation ---
    adaptation = data.get("adaptation", {})
    checks.append({"area": "adaptation", "check": "flexibility_present", "passed": _has(adaptation, "flexibility")})
    checks.append({"area": "adaptation", "check": "fixed_elements_present", "passed": _has(adaptation, "fixed_elements")})
    checks.append({"area": "adaptation", "check": "target_requirements_present", "passed": _has(adaptation, "target_requirements")})

    # --- Policy (v0.2+) ---
    if version >= "0.2":
        policy = data.get("policy", {})
        checks.append({"area": "policy", "check": "policy_present", "passed": bool(policy)})
        checks.append({"area": "policy", "check": "data_classification_present", "passed": _has(policy, "data_classification")})

        for scan_name in ["redaction", "pii_scan", "secrets_scan", "client_identifier_scan", "regulated_content"]:
            scan = policy.get(scan_name, {})
            status = scan.get("status", "not_run")
            checks.append({
                "area": "policy",
                "check": f"{scan_name}_run",
                "passed": status != "not_run",
            })

    # --- Compute scores ---
    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    score = round(passed / total, 3) if total > 0 else 0.0

    # Area breakdown
    areas: dict[str, dict] = {}
    for check in checks:
        area = check["area"].split("_")[0] if check["area"].startswith(("step_", "edge_case_", "dead_end_")) else check["area"]
        if area not in areas:
            areas[area] = {"total": 0, "passed": 0}
        areas[area]["total"] += 1
        if check["passed"]:
            areas[area]["passed"] += 1
    for area in areas:
        a = areas[area]
        a["score"] = round(a["passed"] / a["total"], 3) if a["total"] > 0 else 0.0

    # Rating
    if score >= 0.95:
        rating = "excellent"
    elif score >= 0.80:
        rating = "good"
    elif score >= 0.60:
        rating = "fair"
    else:
        rating = "poor"

    return {
        "composite_score": score,
        "rating": rating,
        "total_checks": total,
        "passed_checks": passed,
        "failed_checks": total - passed,
        "area_scores": areas,
        "checks": checks,
        "step_details": step_details,
    }
