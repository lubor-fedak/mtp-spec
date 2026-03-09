"""Mock adapter for testing and demonstration.

Simulates LLM execution with deterministic responses.
No API keys required. Useful for CI/CD, demos, and conformance testing.
"""

from __future__ import annotations

import hashlib
import random
import time

from mtp_run.adapters import BaseAdapter, StepResult


class MockAdapter(BaseAdapter):
    """Deterministic mock adapter that simulates MTP step execution.

    Behavior is controlled by the step content:
    - Steps containing 'FORCE_FAIL' in action → failure
    - Steps containing 'FORCE_DEVIATE' in action → deviation
    - Steps containing 'FORCE_ESCALATE' in action → escalated
    - Steps containing 'FORCE_PARTIAL' in action → partial
    - All other steps → success

    For realistic demos, set seed for reproducible randomness.
    """

    name = "mock"

    def __init__(self, seed: int | None = None, latency: float = 0.0):
        self._rng = random.Random(seed)
        self._latency = latency

    def execute_step(
        self,
        system_context: str,
        step_prompt: str,
        data: str,
    ) -> StepResult:
        if self._latency > 0:
            time.sleep(self._latency)

        action_upper = step_prompt.upper()

        if "FORCE_FAIL" in action_upper:
            return StepResult(
                state="failure",
                validation_result="fail",
                output="",
                failure_reason="Step forced to fail via FORCE_FAIL marker.",
                notes="Mock adapter: deterministic failure.",
                raw_response="[mock: forced failure]",
            )

        if "FORCE_ESCALATE" in action_upper:
            return StepResult(
                state="escalated",
                validation_result="not_applicable",
                output="",
                notes="Mock adapter: novel situation encountered, escalating.",
                novel_situations=[{
                    "description": "Simulated novel situation requiring human decision.",
                }],
                raw_response="[mock: forced escalation]",
            )

        if "FORCE_DEVIATE" in action_upper:
            return StepResult(
                state="deviation",
                validation_result="pass",
                output=f"[mock output for step — deviated]",
                deviation_description="Mock adapter applied alternative approach.",
                deviation_reason="Simulated deviation for testing execution semantics.",
                notes="Mock adapter: deterministic deviation.",
                raw_response="[mock: forced deviation]",
            )

        if "FORCE_PARTIAL" in action_upper:
            return StepResult(
                state="partial",
                validation_result="pass",
                output=f"[mock output for step — partial]",
                notes="Mock adapter: step completed with reduced scope.",
                raw_response="[mock: forced partial]",
            )

        # Default: success
        content_hash = hashlib.md5(step_prompt.encode()).hexdigest()[:8]
        return StepResult(
            state="success",
            validation_result="pass",
            output=f"[mock output {content_hash}]",
            notes="Mock adapter: step executed successfully.",
            raw_response=f"[mock: success {content_hash}]",
        )

    def is_available(self) -> bool:
        return True

    def platform_id(self) -> str:
        return "mock-adapter-v0.4"
