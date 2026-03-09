"""Merge helpers for mtp-extract."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


def merge_packages(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)

    merged_package = merged.setdefault("package", {})
    overlay_package = overlay.get("package", {})
    merged_package["updated"] = _utc_now_iso()
    merged_package["tags"] = _merge_string_lists(
        merged_package.get("tags", []),
        overlay_package.get("tags", []),
    )
    if overlay_package.get("source_platform") and overlay_package.get("source_platform") != merged_package.get("source_platform"):
        merged_package["source_platform"] = f"{merged_package.get('source_platform', 'unknown')}+{overlay_package['source_platform']}"

    for section in ("intent", "input", "output", "adaptation"):
        merged[section] = _merge_sections(merged.get(section, {}), overlay.get(section, {}))

    merged["constraints"] = _merge_object_lists(
        merged.get("constraints", []),
        overlay.get("constraints", []),
        key="description",
    )
    merged["edge_cases"] = _merge_object_lists(
        merged.get("edge_cases", []),
        overlay.get("edge_cases", []),
        key="scenario",
    )
    merged["dead_ends"] = _merge_object_lists(
        merged.get("dead_ends", []),
        overlay.get("dead_ends", []),
        key="approach",
    )

    merged_methodology = merged.setdefault("methodology", {})
    overlay_methodology = overlay.get("methodology", {})
    merged_methodology["approach"] = _merge_paragraphs(
        merged_methodology.get("approach", ""),
        overlay_methodology.get("approach", ""),
    )
    merged_methodology["steps"] = _merge_steps(
        merged_methodology.get("steps", []),
        overlay_methodology.get("steps", []),
    )

    if overlay.get("policy"):
        merged["policy"] = deepcopy(overlay["policy"])

    return merged


def _merge_sections(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, str):
            result[key] = _merge_paragraphs(str(result.get(key, "")), value)
        elif isinstance(value, list):
            if value and isinstance(value[0], str):
                result[key] = _merge_string_lists(result.get(key, []), value)
            else:
                result[key] = deepcopy(value) or result.get(key, [])
        elif isinstance(value, dict):
            result[key] = _merge_sections(result.get(key, {}), value)
        else:
            result[key] = value
    return result


def _merge_steps(base_steps: list[dict[str, Any]], overlay_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: dict[str, int] = {}

    for step in base_steps + overlay_steps:
        key = _step_key(step)
        if key in seen:
            merged[seen[key]] = deepcopy(step)
        else:
            seen[key] = len(merged)
            merged.append(deepcopy(step))

    for index, step in enumerate(merged, start=1):
        step["step"] = index
        if index > 1 and "depends_on" not in step:
            step["depends_on"] = [index - 1]
    return merged


def _merge_object_lists(base: list[dict[str, Any]], overlay: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for item in list(base) + list(overlay):
        identity = str(item.get(key, "")).strip().lower()
        if not identity:
            continue
        if identity in seen:
            items[seen[identity]] = deepcopy(item)
        else:
            seen[identity] = len(items)
            items.append(deepcopy(item))
    return items


def _merge_string_lists(base: list[str], overlay: list[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for item in list(base) + list(overlay):
        normalized = str(item).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        values.append(str(item))
    return values


def _merge_paragraphs(base: str, overlay: str) -> str:
    base_clean = str(base).strip()
    overlay_clean = str(overlay).strip()
    if not base_clean:
        return overlay_clean
    if not overlay_clean or overlay_clean == base_clean:
        return base_clean
    return f"{base_clean}\n\n{overlay_clean}"


def _step_key(step: dict[str, Any]) -> str:
    name = str(step.get("name", "")).strip().lower()
    if name:
        return name
    return str(step.get("action", "")).strip().lower()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
