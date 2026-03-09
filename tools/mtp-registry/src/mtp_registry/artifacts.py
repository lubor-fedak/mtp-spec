"""Artifact loading, hashing, and schema validation for mtp-registry."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "schema"

PRIMARY_SCHEMAS = {
    "package:0.1": "mtp-package-v0.1.json",
    "package:0.2": "mtp-package-v0.2.json",
    "execution_report:0.2": "mtp-execution-report-v0.2.json",
}

REGISTRY_SCHEMAS = {
    "registry_manifest": "mtp-registry-manifest-v0.6.json",
    "signature_envelope": "mtp-signature-envelope-v0.6.json",
    "approval_record": "mtp-approval-record-v0.6.json",
    "registry_entry": "mtp-registry-entry-v0.6.json",
}


def load_artifact(path: str | Path) -> dict[str, Any]:
    artifact_path = Path(path)
    with open(artifact_path, encoding="utf-8") as handle:
        if artifact_path.suffix in {".yaml", ".yml"}:
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def detect_artifact_type(data: dict[str, Any]) -> str:
    if "mtp_version" in data:
        return "package"
    if "execution_report" in data:
        return "execution_report"
    if "signature_envelope" in data:
        return "signature_envelope"
    if "approval_record" in data:
        return "approval_record"
    if "registry_entry" in data:
        return "registry_entry"
    if "registry" in data and "mtp_registry_version" in data:
        return "registry_manifest"
    raise ValueError("Cannot detect artifact type.")


def detect_primary_version(data: dict[str, Any], artifact_type: str) -> str:
    if artifact_type == "package":
        return str(data.get("mtp_version", "0.1"))
    if artifact_type == "execution_report":
        return str(data.get("execution_report", {}).get("mtp_spec_version", "0.2"))
    raise ValueError(f"Unsupported primary artifact type '{artifact_type}'.")


def validate_primary_artifact(data: dict[str, Any]) -> list[str]:
    artifact_type = detect_artifact_type(data)
    if artifact_type not in {"package", "execution_report"}:
        raise ValueError(f"Unsupported primary artifact type '{artifact_type}'.")

    version = detect_primary_version(data, artifact_type)
    schema_name = PRIMARY_SCHEMAS.get(f"{artifact_type}:{version}")
    if schema_name is None:
        return [f"No schema registered for {artifact_type}:{version}."]
    return _validate_against_schema(data, schema_name)


def validate_registry_artifact(data: dict[str, Any]) -> list[str]:
    artifact_type = detect_artifact_type(data)
    schema_name = REGISTRY_SCHEMAS.get(artifact_type)
    if schema_name is None:
        raise ValueError(f"No registry schema registered for '{artifact_type}'.")
    return _validate_against_schema(data, schema_name)


def canonical_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_hex(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(data)).hexdigest()


def sha256_ref(data: dict[str, Any]) -> dict[str, str]:
    return {
        "algorithm": "sha256",
        "value": f"sha256:{sha256_hex(data)}",
    }


def artifact_identity(data: dict[str, Any]) -> dict[str, str]:
    artifact_type = detect_artifact_type(data)
    if artifact_type == "package":
        package = data.get("package", {})
        return {
            "id": str(package.get("id", "unknown")),
            "version": str(package.get("version", "0.0.0")),
            "name": str(package.get("name", "unnamed-package")),
        }
    if artifact_type == "execution_report":
        report = data.get("execution_report", {})
        return {
            "id": str(report.get("mtp_package_id", "unknown")),
            "version": str(report.get("mtp_package_version", "0.0.0")),
            "name": f"execution-report-{report.get('mtp_package_id', 'unknown')}",
        }
    raise ValueError(f"Unsupported artifact type '{artifact_type}' for identity.")


def slugify(value: str) -> str:
    normalized = value.lower()
    chars = [
        ch if ch.isalnum() else "-"
        for ch in normalized
    ]
    compact = "".join(chars)
    while "--" in compact:
        compact = compact.replace("--", "-")
    return compact.strip("-") or "artifact"


def _validate_against_schema(data: dict[str, Any], schema_filename: str) -> list[str]:
    schema_path = SCHEMA_DIR / schema_filename
    with open(schema_path, encoding="utf-8") as handle:
        schema = json.load(handle)

    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda err: list(err.absolute_path))
    ]
