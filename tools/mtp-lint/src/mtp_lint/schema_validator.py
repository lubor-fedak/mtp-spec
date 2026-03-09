"""Schema validation for MTP packages and execution reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml


SCHEMA_DIR = Path(__file__).resolve().parents[4] / "schema"

SCHEMAS = {
    "package-v0.1": "mtp-package-v0.1.json",
    "package-v0.2": "mtp-package-v0.2.json",
    "execution-report-v0.2": "mtp-execution-report-v0.2.json",
}


def _load_schema(name: str) -> dict:
    path = SCHEMA_DIR / SCHEMAS[name]
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    with open(path) as f:
        return json.load(f)


def load_package(path: str | Path) -> dict:
    """Load a YAML or JSON MTP package file."""
    p = Path(path)
    with open(p) as f:
        if p.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)
        else:
            return json.load(f)


def detect_artifact_type(data: dict) -> str:
    """Detect whether the data is a package or execution report."""
    if "execution_report" in data:
        return "execution-report"
    if "mtp_version" in data:
        return "package"
    raise ValueError("Cannot detect artifact type: no 'mtp_version' or 'execution_report' key found.")


def detect_version(data: dict, artifact_type: str) -> str:
    """Detect the MTP version of the artifact."""
    if artifact_type == "execution-report":
        spec_version = data.get("execution_report", {}).get("mtp_spec_version", "0.2")
        return spec_version
    return data.get("mtp_version", "0.1")


def validate_schema(data: dict, artifact_type: str | None = None, version: str | None = None) -> list[dict]:
    """Validate data against the appropriate MTP JSON Schema.

    Returns a list of error dicts: [{"path": str, "message": str, "severity": "error"}]
    """
    if artifact_type is None:
        artifact_type = detect_artifact_type(data)
    if version is None:
        version = detect_version(data, artifact_type)

    schema_key = f"{artifact_type}-v{version}"
    if schema_key not in SCHEMAS:
        return [{"path": "$", "message": f"No schema found for {schema_key}", "severity": "error"}]

    schema = _load_schema(schema_key)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)

    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        errors.append({
            "path": ".".join(str(p) for p in error.absolute_path) or "$",
            "message": error.message,
            "severity": "error",
        })

    return errors
