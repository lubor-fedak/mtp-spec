"""Minimal drift comparison for mtp-run v0.4."""

from __future__ import annotations

from typing import Any


def compare_reports(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_steps = left["execution_report"]["steps"]
    right_steps = right["execution_report"]["steps"]

    left_by_step = {step["step"]: step for step in left_steps}
    right_by_step = {step["step"]: step for step in right_steps}
    all_step_numbers = sorted(set(left_by_step) | set(right_by_step))
    total = len(all_step_numbers)
    matches = 0
    differences = []

    for step_number in all_step_numbers:
        left_step = left_by_step.get(step_number)
        right_step = right_by_step.get(step_number)
        left_state = left_step["state"] if left_step is not None else "missing"
        right_state = right_step["state"] if right_step is not None else "missing"

        if left_state == right_state:
            matches += 1
            continue

        if right_step is None or left_step is None:
            differences.append({
                "step": step_number,
                "left_state": left_state,
                "right_state": right_state,
            })
            continue

        differences.append({
            "step": step_number,
            "left_state": left_state,
            "right_state": right_state,
        })

    agreement = (matches / total) if total else 0.0
    return {
        "matching_steps": matches,
        "total_steps": total,
        "step_state_agreement": agreement,
        "differences": differences,
    }
