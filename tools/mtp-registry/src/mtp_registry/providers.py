"""Key-provider helpers for mtp-registry."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import jsonschema
import yaml


REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "mtp-key-provider-manifest-v1.0.json"


def init_key_provider_manifest(path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "mtp_key_provider_version": "1.0",
        "key_provider_manifest": {
            "provider_id": "local-kms",
            "keys": [],
        },
    }
    with open(output, "w", encoding="utf-8") as handle:
        yaml.safe_dump(manifest, handle, sort_keys=False, allow_unicode=False)
    return output


def resolve_key_material(
    provider: str,
    key_env: str | None = None,
    key_file: Path | None = None,
    profile: str | None = None,
    key_provider_manifest: Path | None = None,
    key_id: str | None = None,
    purpose: str = "sign",
) -> tuple[str | None, str | None, str | None]:
    if provider == "direct":
        return _resolve_direct_key_material(key_env, key_file, profile)
    if provider == "local-kms":
        return _resolve_local_kms_material(key_provider_manifest, key_id, purpose)
    raise ValueError(f"Unsupported key provider '{provider}'.")


def validate_key_provider_manifest(path: str | Path) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    manifest = load_key_provider_manifest(path)
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(manifest), key=lambda err: list(err.absolute_path))
    ]


def load_key_provider_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    with open(manifest_path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a top-level object/map, got {type(data).__name__}.")
    errors = validate_manifest_dict(data)
    if errors:
        raise ValueError(f"Key provider manifest is not schema-valid: {errors}")
    return data


def validate_manifest_dict(data: dict[str, Any]) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda err: list(err.absolute_path))
    ]


def _resolve_direct_key_material(
    key_env: str | None,
    key_file: Path | None,
    profile: str | None,
) -> tuple[str | None, str | None, str | None]:
    if key_env and key_file:
        raise ValueError("Use either --key-env or --key-file, not both.")
    if key_env:
        value = os.environ.get(key_env)
        if value is None:
            raise ValueError(f"Environment variable '{key_env}' is not set.")
        return value, f"env:{key_env}", profile
    if key_file:
        return key_file.read_text(encoding="utf-8"), f"file:{key_file}", profile
    return None, None, profile


def _resolve_local_kms_material(
    manifest_path: Path | None,
    key_id: str | None,
    purpose: str,
) -> tuple[str | None, str | None, str | None]:
    if manifest_path is None or key_id is None:
        raise ValueError("local-kms requires --key-provider-manifest and --key-id.")
    manifest = load_key_provider_manifest(manifest_path)
    keys = manifest["key_provider_manifest"]["keys"]
    selected = next((item for item in keys if item["key_id"] == key_id), None)
    if selected is None:
        raise ValueError(f"Key '{key_id}' not found in key provider manifest.")

    if purpose == "sign":
        env_name = selected.get("signing_key_env")
        file_ref = selected.get("signing_key_ref")
    else:
        env_name = selected.get("verification_key_env") or selected.get("signing_key_env")
        file_ref = selected.get("verification_key_ref") or selected.get("signing_key_ref")

    if env_name:
        value = os.environ.get(env_name)
        if value is None:
            raise ValueError(f"Environment variable '{env_name}' is not set.")
        return value, f"local-kms:{key_id}:env:{env_name}", selected["profile"]
    if file_ref:
        ref_path = (manifest_path.parent / file_ref).resolve()
        return ref_path.read_text(encoding="utf-8"), f"local-kms:{key_id}:file:{file_ref}", selected["profile"]
    raise ValueError(f"Key '{key_id}' does not define usable material for purpose '{purpose}'.")
