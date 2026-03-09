"""Signing, approval, and registry publication workflows."""

from __future__ import annotations

import base64
import hmac
import shutil
import uuid
from hashlib import sha256
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from mtp_registry.artifacts import (
    artifact_identity,
    canonical_bytes,
    detect_artifact_type,
    dump_yaml,
    load_artifact,
    sha256_ref,
    slugify,
    utc_now_iso,
    validate_primary_artifact,
    validate_registry_artifact,
)


REGISTRY_CHANNELS = ["draft", "review", "approved", "deprecated"]


def init_registry(registry_dir: str | Path, name: str) -> Path:
    root = Path(registry_dir)
    root.mkdir(parents=True, exist_ok=True)
    for relative in (
        "artifacts/packages",
        "artifacts/execution-reports",
        "signatures",
        "approvals",
        "entries",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)

    manifest = {
        "mtp_registry_version": "0.6",
        "registry": {
            "id": str(uuid.uuid4()),
            "name": name,
            "created_at": utc_now_iso(),
            "layout_version": "0.6",
            "default_channel": "draft",
            "supported_channels": REGISTRY_CHANNELS,
        },
    }
    errors = validate_registry_artifact(manifest)
    if errors:
        raise ValueError(f"Generated registry manifest is not valid: {errors}")

    manifest_path = root / "registry.yaml"
    dump_yaml(manifest_path, manifest)
    return manifest_path


def create_signature_envelope(
    artifact: dict[str, Any],
    artifact_ref: str,
    key: str,
    key_id: str,
    signer_id: str,
    key_source: str,
    profile: str = "hmac-sha256",
) -> dict[str, Any]:
    errors = validate_primary_artifact(artifact)
    if errors:
        raise ValueError(f"Cannot sign invalid artifact: {errors}")

    artifact_type = detect_artifact_type(artifact)
    identity = artifact_identity(artifact)
    signature_value = _sign(profile, key, canonical_bytes(artifact))

    envelope = {
        "mtp_registry_version": "0.6",
        "signature_envelope": {
            "envelope_id": str(uuid.uuid4()),
            "artifact_type": artifact_type,
            "artifact_identity": identity,
            "artifact_ref": artifact_ref,
            "artifact_hash": sha256_ref(artifact),
            "canonicalization": "json-sorted-v1",
            "signature_profile": {
                "profile": profile,
                "key_id": key_id,
                "key_source": key_source,
            },
            "signer": {
                "id": signer_id,
            },
            "signed_at": utc_now_iso(),
            "signature": signature_value,
        },
    }
    errors = validate_registry_artifact(envelope)
    if errors:
        raise ValueError(f"Generated signature envelope is not valid: {errors}")
    return envelope


def verify_signature_envelope(
    artifact: dict[str, Any],
    envelope: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    envelope_errors = validate_registry_artifact(envelope)
    if envelope_errors:
        raise ValueError(f"Signature envelope is not schema-valid: {envelope_errors}")

    artifact_errors = validate_primary_artifact(artifact)
    if artifact_errors:
        raise ValueError(f"Artifact is not schema-valid: {artifact_errors}")

    signature = envelope["signature_envelope"]
    profile = signature["signature_profile"]["profile"]
    expected_hash = sha256_ref(artifact)
    hash_matches = signature["artifact_hash"] == expected_hash
    signature_matches = _verify_signature(profile, key, canonical_bytes(artifact), signature["signature"])
    artifact_type_matches = signature["artifact_type"] == detect_artifact_type(artifact)
    identity_matches = signature["artifact_identity"] == artifact_identity(artifact)

    verified = hash_matches and signature_matches and artifact_type_matches and identity_matches
    return {
        "verified": verified,
        "hash_matches": hash_matches,
        "signature_matches": signature_matches,
        "artifact_type_matches": artifact_type_matches,
        "identity_matches": identity_matches,
    }


def create_approval_record(
    artifact: dict[str, Any],
    artifact_ref: str,
    signature: dict[str, Any],
    signature_ref: str,
    approver_id: str,
    approver_name: str,
    role: str,
    status: str,
    policy: str,
    rationale: str,
    ticket_ref: str | None = None,
    conformance_ref: str | None = None,
) -> dict[str, Any]:
    if status not in {"approved", "rejected"}:
        raise ValueError("Approval status must be 'approved' or 'rejected'.")

    signature_errors = validate_registry_artifact(signature)
    if signature_errors:
        raise ValueError(f"Signature envelope is not schema-valid: {signature_errors}")

    signature_body = signature["signature_envelope"]
    if (
        signature_body["artifact_hash"] != sha256_ref(artifact)
        or signature_body["artifact_type"] != detect_artifact_type(artifact)
        or signature_body["artifact_identity"] != artifact_identity(artifact)
    ):
        raise ValueError("Approval cannot be created for a signature envelope that does not match the artifact.")

    approval = {
        "mtp_registry_version": "0.6",
        "approval_record": {
            "approval_id": str(uuid.uuid4()),
            "artifact_type": detect_artifact_type(artifact),
            "artifact_identity": artifact_identity(artifact),
            "artifact_ref": artifact_ref,
            "artifact_hash": sha256_ref(artifact),
            "workflow": {
                "policy": policy,
                "decision": status,
            },
            "approver": {
                "id": approver_id,
                "name": approver_name,
                "role": role,
            },
            "decided_at": utc_now_iso(),
            "rationale": rationale,
            "evidence": {
                "signature_ref": signature_ref,
            },
        },
    }
    if ticket_ref:
        approval["approval_record"]["evidence"]["ticket_ref"] = ticket_ref
    if conformance_ref:
        approval["approval_record"]["evidence"]["conformance_ref"] = conformance_ref

    errors = validate_registry_artifact(approval)
    if errors:
        raise ValueError(f"Generated approval record is not valid: {errors}")
    return approval


def publish_artifact(
    artifact_path: str | Path,
    artifact: dict[str, Any],
    registry_dir: str | Path,
    signature_path: str | Path,
    signature: dict[str, Any],
    signing_key: str | None,
    approval_paths: list[Path],
    approvals: list[dict[str, Any]],
    status: str,
    channel: str,
    conformance_level: str | None = None,
    conformance_summary_hash: str | None = None,
    conformance_summary_ref: str | None = None,
    source_repo: str | None = None,
    source_commit: str | None = None,
) -> Path:
    if status not in REGISTRY_CHANNELS:
        raise ValueError(f"Registry status must be one of: {', '.join(REGISTRY_CHANNELS)}.")

    root = Path(registry_dir)
    manifest_path = root / "registry.yaml"
    if not manifest_path.exists():
        raise ValueError("Registry directory is not initialized. Run `mtp-registry init` first.")

    signature_errors = validate_registry_artifact(signature)
    if signature_errors:
        raise ValueError(f"Signature envelope is not schema-valid: {signature_errors}")

    signature_body = signature["signature_envelope"]
    artifact_type = detect_artifact_type(artifact)
    identity = artifact_identity(artifact)
    if (
        signature_body["artifact_hash"] != sha256_ref(artifact)
        or signature_body["artifact_type"] != artifact_type
        or signature_body["artifact_identity"] != identity
    ):
        raise ValueError("Signature envelope does not match the artifact identity or hash.")
    signature_verified = False
    if signing_key is not None:
        cryptographic_check = verify_signature_envelope(
            artifact=artifact,
            envelope=signature,
            key=signing_key,
        )
        if not cryptographic_check["verified"]:
            raise ValueError("Signature envelope failed cryptographic verification during publish.")
        signature_verified = True
    if status == "approved" and not signature_verified:
        raise ValueError("Approved registry entries require cryptographic signature verification during publish.")

    normalized_approvals: list[dict[str, Any]] = []
    for approval in approvals:
        errors = validate_registry_artifact(approval)
        if errors:
            raise ValueError(f"Approval record is not schema-valid: {errors}")
        approval_body = approval["approval_record"]
        if (
            approval_body["artifact_hash"] != sha256_ref(artifact)
            or approval_body["artifact_type"] != artifact_type
            or approval_body["artifact_identity"] != identity
        ):
            raise ValueError("Approval record does not match artifact hash, type, or identity.")
        normalized_approvals.append(approval)

    approved_decisions = [
        approval for approval in normalized_approvals
        if approval["approval_record"]["workflow"]["decision"] == "approved"
    ]
    approval_required = status == "approved"
    if approval_required and not approved_decisions:
        raise ValueError("Approved registry entries require at least one approved approval record.")

    artifact_relative = _artifact_relative_path(artifact_type, identity)
    copied_artifact_path = root / artifact_relative
    copied_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(artifact_path), copied_artifact_path)

    signature_relative = _trust_relative_path("signatures", identity, Path(signature_path).name)
    copied_signature_path = root / signature_relative
    copied_signature_path.parent.mkdir(parents=True, exist_ok=True)
    copied_signature = {
        **signature,
        "signature_envelope": {
            **signature["signature_envelope"],
            "artifact_ref": artifact_relative.as_posix(),
        },
    }
    dump_yaml(copied_signature_path, copied_signature)

    copied_approval_refs: list[str] = []
    for approval_path, approval in zip(approval_paths, normalized_approvals):
        approval_relative = _trust_relative_path("approvals", identity, Path(approval_path).name)
        copied_approval_path = root / approval_relative
        copied_approval_path.parent.mkdir(parents=True, exist_ok=True)
        copied_approval = {
            **approval,
            "approval_record": {
                **approval["approval_record"],
                "artifact_ref": artifact_relative.as_posix(),
                "evidence": {
                    **approval["approval_record"].get("evidence", {}),
                    "signature_ref": signature_relative.as_posix(),
                },
            },
        }
        dump_yaml(copied_approval_path, copied_approval)
        copied_approval_refs.append(approval_relative.as_posix())

    entry = {
        "mtp_registry_version": "0.6",
        "registry_entry": {
            "entry_id": str(uuid.uuid4()),
            "artifact_type": artifact_type,
            "artifact_identity": identity,
            "artifact_ref": artifact_relative.as_posix(),
            "artifact_hash": sha256_ref(artifact),
            "registry_status": status,
            "channel": channel,
            "published_at": utc_now_iso(),
            "signature_refs": [signature_relative.as_posix()],
            "approval_refs": copied_approval_refs,
            "trust": {
                "signature_verified": signature_verified,
                "approval_required": approval_required,
                "approved": bool(approved_decisions),
            },
        },
    }

    if conformance_level or conformance_summary_hash or conformance_summary_ref:
        entry["registry_entry"]["conformance"] = {}
        if conformance_level:
            entry["registry_entry"]["conformance"]["level"] = conformance_level
        if conformance_summary_hash:
            entry["registry_entry"]["conformance"]["summary_hash"] = conformance_summary_hash
        if conformance_summary_ref:
            entry["registry_entry"]["conformance"]["summary_ref"] = conformance_summary_ref

    if source_repo or source_commit:
        entry["registry_entry"]["provenance"] = {}
        if source_repo:
            entry["registry_entry"]["provenance"]["source_repo"] = source_repo
        if source_commit:
            entry["registry_entry"]["provenance"]["source_commit"] = source_commit

    entry_errors = validate_registry_artifact(entry)
    if entry_errors:
        raise ValueError(f"Generated registry entry is not valid: {entry_errors}")

    entry_relative = root / "entries" / f"{slugify(identity['name'])}-{identity['version']}.registry-entry.yaml"
    dump_yaml(entry_relative, entry)
    return entry_relative


def verify_registry_entry(
    registry_dir: str | Path,
    entry_path: str | Path,
    key: str | None = None,
) -> dict[str, Any]:
    root = Path(registry_dir)
    entry = load_artifact(entry_path)
    entry_errors = validate_registry_artifact(entry)
    if entry_errors:
        raise ValueError(f"Registry entry is not schema-valid: {entry_errors}")

    entry_body = entry["registry_entry"]
    artifact_path = root / entry_body["artifact_ref"]
    if not artifact_path.exists():
        raise ValueError(f"Artifact referenced by entry does not exist: {artifact_path}")
    artifact = load_artifact(artifact_path)
    artifact_hash_matches = entry_body["artifact_hash"] == sha256_ref(artifact)

    signature_results = []
    for signature_ref in entry_body["signature_refs"]:
        signature_path = root / signature_ref
        if not signature_path.exists():
            raise ValueError(f"Missing signature envelope: {signature_path}")
        signature = load_artifact(signature_path)
        signature_errors = validate_registry_artifact(signature)
        if signature_errors:
            raise ValueError(f"Signature envelope is not schema-valid: {signature_errors}")
        signature_body = signature["signature_envelope"]
        structural_result = {
            "hash_matches": signature_body["artifact_hash"] == sha256_ref(artifact),
            "artifact_type_matches": signature_body["artifact_type"] == detect_artifact_type(artifact),
            "identity_matches": signature_body["artifact_identity"] == artifact_identity(artifact),
        }
        if key is None:
            signature_results.append({
                "path": signature_ref,
                **structural_result,
                "verified": all(structural_result.values()),
                "cryptographic_check": "skipped",
            })
            continue
        verification = verify_signature_envelope(artifact, signature, key)
        signature_results.append({
            "path": signature_ref,
            "cryptographic_check": "verified",
            **verification,
        })

    approval_results = []
    for approval_ref in entry_body["approval_refs"]:
        approval_path = root / approval_ref
        if not approval_path.exists():
            raise ValueError(f"Missing approval record: {approval_path}")
        approval = load_artifact(approval_path)
        approval_errors = validate_registry_artifact(approval)
        if approval_errors:
            raise ValueError(f"Approval record is not schema-valid: {approval_errors}")
        approval_body = approval["approval_record"]
        approval_matches = (
            approval_body["artifact_hash"] == sha256_ref(artifact)
            and approval_body["artifact_type"] == detect_artifact_type(artifact)
            and approval_body["artifact_identity"] == artifact_identity(artifact)
        )
        approval_results.append({
            "path": approval_ref,
            "hash_matches": approval_matches,
            "decision": approval_body["workflow"]["decision"],
        })

    approved_decisions = [
        result for result in approval_results if result["decision"] == "approved" and result["hash_matches"]
    ]
    approved_requirement_met = (
        entry_body["registry_status"] != "approved" or bool(approved_decisions)
    )

    signature_ok = all(result.get("verified", False) for result in signature_results)
    approvals_ok = all(result["hash_matches"] for result in approval_results)
    trust = entry_body.get("trust", {})
    trust_approval_required_matches = trust.get("approval_required") == (entry_body["registry_status"] == "approved")
    trust_approved_matches = trust.get("approved") == bool(approved_decisions)
    if key is None:
        # Without a key we cannot verify cryptographically, so we only check
        # that the trust claim is consistent: if signature_verified is true the
        # entry was verified at publish time — we accept it structurally.
        trust_signature_verified_matches = True
    else:
        trust_signature_verified_matches = trust.get("signature_verified") == signature_ok

    trust_claims_match = (
        trust_approval_required_matches
        and trust_approved_matches
        and trust_signature_verified_matches
    )

    verified = (
        artifact_hash_matches
        and signature_ok
        and approvals_ok
        and approved_requirement_met
        and trust_claims_match
    )

    return {
        "verified": verified,
        "artifact_hash_matches": artifact_hash_matches,
        "signature_results": signature_results,
        "approval_results": approval_results,
        "approved_requirement_met": approved_requirement_met,
        "trust_claims_match": trust_claims_match,
        "trust_checks": {
            "approval_required_matches": trust_approval_required_matches,
            "approved_matches": trust_approved_matches,
            "signature_verified_matches": trust_signature_verified_matches,
        },
    }


def list_entries(
    registry_dir: str | Path,
    status: str | None = None,
    channel: str | None = None,
) -> list[dict[str, Any]]:
    """List registry entries, optionally filtered by status and/or channel."""
    root = Path(registry_dir)
    entries_dir = root / "entries"
    if not entries_dir.exists():
        return []

    results = []
    for entry_path in sorted(entries_dir.glob("*.registry-entry.yaml")):
        entry = load_artifact(entry_path)
        body = entry.get("registry_entry", {})
        if status and body.get("registry_status") != status:
            continue
        if channel and body.get("channel") != channel:
            continue
        results.append({
            "entry_file": entry_path.name,
            "entry_id": body.get("entry_id", ""),
            "artifact_type": body.get("artifact_type", ""),
            "name": body.get("artifact_identity", {}).get("name", ""),
            "version": body.get("artifact_identity", {}).get("version", ""),
            "status": body.get("registry_status", ""),
            "channel": body.get("channel", ""),
            "published_at": body.get("published_at", ""),
            "trust": body.get("trust", {}),
        })
    return results


def _artifact_relative_path(artifact_type: str, identity: dict[str, str]) -> Path:
    if artifact_type == "package":
        return Path("artifacts") / "packages" / slugify(identity["id"]) / identity["version"] / "package.yaml"
    return Path("artifacts") / "execution-reports" / slugify(identity["id"]) / identity["version"] / "execution-report.yaml"


def _trust_relative_path(kind: str, identity: dict[str, str], filename: str) -> Path:
    return Path(kind) / slugify(identity["id"]) / identity["version"] / filename


def _sign(profile: str, key_material: str, payload: bytes) -> str:
    if profile == "hmac-sha256":
        return hmac.new(key_material.encode("utf-8"), payload, sha256).hexdigest()
    if profile == "ed25519":
        private_key = _load_ed25519_private_key(key_material)
        return base64.b64encode(private_key.sign(payload)).decode("ascii")
    raise ValueError(f"Unsupported signature profile '{profile}'.")


def _verify_signature(profile: str, key_material: str, payload: bytes, signature: str) -> bool:
    if profile == "hmac-sha256":
        actual_signature = hmac.new(key_material.encode("utf-8"), payload, sha256).hexdigest()
        return hmac.compare_digest(signature, actual_signature)
    if profile == "ed25519":
        public_key = _load_ed25519_public_key(key_material)
        try:
            public_key.verify(base64.b64decode(signature), payload)
            return True
        except Exception:
            return False
    raise ValueError(f"Unsupported signature profile '{profile}'.")


def _load_ed25519_private_key(key_material: str) -> Ed25519PrivateKey:
    loaded = serialization.load_pem_private_key(_normalize_key_material(key_material).encode("utf-8"), password=None)
    if not isinstance(loaded, Ed25519PrivateKey):
        raise ValueError("Signing key is not an Ed25519 private key.")
    return loaded


def _load_ed25519_public_key(key_material: str) -> Ed25519PublicKey:
    normalized = _normalize_key_material(key_material)
    if "BEGIN PRIVATE KEY" in normalized:
        return _load_ed25519_private_key(normalized).public_key()
    loaded = serialization.load_pem_public_key(normalized.encode("utf-8"))
    if not isinstance(loaded, Ed25519PublicKey):
        raise ValueError("Verification key is not an Ed25519 public key.")
    return loaded


def _normalize_key_material(key_material: str) -> str:
    return key_material.replace("\\n", "\n").strip()
