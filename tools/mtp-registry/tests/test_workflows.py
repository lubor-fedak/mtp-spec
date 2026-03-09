"""Tests for mtp-registry workflow functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from mtp_registry.artifacts import load_artifact, sha256_ref
from mtp_registry.workflows import (
    create_approval_record,
    create_signature_envelope,
    init_registry,
    list_entries,
    publish_artifact,
    verify_registry_entry,
    verify_signature_envelope,
)


_HERE = Path(__file__).parent
_PROJECT = _HERE.parent.parent.parent
PACKAGE_FILE = _PROJECT / "examples" / "churn-risk-scoring-v0.2.yaml"
KEY = "test-workflow-secret-key"


@pytest.fixture
def package() -> dict:
    return load_artifact(PACKAGE_FILE)


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    init_registry(tmp_path / "registry", name="Test")
    return tmp_path / "registry"


@pytest.fixture
def envelope(package: dict) -> dict:
    return create_signature_envelope(
        artifact=package,
        artifact_ref=str(PACKAGE_FILE),
        key=KEY,
        key_id="test-key",
        signer_id="test-bot",
        key_source="env:TEST_KEY",
    )


class TestInitRegistry:
    def test_creates_manifest(self, tmp_path: Path) -> None:
        manifest_path = init_registry(tmp_path / "reg", name="My Registry")
        assert manifest_path.exists()
        data = load_artifact(manifest_path)
        assert data["registry"]["name"] == "My Registry"
        assert data["mtp_registry_version"] == "0.6"

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        init_registry(tmp_path / "reg", name="Test")
        assert (tmp_path / "reg" / "artifacts" / "packages").is_dir()
        assert (tmp_path / "reg" / "signatures").is_dir()
        assert (tmp_path / "reg" / "approvals").is_dir()
        assert (tmp_path / "reg" / "entries").is_dir()


class TestCreateSignatureEnvelope:
    def test_creates_valid_envelope(self, envelope: dict) -> None:
        assert "signature_envelope" in envelope
        body = envelope["signature_envelope"]
        assert body["artifact_type"] == "package"
        assert body["signature_profile"]["profile"] == "hmac-sha256"
        assert len(body["signature"]) == 64

    def test_invalid_artifact_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot sign invalid"):
            create_signature_envelope(
                artifact={"mtp_version": "0.2"},
                artifact_ref="test",
                key=KEY,
                key_id="k",
                signer_id="s",
                key_source="env:K",
            )


class TestVerifySignatureEnvelope:
    def test_valid_verification(self, package: dict, envelope: dict) -> None:
        result = verify_signature_envelope(package, envelope, KEY)
        assert result["verified"] is True
        assert result["hash_matches"] is True
        assert result["signature_matches"] is True

    def test_wrong_key_fails(self, package: dict, envelope: dict) -> None:
        result = verify_signature_envelope(package, envelope, "wrong-key")
        assert result["verified"] is False
        assert result["signature_matches"] is False

    def test_tampered_artifact_fails(self, package: dict, envelope: dict) -> None:
        tampered = {**package, "mtp_version": "0.1"}
        result = verify_signature_envelope(tampered, envelope, KEY)
        assert result["verified"] is False


class TestCreateApprovalRecord:
    def test_creates_valid_approval(self, package: dict, envelope: dict) -> None:
        approval = create_approval_record(
            artifact=package,
            artifact_ref=str(PACKAGE_FILE),
            signature=envelope,
            signature_ref="sig.yaml",
            approver_id="reviewer",
            approver_name="Reviewer",
            role="governance",
            status="approved",
            policy="test-policy",
            rationale="Looks good.",
        )
        assert approval["approval_record"]["workflow"]["decision"] == "approved"
        assert approval["approval_record"]["artifact_hash"] == sha256_ref(package)

    def test_rejected_status(self, package: dict, envelope: dict) -> None:
        approval = create_approval_record(
            artifact=package,
            artifact_ref=str(PACKAGE_FILE),
            signature=envelope,
            signature_ref="sig.yaml",
            approver_id="reviewer",
            approver_name="Reviewer",
            role="governance",
            status="rejected",
            policy="test-policy",
            rationale="Needs rework.",
        )
        assert approval["approval_record"]["workflow"]["decision"] == "rejected"

    def test_invalid_status_raises(self, package: dict, envelope: dict) -> None:
        with pytest.raises(ValueError, match="approved.*rejected"):
            create_approval_record(
                artifact=package,
                artifact_ref=str(PACKAGE_FILE),
                signature=envelope,
                signature_ref="sig.yaml",
                approver_id="r",
                approver_name="R",
                role="g",
                status="pending",
                policy="p",
                rationale="r",
            )


class TestListEntries:
    def test_empty_registry(self, registry: Path) -> None:
        entries = list_entries(registry)
        assert entries == []

    def test_lists_published_entry(self, package: dict, registry: Path) -> None:
        envelope = create_signature_envelope(
            artifact=package,
            artifact_ref=str(PACKAGE_FILE),
            key=KEY,
            key_id="test-key",
            signer_id="test-bot",
            key_source="env:TEST_KEY",
        )
        sig_path = registry.parent / "sig.yaml"
        from mtp_registry.artifacts import dump_yaml
        dump_yaml(sig_path, envelope)

        publish_artifact(
            artifact_path=PACKAGE_FILE,
            artifact=package,
            registry_dir=registry,
            signature_path=sig_path,
            signature=envelope,
            signing_key=KEY,
            approval_paths=[],
            approvals=[],
            status="draft",
            channel="internal",
        )

        entries = list_entries(registry)
        assert len(entries) == 1
        assert entries[0]["status"] == "draft"

    def test_filter_by_status(self, package: dict, registry: Path) -> None:
        envelope = create_signature_envelope(
            artifact=package,
            artifact_ref=str(PACKAGE_FILE),
            key=KEY,
            key_id="test-key",
            signer_id="test-bot",
            key_source="env:TEST_KEY",
        )
        sig_path = registry.parent / "sig.yaml"
        from mtp_registry.artifacts import dump_yaml
        dump_yaml(sig_path, envelope)

        publish_artifact(
            artifact_path=PACKAGE_FILE,
            artifact=package,
            registry_dir=registry,
            signature_path=sig_path,
            signature=envelope,
            signing_key=KEY,
            approval_paths=[],
            approvals=[],
            status="draft",
            channel="internal",
        )

        assert len(list_entries(registry, status="draft")) == 1
        assert len(list_entries(registry, status="approved")) == 0


class TestVerifyRegistryEntry:
    def test_structural_verification_of_approved_entry(self, package: dict, registry: Path) -> None:
        """Structural-only check (no key) should pass for a properly published entry."""
        envelope = create_signature_envelope(
            artifact=package,
            artifact_ref=str(PACKAGE_FILE),
            key=KEY,
            key_id="test-key",
            signer_id="test-bot",
            key_source="env:TEST_KEY",
        )
        approval = create_approval_record(
            artifact=package,
            artifact_ref=str(PACKAGE_FILE),
            signature=envelope,
            signature_ref="sig.yaml",
            approver_id="reviewer",
            approver_name="Reviewer",
            role="governance",
            status="approved",
            policy="test-policy",
            rationale="OK.",
        )
        sig_path = registry.parent / "sig.yaml"
        appr_path = registry.parent / "approval.yaml"
        from mtp_registry.artifacts import dump_yaml
        dump_yaml(sig_path, envelope)
        dump_yaml(appr_path, approval)

        entry_path = publish_artifact(
            artifact_path=PACKAGE_FILE,
            artifact=package,
            registry_dir=registry,
            signature_path=sig_path,
            signature=envelope,
            signing_key=KEY,
            approval_paths=[appr_path],
            approvals=[approval],
            status="approved",
            channel="internal",
        )

        # Structural check (no key) should pass
        result = verify_registry_entry(registry, entry_path, key=None)
        assert result["verified"] is True
        assert result["signature_results"][0]["cryptographic_check"] == "skipped"

        # Cryptographic check should also pass
        result_crypto = verify_registry_entry(registry, entry_path, key=KEY)
        assert result_crypto["verified"] is True
