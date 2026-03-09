"""Artifact helpers for mtp-release."""

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
    "provider_matrix": "mtp-provider-matrix-v1.0.json",
    "compatibility_contract": "mtp-compatibility-contract-v1.0.json",
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
    if "provider_matrix" in data and "mtp_provider_matrix_version" in data:
        return "provider_matrix"
    if "compatibility_contract" in data and "mtp_compatibility_contract_version" in data:
        return "compatibility_contract"
    raise ValueError("Cannot detect release artifact type.")


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
