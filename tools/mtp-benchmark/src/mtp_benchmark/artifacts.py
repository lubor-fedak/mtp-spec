"""Artifact helpers for mtp-benchmark."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml


REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCHEMA_DIR = REPO_ROOT / "schema"

SCHEMAS = {
    "benchmark_suite": "mtp-benchmark-suite-v0.7.json",
    "benchmark_result": "mtp-benchmark-result-v0.7.json",
    "adapter_certification": "mtp-adapter-certification-v0.7.json",
}


def load_artifact(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path)
    with open(artifact_path, encoding="utf-8") as handle:
        if artifact_path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(handle)
        else:
            data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a top-level object/map, got {type(data).__name__}.")
    return data


def dump_yaml(path: str | Path, data: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)


def detect_artifact_type(data: dict[str, Any]) -> str:
    if "suite" in data and "mtp_benchmark_version" in data:
        return "benchmark_suite"
    if "benchmark_result" in data and "mtp_benchmark_version" in data:
        return "benchmark_result"
    if "adapter_certification" in data and "mtp_adapter_certification_version" in data:
        return "adapter_certification"
    raise ValueError("Cannot detect benchmark artifact type.")


def validate_artifact(data: dict[str, Any]) -> list[str]:
    artifact_type = detect_artifact_type(data)
    schema_path = SCHEMA_DIR / SCHEMAS[artifact_type]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda err: list(err.absolute_path))
    ]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
