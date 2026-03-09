"""Tests for mtp-registry artifact utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from mtp_registry.artifacts import (
    artifact_identity,
    canonical_bytes,
    detect_artifact_type,
    detect_primary_version,
    sha256_hex,
    sha256_ref,
    slugify,
    validate_primary_artifact,
    validate_registry_artifact,
)


_HERE = Path(__file__).parent
_PROJECT = _HERE.parent.parent.parent
PACKAGE_FILE = _PROJECT / "examples" / "churn-risk-scoring-v0.2.yaml"


class TestDetectArtifactType:
    def test_package(self) -> None:
        assert detect_artifact_type({"mtp_version": "0.2"}) == "package"

    def test_execution_report(self) -> None:
        assert detect_artifact_type({"execution_report": {}}) == "execution_report"

    def test_signature_envelope(self) -> None:
        assert detect_artifact_type({"signature_envelope": {}}) == "signature_envelope"

    def test_approval_record(self) -> None:
        assert detect_artifact_type({"approval_record": {}}) == "approval_record"

    def test_registry_entry(self) -> None:
        assert detect_artifact_type({"registry_entry": {}}) == "registry_entry"

    def test_registry_manifest(self) -> None:
        assert detect_artifact_type({"mtp_registry_version": "0.6", "registry": {}}) == "registry_manifest"

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot detect"):
            detect_artifact_type({"unknown": True})


class TestDetectPrimaryVersion:
    def test_package_v02(self) -> None:
        assert detect_primary_version({"mtp_version": "0.2"}, "package") == "0.2"

    def test_package_v01_default(self) -> None:
        assert detect_primary_version({}, "package") == "0.1"

    def test_execution_report(self) -> None:
        data = {"execution_report": {"mtp_spec_version": "0.2"}}
        assert detect_primary_version(data, "execution_report") == "0.2"

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            detect_primary_version({}, "signature_envelope")


class TestCanonicalBytes:
    def test_deterministic(self) -> None:
        data = {"b": 2, "a": 1}
        result = canonical_bytes(data)
        assert result == b'{"a":1,"b":2}'

    def test_sorted_keys(self) -> None:
        d1 = {"z": 1, "a": 2}
        d2 = {"a": 2, "z": 1}
        assert canonical_bytes(d1) == canonical_bytes(d2)


class TestSha256:
    def test_hex_is_64_chars(self) -> None:
        result = sha256_hex({"test": True})
        assert len(result) == 64

    def test_ref_format(self) -> None:
        ref = sha256_ref({"test": True})
        assert ref["algorithm"] == "sha256"
        assert ref["value"].startswith("sha256:")
        assert len(ref["value"]) == 7 + 64  # "sha256:" + 64 hex chars

    def test_deterministic(self) -> None:
        assert sha256_hex({"a": 1}) == sha256_hex({"a": 1})

    def test_different_data_different_hash(self) -> None:
        assert sha256_hex({"a": 1}) != sha256_hex({"a": 2})


class TestArtifactIdentity:
    def test_package_identity(self) -> None:
        data = {"mtp_version": "0.2", "package": {"id": "pkg-1", "version": "1.0.0", "name": "Test"}}
        identity = artifact_identity(data)
        assert identity == {"id": "pkg-1", "version": "1.0.0", "name": "Test"}

    def test_execution_report_identity(self) -> None:
        data = {"execution_report": {"mtp_package_id": "pkg-1", "mtp_package_version": "1.0.0"}}
        identity = artifact_identity(data)
        assert identity["id"] == "pkg-1"
        assert identity["version"] == "1.0.0"

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported artifact type"):
            artifact_identity({"signature_envelope": {}})


class TestSlugify:
    def test_simple(self) -> None:
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self) -> None:
        assert slugify("My Package (v2)!") == "my-package-v2"

    def test_consecutive_hyphens_collapsed(self) -> None:
        assert slugify("a---b") == "a-b"

    def test_empty_string_returns_artifact(self) -> None:
        assert slugify("!!!") == "artifact"

    def test_uuid_passthrough(self) -> None:
        result = slugify("b2c3d4e5-f6a7-8901-bcde-f12345678901")
        assert result == "b2c3d4e5-f6a7-8901-bcde-f12345678901"


class TestValidation:
    def test_valid_package_passes(self) -> None:
        from mtp_registry.artifacts import load_artifact
        data = load_artifact(PACKAGE_FILE)
        errors = validate_primary_artifact(data)
        assert errors == []

    def test_empty_package_has_errors(self) -> None:
        errors = validate_primary_artifact({"mtp_version": "0.2"})
        assert len(errors) > 0

    def test_registry_artifact_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="No registry schema"):
            validate_registry_artifact({"mtp_version": "0.2"})
