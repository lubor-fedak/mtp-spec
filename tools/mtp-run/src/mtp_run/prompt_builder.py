"""Prompt builder for MTP execution.

Constructs the system context (methodology-level) and per-step prompts
from an MTP package. The prompts are adapter-agnostic — any LLM can
process them.
"""

from __future__ import annotations

from typing import Any


def build_system_context(package: dict) -> str:
    """Build the methodology-level system context.

    This is sent once at the start and includes intent, approach,
    dead ends, and global constraints. It does NOT include step details.
    """
    intent = package.get("intent", {})
    methodology = package.get("methodology", {})
    dead_ends = package.get("dead_ends", [])
    constraints = package.get("constraints", [])
    adaptation = package.get("adaptation", {})

    parts = [
        "You are executing a methodology defined by an MTP (Methodology Transfer Protocol) package.",
        "This is a controlled execution — not a creative task. Follow the methodology precisely.",
        "",
        "=== METHODOLOGY INTENT ===",
        f"Goal: {intent.get('goal', 'Not specified')}",
    ]

    if intent.get("context"):
        parts.append(f"Context: {intent['context']}")

    if intent.get("success_criteria"):
        parts.append("Success criteria:")
        for sc in intent["success_criteria"]:
            parts.append(f"  - {sc}")

    if intent.get("non_goals"):
        parts.append("Non-goals (do NOT attempt these):")
        for ng in intent["non_goals"]:
            parts.append(f"  - {ng}")

    parts.append("")
    parts.append("=== APPROACH ===")
    parts.append(methodology.get("approach", "Not specified"))

    if dead_ends:
        parts.append("")
        parts.append("=== DEAD ENDS (DO NOT REPEAT THESE APPROACHES) ===")
        for i, de in enumerate(dead_ends):
            parts.append(f"Dead end #{i}: {de.get('approach', '')}")
            parts.append(f"  Why it failed: {de.get('reason', '')}")
            parts.append(f"  Lesson: {de.get('lesson', '')}")

    if constraints:
        parts.append("")
        parts.append("=== CONSTRAINTS ===")
        for c in constraints:
            parts.append(f"  [{c.get('type', 'general')}] {c.get('description', '')}")

    if adaptation.get("fixed_elements"):
        parts.append("")
        parts.append("=== FIXED ELEMENTS (DO NOT CHANGE) ===")
        parts.append(adaptation["fixed_elements"])

    parts.append("")
    parts.append("=== RESPONSE FORMAT ===")
    parts.append("For EACH step you execute, respond with EXACTLY this YAML structure:")
    parts.append("```yaml")
    parts.append("state: success  # one of: success, partial, deviation, failure, escalated")
    parts.append("validation_result: pass  # one of: pass, fail, not_applicable")
    parts.append("output: |")
    parts.append("  <your actual work output for this step>")
    parts.append("deviation_description: \"\"  # fill only if state is deviation")
    parts.append("deviation_reason: \"\"  # fill only if state is deviation")
    parts.append("failure_reason: \"\"  # fill only if state is failure")
    parts.append("notes: \"\"  # any observations")
    parts.append("edge_cases: []  # list of {scenario, matched_edge_case, handling_applied}")
    parts.append("novel_situations: []  # list of {description, action_taken, notes}")
    parts.append("dead_ends_considered: []  # list of {dead_end_ref, notes} that you consciously avoided")
    parts.append("dead_ends_repeated: []  # list of {dead_end_ref, notes} only if you actually repeated one")
    parts.append("```")
    parts.append("")
    parts.append("RULES:")
    parts.append("1. If a situation is NOT covered by the edge cases, set state to 'escalated'. Do NOT improvise.")
    parts.append("2. If you considered an approach listed in DEAD ENDS, note it in your response but do NOT use it.")
    parts.append("3. Every step MUST have a validation_result. Apply the validation rule and report pass or fail.")
    parts.append("4. Report 'deviation' if you modified the prescribed action, with description and reason.")

    return "\n".join(parts)


def build_step_prompt(step: dict, edge_cases: list[dict], step_outputs: dict[int, str]) -> str:
    """Build the prompt for a single step execution.

    Args:
        step: The step definition from the MTP package
        edge_cases: All edge cases from the package (filtered by relevance if possible)
        step_outputs: Outputs from previously executed steps (keyed by step number)
    """
    step_num = step.get("step", "?")
    parts = [
        f"=== EXECUTE STEP {step_num}: {step.get('name', 'Unnamed')} ===",
        "",
        "ACTION:",
        step.get("action", "No action specified"),
    ]

    if step.get("rationale"):
        parts.append("")
        parts.append("RATIONALE (why this step exists):")
        parts.append(step["rationale"])

    if step.get("decision_points"):
        parts.append("")
        parts.append("DECISION POINTS:")
        for dp in step["decision_points"]:
            parts.append(f"  IF: {dp.get('condition', '')}")
            parts.append(f"  THEN: {dp.get('then', '')}")
            if dp.get("else"):
                parts.append(f"  ELSE: {dp['else']}")
            if dp.get("rationale"):
                parts.append(f"  WHY: {dp['rationale']}")

    if step.get("validation"):
        parts.append("")
        parts.append("VALIDATION (you MUST check this and report pass/fail):")
        parts.append(step["validation"])

    # Include relevant edge cases
    if edge_cases:
        parts.append("")
        parts.append("EDGE CASES TO WATCH FOR:")
        for i, ec in enumerate(edge_cases):
            parts.append(f"  [{ec.get('severity', 'info')}] {ec.get('scenario', '')}")
            parts.append(f"    Handle: {ec.get('handling', '')}")

    # Include outputs from dependency steps
    depends = step.get("depends_on", [])
    if depends and step_outputs:
        parts.append("")
        parts.append("OUTPUTS FROM PREVIOUS STEPS:")
        for dep_num in depends:
            if dep_num in step_outputs:
                output = step_outputs[dep_num]
                # Truncate very long outputs
                if len(output) > 2000:
                    output = output[:2000] + "\n... [truncated]"
                parts.append(f"  Step {dep_num}: {output}")

    parts.append("")
    parts.append("Execute this step now. Respond with the YAML structure specified in the system context.")

    return "\n".join(parts)


def build_data_section(data: str, input_spec: dict | None = None) -> str:
    """Build the data section of the prompt.

    If input specification is available, includes schema context.
    """
    parts = ["=== DATA ==="]

    if input_spec:
        if input_spec.get("assumptions"):
            parts.append("Data assumptions:")
            for a in input_spec["assumptions"]:
                parts.append(f"  - {a}")
            parts.append("")

    parts.append(data)
    return "\n".join(parts)
