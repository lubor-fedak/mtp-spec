"""Heuristic extraction for draft MTP packages."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from mtp_lint.redaction_scanner import scan_all

from mtp_extract import __version__
from mtp_extract.conversation import Message


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "then", "than",
    "your", "their", "there", "need", "should", "would", "could", "about", "after",
    "before", "must", "have", "when", "what", "which", "across", "through", "where",
    "make", "build", "using", "used", "into", "will", "them", "does", "dont",
}
ACTION_HINTS = {
    "collect", "validate", "compute", "calculate", "compare", "rank", "summarize",
    "normalize", "filter", "classify", "score", "segment", "review", "flag", "output",
    "check", "aggregate", "transform", "extract", "derive", "apply",
}
EDGE_HINTS = ("if", "when", "unless", "missing", "null", "empty", "edge case", "exception")
DEAD_END_HINTS = ("avoid", "do not", "don't", "didn't", "failed", "rejected", "discarded", "not use", "instead")


def build_draft_package(
    messages: list[Message],
    name: str | None,
    author: str,
    source_platform: str | None,
    precheck: bool = False,
    client_identifiers: list[str] | None = None,
) -> dict[str, Any]:
    if not messages:
        raise ValueError("Conversation must contain at least one message.")

    package_name = name or _infer_name(messages)
    created = _utc_now_iso()
    steps = _extract_steps(messages)
    edge_cases = _extract_edge_cases(messages)
    dead_ends = _extract_dead_ends(messages)
    tags = _infer_tags(messages)

    package: dict[str, Any] = {
        "mtp_version": "0.2",
        "package": {
            "id": str(uuid.uuid4()),
            "name": package_name,
            "version": "0.1.0",
            "created": created,
            "updated": created,
            "author": author,
            "source_platform": source_platform or "unknown",
            "tags": tags,
        },
        "intent": {
            "goal": _infer_goal(messages),
            "context": _infer_context(messages),
            "success_criteria": _infer_success_criteria(messages),
            "non_goals": _infer_non_goals(messages),
        },
        "input": {
            "description": _infer_input_description(messages),
            "assumptions": _infer_assumptions(messages),
            "preprocessing": [
                {
                    "step": 1,
                    "action": "Normalize the incoming material into a structured working set before executing methodology steps.",
                    "rationale": "Extraction drafts cannot assume clean source material. The target runtime should make structure explicit before applying the methodology.",
                }
            ],
        },
        "methodology": {
            "approach": _infer_approach(messages),
            "steps": steps,
        },
        "edge_cases": edge_cases,
        "constraints": _infer_constraints(messages),
        "output": {
            "description": _infer_output_description(messages),
            "quality_checks": [
                {
                    "check": "No input records or required analytical units are silently omitted.",
                    "failure_action": "halt",
                    "is_blocking": True,
                },
                {
                    "check": "Output includes enough structure to explain why the methodology reached its result.",
                    "failure_action": "flag_and_review",
                    "is_blocking": False,
                },
            ],
        },
        "dead_ends": dead_ends,
        "adaptation": {
            "flexibility": "Thresholds, labels, and presentation formatting may be adapted to the target environment if methodological intent is preserved.",
            "fixed_elements": "Core decision logic, validation expectations, and documented dead ends must remain unchanged unless explicitly re-authored.",
            "target_requirements": "The target system must preserve provenance, report deviations explicitly, and avoid improvising around dead ends.",
        },
        "policy": _base_policy(),
    }

    if precheck:
        package["policy"] = build_policy_from_scan(package, client_identifiers)

    return package


def build_policy_from_scan(package: dict[str, Any], client_identifiers: list[str] | None = None) -> dict[str, Any]:
    result = scan_all(package, client_identifiers)
    report_hash = "sha256:" + hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    now = _utc_now_iso()

    def status_for(category: str) -> str:
        if category == "client_identifier" and not client_identifiers:
            return "not_run"
        return "failed" if result["by_category"].get(category, 0) > 0 else "passed"

    return {
        "data_classification": "internal",
        "redaction": {
            "status": "failed" if not result["passed"] else "passed",
            "last_checked": now,
            "checker": "mtp-extract precheck",
            "checker_version": __version__,
            "report_hash": report_hash,
        },
        "pii_scan": {
            "status": status_for("pii"),
            "last_checked": now,
            "checker": "mtp-extract precheck",
        },
        "secrets_scan": {
            "status": "failed" if result["by_category"].get("secret", 0) > 0 or result["by_category"].get("entropy", 0) > 0 else "passed",
            "last_checked": now,
            "checker": "mtp-extract precheck",
        },
        "client_identifier_scan": {
            "status": status_for("client_identifier"),
            "last_checked": now,
            "checker": "mtp-extract precheck",
        },
        "regulated_content": {
            "status": "failed" if result["by_category"].get("regulated_content", 0) > 0 or result["by_category"].get("literal_data", 0) > 0 else "passed",
            "last_checked": now,
            "checker": "mtp-extract precheck",
        },
    }


def extract_provenance_map(package: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for step in package.get("methodology", {}).get("steps", []):
        provenance = step.get("provenance") or {}
        entries.append(
            {
                "kind": "step",
                "label": step.get("name"),
                "source_type": provenance.get("source_type"),
                "source_ref": provenance.get("source_ref"),
                "confidence": provenance.get("confidence"),
            }
        )

    for edge_case in package.get("edge_cases", []) or []:
        provenance = edge_case.get("provenance") or {}
        entries.append(
            {
                "kind": "edge_case",
                "label": edge_case.get("scenario"),
                "source_type": provenance.get("source_type"),
                "source_ref": provenance.get("source_ref"),
                "confidence": provenance.get("confidence"),
            }
        )

    for dead_end in package.get("dead_ends", []) or []:
        provenance = dead_end.get("provenance") or {}
        entries.append(
            {
                "kind": "dead_end",
                "label": dead_end.get("approach"),
                "source_type": provenance.get("source_type"),
                "source_ref": provenance.get("source_ref"),
                "confidence": provenance.get("confidence"),
            }
        )

    return entries


def _extract_steps(messages: list[Message]) -> list[dict[str, Any]]:
    candidates: list[tuple[str, Message]] = []
    seen: set[str] = set()

    for message in messages:
        for line in _candidate_lines(message.content):
            normalized = _normalize_text(line)
            if normalized in seen:
                continue
            if len(line) < 10:
                continue
            seen.add(normalized)
            candidates.append((line, message))

    if not candidates:
        for message in messages:
            summary = _summarize_text(message.content, 180)
            if len(summary) >= 10:
                candidates.append((summary, message))

    if not candidates:
        raise ValueError("Extractor could not identify any candidate methodology steps.")

    steps: list[dict[str, Any]] = []
    for index, (text, message) in enumerate(candidates[:5], start=1):
        on_failure = "retry" if "retry" in text.lower() or "re-run" in text.lower() else "halt"
        on_deviation = "ask_human" if any(term in text.lower() for term in ("human", "review", "escalat")) else "flag_and_proceed"
        step = {
            "step": index,
            "name": _step_name(text, index),
            "action": _ensure_sentence(text),
            "rationale": (
                "Draft step extracted heuristically from the source conversation. "
                "Human review should tighten thresholds, edge cases, and validations before production use."
            ),
            "provenance": {
                "source_type": "conversation",
                "source_ref": message.source_ref,
                "confidence": "medium",
                "notes": "Heuristically extracted from conversation content by mtp-extract.",
            },
            "execution_semantics": {
                "on_success": "proceed",
                "on_failure": on_failure,
                "on_deviation": on_deviation,
            },
            "validation": "Confirm the step completed with structured output and without silent omission of relevant records or analytical units.",
        }
        if on_failure == "retry":
            step["execution_semantics"]["max_retries"] = 1
        if index > 1:
            step["depends_on"] = [index - 1]
        steps.append(step)
    return steps


def _extract_edge_cases(messages: list[Message]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for message in messages:
        for sentence in _sentences(message.content):
            lower = sentence.lower()
            if not any(hint in lower for hint in EDGE_HINTS):
                continue
            normalized = _normalize_text(sentence)
            if normalized in seen:
                continue
            seen.add(normalized)
            items.append(
                {
                    "scenario": _summarize_text(sentence, 140),
                    "handling": "Flag the condition explicitly, preserve provenance, and route the case through the documented methodology rather than improvising.",
                    "rationale": "This condition appeared in the source conversation as something that could distort results if handled implicitly.",
                    "severity": "warning",
                    "provenance": {
                        "source_type": "conversation",
                        "source_ref": message.source_ref,
                        "confidence": "medium",
                        "notes": "Detected as an edge-case cue in the conversation.",
                    },
                }
            )
            if len(items) >= 4:
                return items
    return items


def _extract_dead_ends(messages: list[Message]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for message in messages:
        for sentence in _sentences(message.content):
            lower = sentence.lower()
            if not any(hint in lower for hint in DEAD_END_HINTS):
                continue
            normalized = _normalize_text(sentence)
            if normalized in seen:
                continue
            seen.add(normalized)
            items.append(
                {
                    "approach": _summarize_text(sentence, 140),
                    "reason": "The source conversation indicates this path was considered unsafe, ineffective, or misleading for the methodology.",
                    "lesson": "Do not rediscover this path during execution. Escalate or revisit the package authoring flow instead.",
                    "provenance": {
                        "source_type": "conversation",
                        "source_ref": message.source_ref,
                        "confidence": "medium",
                        "notes": "Detected as a rejected or discouraged approach in the conversation.",
                    },
                }
            )
            if len(items) >= 4:
                return items
    return items


def _infer_name(messages: list[Message]) -> str:
    for message in messages:
        candidate = _summarize_text(message.content, 80).strip(" .:-")
        if len(candidate.split()) >= 3:
            return candidate.title()
    return "Extracted Methodology Draft"


def _infer_goal(messages: list[Message]) -> str:
    for message in messages:
        if message.role == "user":
            summary = _summarize_text(message.content, 320)
            if len(summary) >= 10:
                return _ensure_sentence(summary)
    return "Transfer the conversation into a portable methodology that preserves decision logic, validation, and execution constraints."


def _infer_context(messages: list[Message]) -> str:
    joined = " ".join(_summarize_text(message.content, 180) for message in messages[:3])
    return _ensure_sentence(joined) if joined else "Conversation-derived draft extracted by mtp-extract."


def _infer_success_criteria(messages: list[Message]) -> list[str]:
    criteria: list[str] = []
    for message in messages:
        for sentence in _sentences(message.content):
            lower = sentence.lower()
            if any(token in lower for token in ("must", "should", "ensure", "need to", "has to")):
                criteria.append(_ensure_sentence(_summarize_text(sentence, 160)))
            if len(criteria) >= 3:
                return _dedupe(criteria)
    criteria.append("The extracted methodology remains schema-valid and reviewable before execution.")
    return _dedupe(criteria)


def _infer_non_goals(messages: list[Message]) -> list[str]:
    items: list[str] = []
    for message in messages:
        for sentence in _sentences(message.content):
            lower = sentence.lower()
            if "not" in lower and any(token in lower for token in ("goal", "scope", "meant to", "intended to", "trying to")):
                items.append(_ensure_sentence(_summarize_text(sentence, 160)))
            if len(items) >= 3:
                return _dedupe(items)
    return [
        "This draft does not encode raw source data or platform-specific prompt history.",
        "This draft is not a substitute for human review before enterprise execution.",
    ]


def _infer_input_description(messages: list[Message]) -> str:
    for message in messages:
        lower = message.content.lower()
        if any(term in lower for term in ("data", "dataset", "input", "csv", "report", "records", "file")):
            return _ensure_sentence(_summarize_text(message.content, 220))
    return "Structured source material relevant to the methodology, such as datasets, records, reports, or operational context."


def _infer_assumptions(messages: list[Message]) -> list[str]:
    assumptions: list[str] = []
    for message in messages:
        for sentence in _sentences(message.content):
            lower = sentence.lower()
            if any(term in lower for term in ("assume", "assuming", "expects", "provided", "available", "complete")):
                assumptions.append(_ensure_sentence(_summarize_text(sentence, 160)))
            if len(assumptions) >= 3:
                return _dedupe(assumptions)
    return [
        "Input material is accessible to the target system in a structured form.",
        "The target system can preserve step ordering, provenance, and explicit deviations.",
    ]


def _infer_approach(messages: list[Message]) -> str:
    assistant_text = " ".join(_summarize_text(message.content, 160) for message in messages if message.role == "assistant")
    if assistant_text:
        return _ensure_sentence(assistant_text[:400])
    return "Conversation-derived, stepwise methodology extracted heuristically from the transcript with explicit provenance and default execution semantics."


def _infer_constraints(messages: list[Message]) -> list[dict[str, str]]:
    items = [
        {
            "type": "accuracy",
            "description": "The target system must preserve the extracted step order and validation intent.",
            "enforcement": "Flag deviations explicitly and halt if a required step cannot be executed reliably.",
        },
        {
            "type": "security",
            "description": "The package remains data-free and must not embed sensitive source material from the conversation.",
            "enforcement": "Run policy precheck before enterprise execution and reject packages that contain leaks.",
        },
    ]
    if any("compliance" in message.content.lower() for message in messages):
        items.append(
            {
                "type": "compliance",
                "description": "Conversation context indicates that compliance or policy boundaries matter for execution.",
                "enforcement": "Keep methodology portable and move real data only inside approved enterprise boundaries.",
            }
        )
    return items


def _infer_output_description(messages: list[Message]) -> str:
    for message in messages:
        for sentence in _sentences(message.content):
            if any(term in sentence.lower() for term in ("output", "return", "produce", "result", "report")):
                return _ensure_sentence(_summarize_text(sentence, 220))
    return "A structured, explainable output that shows the result of applying the methodology plus the reasoning artifacts needed for validation."


def _infer_tags(messages: list[Message]) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", " ".join(message.content for message in messages).lower())
    filtered = [word for word in words if word not in STOPWORDS]
    counts = Counter(filtered)
    tags = [word for word, _count in counts.most_common(6)]
    return tags or ["methodology", "draft", "extracted"]


def _base_policy() -> dict[str, Any]:
    return {
        "data_classification": "internal",
        "redaction": {"status": "not_run", "checker": "mtp-extract"},
        "pii_scan": {"status": "not_run", "checker": "mtp-extract"},
        "secrets_scan": {"status": "not_run", "checker": "mtp-extract"},
        "client_identifier_scan": {"status": "not_run", "checker": "mtp-extract"},
        "regulated_content": {"status": "not_run", "checker": "mtp-extract"},
    }


def _candidate_lines(text: str) -> list[str]:
    numbered = []
    bullets = []
    sentences = []
    for raw_line in text.splitlines():
        line = raw_line.strip(" -*\t")
        if not line:
            continue
        if re.match(r"^\d+[\.\)]\s+", raw_line.strip()):
            numbered.append(re.sub(r"^\d+[\.\)]\s+", "", raw_line.strip()))
            continue
        if raw_line.strip().startswith(("-", "*")) and _looks_actionable(line):
            bullets.append(line)
    if numbered:
        return numbered
    if bullets:
        return bullets
    for sentence in _sentences(text):
        if _looks_actionable(sentence):
            sentences.append(sentence)
    return sentences


def _looks_actionable(text: str) -> bool:
    lower = text.lower()
    if len(text) < 20:
        return False
    if text.endswith("?"):
        return False
    return any(f" {hint} " in f" {lower} " for hint in ACTION_HINTS)


def _step_name(text: str, index: int) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text)
    name = " ".join(words[:6]).strip()
    return name.title() if name else f"Extracted Step {index}"


def _summarize_text(text: str, max_len: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_len:
        return normalized
    truncated = normalized[: max_len - 3].rstrip(" ,;:")
    return truncated + "..."


def _sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    parts = re.split(r"(?<=[\.\!\?])\s+", normalized)
    return [part.strip() for part in parts if len(part.strip()) >= 12]


def _ensure_sentence(text: str) -> str:
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return "No content extracted."
    if cleaned[-1] not in ".!?":
        return cleaned + "."
    return cleaned


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = _normalize_text(item)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)
    return result


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
