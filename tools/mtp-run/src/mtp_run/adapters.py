"""Adapter registry for mtp-run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdapterStatus:
    name: str
    kind: str
    status: str
    target_platform: str
    notes: str


ADAPTER_STATUSES = [
    AdapterStatus(
        name="mock",
        kind="built-in",
        status="ready",
        target_platform="mock-runtime",
        notes="Deterministic reference adapter for schema-valid execution reports.",
    ),
    AdapterStatus(
        name="azure-openai",
        kind="platform",
        status="planned",
        target_platform="azure-openai",
        notes="Planned production adapter.",
    ),
    AdapterStatus(
        name="chatgpt",
        kind="platform",
        status="planned",
        target_platform="chatgpt",
        notes="Planned production adapter.",
    ),
    AdapterStatus(
        name="claude",
        kind="platform",
        status="planned",
        target_platform="claude",
        notes="Planned production adapter.",
    ),
]


class MockAdapter:
    """Deterministic adapter for end-to-end loop verification."""

    name = "mock"
    target_platform = "mock-runtime"

    def execute(self, package: dict[str, Any], executor_version: str) -> dict[str, Any]:
        steps = package["methodology"]["steps"]
        quality_checks = package.get("output", {}).get("quality_checks", [])

        step_reports = []
        total_duration = 0.0
        for idx, step in enumerate(steps, start=1):
            duration = round(1.0 + (idx * 0.2), 1)
            total_duration += duration
            step_reports.append({
                "step": step["step"],
                "state": "success",
                "validation_result": "pass",
                "duration_seconds": duration,
                "retries_attempted": 0,
                "notes": f"Mock adapter executed step {step['step']}: {step['name']}.",
            })

        quality_results = []
        for check in quality_checks:
            quality_results.append({
                "check": check["check"],
                "result": "pass",
                "is_blocking": bool(check.get("is_blocking", False)),
                "notes": "Mock adapter marked quality check as passed.",
            })

        return {
            "target_platform": self.target_platform,
            "executor": f"mtp-run v{executor_version}",
            "duration_seconds": round(total_duration, 1),
            "overall_status": "success",
            "overall_confidence": "high",
            "steps": step_reports,
            "edge_cases_encountered": [],
            "novel_situations": [],
            "dead_ends_prevented": [],
            "quality_checks": quality_results,
            "policy_compliance": {
                "data_leaked": False,
                "pii_detected": False,
                "notes": "Mock adapter does not ingest live data and emits reference-safe output.",
            },
            "drift_score": {
                "composite": 1.0,
                "baseline_type": "self_comparison",
                "baseline_ref": "self",
                "components": {
                    "step_fidelity": 1.0,
                    "deviation_rate": 1.0,
                    "validation_pass_rate": 1.0,
                    "output_quality": 1.0,
                    "edge_case_coverage": None,
                    "novel_situation_rate": 1.0,
                    "dead_end_avoidance": 1.0,
                },
                "weights_used": {
                    "step_fidelity": 0.25,
                    "deviation_rate": 0.15,
                    "validation_pass_rate": 0.25,
                    "output_quality": 0.20,
                    "edge_case_coverage": 0.10,
                    "novel_situation_rate": 0.03,
                    "dead_end_avoidance": 0.02,
                },
            },
        }


def get_adapter(name: str) -> MockAdapter:
    if name != "mock":
        raise ValueError(f"Adapter '{name}' is not executable in v0.4. Available executable adapter: mock")
    return MockAdapter()
