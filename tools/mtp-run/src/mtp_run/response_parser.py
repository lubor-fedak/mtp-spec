"""Response parser for LLM step execution outputs.

Extracts structured StepResult from LLM text responses.
Handles YAML blocks, partial YAML, and fallback heuristics.
"""

from __future__ import annotations

import re

import yaml

from mtp_run.adapters import StepResult


VALID_STATES = {"success", "partial", "deviation", "failure", "escalated", "skipped"}
VALID_VALIDATION = {"pass", "fail", "not_applicable"}


def parse_step_response(raw: str) -> StepResult:
    """Parse an LLM response into a StepResult.

    Attempts to extract YAML from the response. Falls back to
    heuristic parsing if YAML extraction fails.
    """
    yaml_block = _extract_yaml(raw)

    if yaml_block:
        try:
            data = yaml.safe_load(yaml_block)
            if isinstance(data, dict):
                return _from_dict(data, raw)
        except yaml.YAMLError:
            pass

    # Fallback: try to parse the entire response as YAML
    try:
        data = yaml.safe_load(raw)
        if isinstance(data, dict):
            return _from_dict(data, raw)
    except (yaml.YAMLError, ValueError):
        pass

    # Final fallback: heuristic parsing
    return _heuristic_parse(raw)


def _extract_yaml(text: str) -> str | None:
    """Extract YAML block from markdown-fenced code."""
    patterns = [
        r"```ya?ml\s*\n(.*?)```",
        r"```\s*\n(.*?)```",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


def _from_dict(data: dict, raw: str) -> StepResult:
    """Convert a parsed dict into a StepResult."""
    state = str(data.get("state", "failure")).lower().strip()
    if state not in VALID_STATES:
        state = "failure"

    validation = str(data.get("validation_result", "not_applicable")).lower().strip()
    if validation not in VALID_VALIDATION:
        validation = "not_applicable"

    output = data.get("output", "")
    if isinstance(output, dict) or isinstance(output, list):
        output = yaml.dump(output, default_flow_style=False)
    else:
        output = str(output)

    edge_cases = _normalize_edge_cases(data.get("edge_cases", []))
    novel = _normalize_novel_situations(data.get("novel_situations", []))
    dead_ends = _normalize_dead_end_list(data.get("dead_ends_considered", []))
    dead_ends_repeated = _normalize_dead_end_list(data.get("dead_ends_repeated", []))

    return StepResult(
        state=state,
        validation_result=validation,
        output=output,
        deviation_description=str(data.get("deviation_description", "")),
        deviation_reason=str(data.get("deviation_reason", "")),
        failure_reason=str(data.get("failure_reason", "")),
        notes=str(data.get("notes", "")),
        edge_cases_encountered=edge_cases,
        novel_situations=novel,
        dead_ends_considered=dead_ends,
        dead_ends_repeated=dead_ends_repeated,
        raw_response=raw,
    )


def _heuristic_parse(raw: str) -> StepResult:
    """Last-resort heuristic parsing when YAML extraction fails.

    Looks for state keywords in the text and treats the entire
    response as the output.
    """
    lower = raw.lower()

    if "escalat" in lower:
        state = "escalated"
    elif "fail" in lower or "error" in lower or "cannot" in lower:
        state = "failure"
    elif "deviat" in lower:
        state = "deviation"
    elif "partial" in lower:
        state = "partial"
    else:
        state = "success"

    return StepResult(
        state=state,
        validation_result="not_applicable",
        output=raw,
        notes="Parsed via heuristic fallback — LLM did not return structured YAML.",
        raw_response=raw,
    )


def _normalize_edge_cases(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        if isinstance(item, dict):
            scenario = str(item.get("scenario", "")).strip()
            matched = str(item.get("matched_edge_case", "")).strip()
            handling = str(item.get("handling_applied", "")).strip()
        else:
            scenario = str(item).strip()
            matched = ""
            handling = ""

        if not scenario:
            continue

        normalized.append({
            "scenario": scenario,
            "matched_edge_case": matched or "novel",
            "handling_applied": handling,
        })
    return normalized


def _normalize_novel_situations(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        if isinstance(item, dict):
            description = str(item.get("description", "")).strip()
            action_taken = str(item.get("action_taken", "escalated")).strip() or "escalated"
            notes = str(item.get("notes", "")).strip()
        else:
            description = str(item).strip()
            action_taken = "escalated"
            notes = ""

        if not description:
            continue

        if action_taken not in {"escalated", "skipped"}:
            action_taken = "escalated"

        normalized.append({
            "description": description,
            "action_taken": action_taken,
            "notes": notes,
        })
    return normalized


def _normalize_dead_end_list(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        if isinstance(item, dict):
            dead_end_ref = str(item.get("dead_end_ref", "")).strip()
            notes = str(item.get("notes", "")).strip()
        else:
            dead_end_ref = str(item).strip()
            notes = ""

        if not dead_end_ref:
            continue

        normalized.append({
            "dead_end_ref": dead_end_ref,
            "notes": notes,
        })
    return normalized
