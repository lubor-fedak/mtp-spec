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

    edge_cases = data.get("edge_cases", [])
    if not isinstance(edge_cases, list):
        edge_cases = []

    novel = data.get("novel_situations", [])
    if not isinstance(novel, list):
        novel = []

    dead_ends = data.get("dead_ends_considered", [])
    if not isinstance(dead_ends, list):
        dead_ends = []

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
