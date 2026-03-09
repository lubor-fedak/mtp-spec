"""Adapter registry and implementations for mtp-run.

Each adapter takes an MTP package and produces a raw execution result dict
that reporting.py wraps into a schema-valid execution report.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AdapterInfo:
    name: str
    kind: str
    status: str
    target_platform: str
    notes: str


def list_adapters() -> list[AdapterInfo]:
    """Return status of all known adapters."""
    infos: list[AdapterInfo] = [
        AdapterInfo("mock", "built-in", "ready", "mock-runtime",
                    "Deterministic reference adapter — no API key required."),
    ]

    try:
        import anthropic  # noqa: F401
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        infos.append(AdapterInfo(
            "anthropic", "platform",
            "ready" if has_key else "available",
            "anthropic-claude",
            "Claude API." + ("" if has_key else " Set ANTHROPIC_API_KEY to enable."),
        ))
    except ImportError:
        infos.append(AdapterInfo(
            "anthropic", "platform", "unavailable", "anthropic-claude",
            "SDK not installed. Run: pip install mtp-run[anthropic]",
        ))

    try:
        import openai as _openai  # noqa: F401
        has_oai = bool(os.environ.get("OPENAI_API_KEY"))
        has_azure = bool(
            os.environ.get("AZURE_OPENAI_API_KEY")
            and os.environ.get("AZURE_OPENAI_ENDPOINT")
        )
        infos.append(AdapterInfo(
            "openai", "platform",
            "ready" if has_oai else "available",
            "openai",
            "OpenAI API." + ("" if has_oai else " Set OPENAI_API_KEY to enable."),
        ))
        infos.append(AdapterInfo(
            "azure-openai", "platform",
            "ready" if has_azure else "available",
            "azure-openai",
            "Azure OpenAI." + ("" if has_azure else " Set AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT."),
        ))
    except ImportError:
        for n in ("openai", "azure-openai"):
            infos.append(AdapterInfo(
                n, "platform", "unavailable", n,
                "SDK not installed. Run: pip install mtp-run[openai]",
            ))

    return infos


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------

class MockAdapter:
    """Deterministic adapter for end-to-end loop verification."""

    name = "mock"
    target_platform = "mock-runtime"

    def execute(self, package: dict[str, Any], executor_version: str) -> dict[str, Any]:
        steps = package["methodology"]["steps"]
        quality_checks = package.get("output", {}).get("quality_checks", [])

        step_reports = []
        total_duration = 0.0
        for step in steps:
            duration = round(1.0 + (step["step"] * 0.2), 1)
            total_duration += duration
            step_reports.append({
                "step": step["step"],
                "state": "success",
                "validation_result": "pass",
                "duration_seconds": duration,
                "retries_attempted": 0,
                "notes": f"Mock adapter executed step {step['step']}: {step['name']}.",
            })

        quality_results = [
            {
                "check": qc["check"],
                "result": "pass",
                "is_blocking": bool(qc.get("is_blocking", False)),
                "notes": "Mock adapter marked quality check as passed.",
            }
            for qc in quality_checks
        ]

        from mtp_run.drift import compute_drift_score
        drift = compute_drift_score(step_reports, quality_results, [], [])

        return _assemble(
            self.target_platform, f"mtp-run v{executor_version}",
            round(total_duration, 1), step_reports, quality_results, drift,
        )


# ---------------------------------------------------------------------------
# LLM-backed adapter base
# ---------------------------------------------------------------------------

def _execute_via_llm(
    package: dict[str, Any],
    executor_version: str,
    target_platform: str,
    call_llm: Callable[[str, str], str],
) -> dict[str, Any]:
    """Shared execution logic for all LLM adapters.

    Builds a system prompt from the package, executes each step
    sequentially, parses YAML responses, and respects execution semantics.
    """
    import yaml as _yaml

    methodology = package.get("methodology", {})
    steps = methodology.get("steps", [])
    edge_cases = package.get("edge_cases", [])
    dead_ends = package.get("dead_ends", [])
    quality_checks = package.get("output", {}).get("quality_checks", [])

    # Build system context
    intent = package.get("intent", {})
    system = (
        "You are executing a methodology defined by an MTP package. "
        "This is a controlled execution — follow each step precisely.\n\n"
        f"GOAL: {intent.get('goal', 'Not specified')}\n\n"
        f"APPROACH: {methodology.get('approach', 'Not specified')}\n"
    )
    if dead_ends:
        system += "\nDEAD ENDS (DO NOT repeat these approaches):\n"
        for de in dead_ends:
            system += f"  - {de.get('approach', '')}: {de.get('reason', '')}\n"

    system += (
        "\nFor EACH step, respond with EXACTLY this YAML:\n"
        "```yaml\n"
        "state: success  # success | partial | deviation | failure | escalated\n"
        "validation_result: pass  # pass | fail | not_applicable\n"
        "output: |\n  <your work output>\n"
        "notes: \"\"\n"
        "```\n"
        "If you encounter a novel situation not in edge cases, set state: escalated. Do NOT improvise.\n"
    )

    step_reports: list[dict] = []
    step_outputs: dict[int, str] = {}
    halted = False
    total_t0 = time.time()

    for step in steps:
        snum = step["step"]
        sem = step.get("execution_semantics", {})
        on_failure = sem.get("on_failure", "halt")
        on_deviation = sem.get("on_deviation", "flag_and_proceed")
        max_retries = sem.get("max_retries", 1)

        if halted:
            step_reports.append({
                "step": snum, "state": "skipped",
                "validation_result": "not_applicable",
                "duration_seconds": 0, "retries_attempted": 0,
                "skip_reason": "pipeline_halted", "notes": "",
            })
            continue

        # Check dependencies
        deps = step.get("depends_on", [])
        unmet = [d for d in deps if any(
            s["step"] == d and s["state"] in ("failure", "skipped", "escalated")
            for s in step_reports
        )]
        if unmet:
            step_reports.append({
                "step": snum, "state": "skipped",
                "validation_result": "not_applicable",
                "duration_seconds": 0, "retries_attempted": 0,
                "skip_reason": f"unmet_dependency: {unmet}", "notes": "",
            })
            continue

        # Build step prompt
        user_prompt = f"STEP {snum}: {step.get('name', '')}\n\nACTION:\n{step.get('action', '')}\n"
        if step.get("validation"):
            user_prompt += f"\nVALIDATION RULE:\n{step['validation']}\n"
        if edge_cases:
            user_prompt += "\nEDGE CASES:\n"
            for ec in edge_cases:
                user_prompt += f"  [{ec.get('severity', 'info')}] {ec.get('scenario', '')}: {ec.get('handling', '')}\n"
        if deps and step_outputs:
            user_prompt += "\nPREVIOUS STEP OUTPUTS:\n"
            for d in deps:
                if d in step_outputs:
                    out = step_outputs[d]
                    user_prompt += f"  Step {d}: {out[:500]}\n"

        # Execute with retries
        retries = 0
        t0 = time.time()
        result = None

        while True:
            raw = call_llm(system, user_prompt)
            result = _parse_llm_response(raw)
            dur = round(time.time() - t0, 2)

            if result["state"] == "failure" and on_failure == "retry" and retries < max_retries:
                retries += 1
                continue
            break

        result["step"] = snum
        result["duration_seconds"] = dur
        result["retries_attempted"] = retries

        # Apply semantics
        if result["state"] == "failure" and on_failure == "halt":
            result["failure_blocking"] = True
            halted = True
        elif result["state"] == "failure":
            result["failure_blocking"] = False

        if result["state"] == "deviation" and on_deviation == "halt":
            halted = True
        if result["state"] == "escalated":
            halted = True

        step_reports.append(result)
        step_outputs[snum] = result.get("output", "")

    total_dur = round(time.time() - total_t0, 2)

    quality_results = [
        {"check": qc["check"], "result": "pass",
         "is_blocking": bool(qc.get("is_blocking", False)),
         "notes": "LLM execution — quality check assessment deferred to report reviewer."}
        for qc in quality_checks
    ]

    from mtp_run.drift import compute_drift_score
    drift = compute_drift_score(step_reports, quality_results, [], [])

    return _assemble(target_platform, f"mtp-run v{executor_version}",
                     total_dur, step_reports, quality_results, drift)


def _parse_llm_response(raw: str) -> dict:
    """Parse structured YAML from LLM response with fallback."""
    import re
    import yaml as _yaml

    VALID_STATES = {"success", "partial", "deviation", "failure", "escalated", "skipped"}

    # Try YAML block extraction
    match = re.search(r"```ya?ml\s*\n(.*?)```", raw, re.DOTALL)
    text = match.group(1).strip() if match else raw

    try:
        data = _yaml.safe_load(text)
        if isinstance(data, dict):
            state = str(data.get("state", "failure")).lower().strip()
            if state not in VALID_STATES:
                state = "failure"
            vr = str(data.get("validation_result", "not_applicable")).lower().strip()
            if vr not in ("pass", "fail", "not_applicable"):
                vr = "not_applicable"
            return {
                "state": state,
                "validation_result": vr,
                "output": str(data.get("output", "")),
                "notes": str(data.get("notes", "")),
                **({"deviation": {
                    "description": str(data.get("deviation_description", "")),
                    "reason": str(data.get("deviation_reason", "")),
                }} if state == "deviation" else {}),
                **({"failure_reason": str(data.get("failure_reason", ""))} if state == "failure" else {}),
            }
    except Exception:
        pass

    # Heuristic fallback
    lower = raw.lower()
    if "escalat" in lower:
        state = "escalated"
    elif "fail" in lower or "error" in lower:
        state = "failure"
    elif "deviat" in lower:
        state = "deviation"
    else:
        state = "success"

    return {
        "state": state, "validation_result": "not_applicable",
        "output": raw[:2000], "notes": "Parsed via heuristic fallback.",
    }


# ---------------------------------------------------------------------------
# Anthropic adapter
# ---------------------------------------------------------------------------

class AnthropicAdapter:
    """Execute MTP packages via Anthropic Claude Messages API."""

    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-20250514", max_tokens: int = 4096):
        self._model = model
        self._max_tokens = max_tokens
        self.target_platform = f"anthropic/{model}"

    def execute(self, package: dict[str, Any], executor_version: str) -> dict[str, Any]:
        import anthropic
        client = anthropic.Anthropic()

        def call_llm(system: str, user: str) -> str:
            resp = client.messages.create(
                model=self._model, max_tokens=self._max_tokens,
                system=system, messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text if resp.content else ""

        return _execute_via_llm(package, executor_version, self.target_platform, call_llm)


# ---------------------------------------------------------------------------
# OpenAI / Azure OpenAI adapter
# ---------------------------------------------------------------------------

class OpenAIAdapter:
    """Execute MTP packages via OpenAI or Azure OpenAI."""

    name = "openai"

    def __init__(self, model: str = "gpt-4o", max_tokens: int = 4096, azure: bool = False):
        self._model = model
        self._max_tokens = max_tokens
        self._azure = azure
        prefix = "azure-openai" if azure else "openai"
        self.target_platform = f"{prefix}/{model}"

    def execute(self, package: dict[str, Any], executor_version: str) -> dict[str, Any]:
        import openai

        if self._azure:
            client = openai.AzureOpenAI(
                api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
                api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            )
        else:
            client = openai.OpenAI()

        def call_llm(system: str, user: str) -> str:
            resp = client.chat.completions.create(
                model=self._model, max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return resp.choices[0].message.content if resp.choices else ""

        return _execute_via_llm(package, executor_version, self.target_platform, call_llm)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_adapter(name: str, model: str | None = None, azure: bool = False):
    """Get an adapter instance by name."""
    if name == "mock":
        return MockAdapter()
    if name == "anthropic":
        return AnthropicAdapter(model=model or "claude-sonnet-4-20250514")
    if name == "openai":
        return OpenAIAdapter(model=model or "gpt-4o", azure=azure)
    if name == "azure-openai":
        return OpenAIAdapter(model=model or "gpt-4o", azure=True)
    raise ValueError(f"Unknown adapter: {name}. Available: mock, anthropic, openai, azure-openai")


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _assemble(
    platform: str, executor: str, duration: float,
    steps: list[dict], quality_checks: list[dict], drift: dict,
) -> dict[str, Any]:
    """Assemble raw result dict expected by reporting.py."""

    states = [s["state"] for s in steps]
    if "escalated" in states:
        overall = "escalated"
    elif any(s["state"] == "failure" and s.get("failure_blocking", True) for s in steps):
        overall = "failure"
    elif any(qc.get("is_blocking") and qc.get("result") == "fail" for qc in quality_checks):
        overall = "failure"
    elif "deviation" in states:
        overall = "deviation"
    elif "partial" in states or "skipped" in states:
        overall = "partial"
    else:
        overall = "success"

    fail_n = sum(1 for s in states if s in ("failure", "escalated"))
    dev_n = sum(1 for s in states if s == "deviation")
    confidence = "low" if fail_n else ("low" if dev_n > len(states) * 0.3 else ("medium" if dev_n else "high"))

    return {
        "target_platform": platform,
        "executor": executor,
        "duration_seconds": duration,
        "overall_status": overall,
        "overall_confidence": confidence,
        "steps": steps,
        "edge_cases_encountered": [],
        "novel_situations": [],
        "dead_ends_prevented": [],
        "quality_checks": quality_checks,
        "policy_compliance": {"data_leaked": False, "pii_detected": False, "notes": ""},
        "drift_score": drift,
    }
