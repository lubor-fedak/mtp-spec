"""Shared file and schema helpers for mtp-run."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml


SCHEMA_DIR = Path(__file__).parent.parent.parent.parent.parent / "schema"


def load_artifact(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path)
    with open(artifact_path) as handle:
        if artifact_path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(handle)
        else:
            data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a top-level object/map, got {type(data).__name__}.")
    return data


def dump_yaml(path: str | Path, data: dict[str, Any]) -> None:
    output_path = Path(path)
    with open(output_path, "w") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_schema(filename: str) -> dict[str, Any]:
    schema_path = SCHEMA_DIR / filename
    with open(schema_path) as handle:
        return json.load(handle)


def validate_package(data: dict[str, Any]) -> list[str]:
    schema = _load_schema("mtp-package-v0.2.json")
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'.'.join(str(p) for p in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]


def validate_execution_report(data: dict[str, Any]) -> list[str]:
    schema = _load_schema("mtp-execution-report-v0.2.json")
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'.'.join(str(p) for p in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]
