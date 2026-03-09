"""Core MTP execution engine.

Orchestrates step-by-step execution of an MTP package through an LLM adapter,
respecting execution semantics, dependency chains, and pipeline rules.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from mtp_run.adapters import BaseAdapter, StepResult
from mtp_run.prompt_builder import build_system_context, build_step_prompt, build_data_section


def execute_package(
    package: dict,
    data: str,
    adapter: BaseAdapter,
    on_step_start: Callable[[int, str], None] | None = None,
    on_step_end: Callable[[int, str, StepResult], None] | None = None,
) -> dict:
    """Execute an MTP package against provided data.

    Args:
        package: Loaded MTP package dict
        data: The data to process (string — CSV, JSON, text, etc.)
        adapter: LLM adapter to use for execution
        on_step_start: Optional callback(step_num, step_name) for progress
        on_step_end: Optional callback(step_num, step_name, result) for progress

    Returns:
        Raw execution results dict (not yet a formatted report — use report_builder)
    """
    methodology = package.get("methodology", {})
    steps = methodology.get("steps", [])
    edge_cases = package.get("edge_cases", [])
    input_spec = package.get("input")

    # Build system context once
    system_context = build_system_context(package)
    data_section = build_data_section(data, input_spec)

    # Execution state
    step_results: dict[int, dict] = {}
    step_outputs: dict[int, str] = {}
    all_edge_cases: list[dict] = []
    all_novel: list[dict] = []
    all_dead_ends_prevented: list[dict] = []
    dead_ends_repeated = False
    halted = False
    halt_reason = ""

    for step in steps:
        step_num = step.get("step", 0)
        step_name = step.get("name", f"Step {step_num}")
        exec_sem = step.get("execution_semantics", {})
        on_failure = exec_sem.get("on_failure", "halt")
        on_deviation = exec_sem.get("on_deviation", "flag_and_proceed")
        max_retries = exec_sem.get("max_retries", 1)

        if on_step_start:
            on_step_start(step_num, step_name)

        # Check if pipeline is halted
        if halted:
            result_dict = {
                "step": step_num,
                "state": "skipped",
                "validation_result": "not_applicable",
                "duration_seconds": 0,
                "retries_attempted": 0,
                "skip_reason": f"Pipeline halted: {halt_reason}",
                "notes": "",
            }
            step_results[step_num] = result_dict
            if on_step_end:
                on_step_end(step_num, step_name, StepResult(state="skipped", validation_result="not_applicable", output=""))
            continue

        # Check dependencies
        depends = step.get("depends_on", [])
        unmet = []
        for dep in depends:
            dep_result = step_results.get(dep)
            if dep_result is None or dep_result["state"] in ("failure", "skipped", "escalated"):
                unmet.append(dep)

        if unmet:
            result_dict = {
                "step": step_num,
                "state": "skipped",
                "validation_result": "not_applicable",
                "duration_seconds": 0,
                "retries_attempted": 0,
                "skip_reason": f"unmet_dependency: steps {unmet}",
                "notes": "",
            }
            step_results[step_num] = result_dict
            if on_step_end:
                on_step_end(step_num, step_name, StepResult(state="skipped", validation_result="not_applicable", output=""))
            continue

        # Build step prompt
        step_prompt = build_step_prompt(step, edge_cases, step_outputs)

        # Execute with retries
        retries = 0
        result = None
        t0 = time.time()

        while True:
            try:
                result = adapter.execute_step(system_context, step_prompt, data_section)
            except Exception as exc:
                result = StepResult(
                    state="failure",
                    validation_result="fail",
                    output="",
                    failure_reason=f"{adapter.platform_id()} runtime error: {exc}",
                    notes="Adapter raised an exception during step execution.",
                    raw_response="",
                )
            duration = round(time.time() - t0, 2)

            if result.state == "failure" and on_failure == "retry" and retries < max_retries:
                retries += 1
                continue
            break

        # Build result dict
        result_dict = {
            "step": step_num,
            "state": result.state,
            "validation_result": result.validation_result,
            "duration_seconds": duration,
            "retries_attempted": retries,
            "notes": result.notes,
        }

        if result.state == "deviation":
            result_dict["deviation"] = {
                "description": result.deviation_description,
                "reason": result.deviation_reason,
                "approved_by": "",
            }
        if result.state == "failure":
            result_dict["failure_reason"] = result.failure_reason
            result_dict["failure_blocking"] = on_failure == "halt"
        if result.state == "skipped":
            result_dict["skip_reason"] = result.notes

        step_results[step_num] = result_dict
        step_outputs[step_num] = result.output

        for edge_case in result.edge_cases_encountered:
            all_edge_cases.append({
                "step": step_num,
                "scenario": edge_case.get("scenario", ""),
                "matched_edge_case": edge_case.get("matched_edge_case", "novel"),
                "handling_applied": edge_case.get("handling_applied", ""),
            })

        if result.state == "escalated" and not result.novel_situations:
            result.novel_situations.append({
                "description": result.notes or f"Step {step_num} escalated without structured novel_situations details.",
                "action_taken": "escalated",
                "notes": "",
            })

        for novel_situation in result.novel_situations:
            all_novel.append({
                "step": step_num,
                "description": novel_situation.get("description", ""),
                "action_taken": novel_situation.get("action_taken", "escalated"),
                "notes": novel_situation.get("notes", ""),
            })

        for dead_end in result.dead_ends_considered:
            all_dead_ends_prevented.append({
                "step": step_num,
                "dead_end_ref": dead_end.get("dead_end_ref", ""),
                "notes": dead_end.get("notes", ""),
            })

        if result.dead_ends_repeated:
            dead_ends_repeated = True

        # Apply execution semantics
        if result.state == "failure":
            if on_failure == "halt":
                halted = True
                halt_reason = f"Step {step_num} failed with on_failure=halt"
            elif on_failure == "escalate":
                result_dict["state"] = "escalated"
                halted = True
                halt_reason = f"Step {step_num} failed and escalated"

        if result.state == "deviation":
            if on_deviation == "halt":
                halted = True
                halt_reason = f"Step {step_num} deviated with on_deviation=halt"
            elif on_deviation == "ask_human":
                result_dict["state"] = "escalated"
                halted = True
                halt_reason = f"Step {step_num} deviated, requires human approval"

        if result.state == "escalated":
            halted = True
            halt_reason = f"Step {step_num} escalated — novel situation"

        if on_step_end:
            on_step_end(step_num, step_name, result)

    # Return raw results for report_builder
    return {
        "steps": list(step_results.values()),
        "platform": adapter.platform_id(),
        "edge_cases_encountered": all_edge_cases,
        "novel_situations": all_novel,
        "dead_ends_prevented": all_dead_ends_prevented,
        "dead_ends_repeated": dead_ends_repeated,
    }
