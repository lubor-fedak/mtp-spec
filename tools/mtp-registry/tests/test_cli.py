"""Tests for mtp-registry CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from mtp_registry.cli import main
from mtp_registry.artifacts import dump_yaml, load_artifact


_HERE = Path(__file__).parent
_PROJECT = _HERE.parent.parent.parent
PACKAGE_FILE = _PROJECT / "examples" / "churn-risk-scoring-v0.2.yaml"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def signing_env() -> dict[str, str]:
    return {"MTP_REGISTRY_SIGNING_KEY": "example-registry-shared-secret-v0.6"}


class TestRegistryCli:
    def test_init_registry(self, runner: CliRunner, tmp_path: Path) -> None:
        registry_dir = tmp_path / "registry"
        result = runner.invoke(main, ["init", str(registry_dir), "--name", "Test Registry"])
        assert result.exit_code == 0
        assert (registry_dir / "registry.yaml").exists()
        assert (registry_dir / "artifacts" / "packages").exists()
        assert (registry_dir / "signatures").exists()

    def test_sign_and_verify(self, runner: CliRunner, tmp_path: Path, signing_env: dict[str, str]) -> None:
        signature_path = tmp_path / "package.signature.yaml"
        sign_result = runner.invoke(
            main,
            [
                "sign",
                str(PACKAGE_FILE),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--key-id",
                "example-key",
                "--signer",
                "release-bot",
                "--output",
                str(signature_path),
            ],
            env=signing_env,
        )
        assert sign_result.exit_code == 0
        assert signature_path.exists()

        verify_result = runner.invoke(
            main,
            [
                "verify",
                str(PACKAGE_FILE),
                "--signature",
                str(signature_path),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
            ],
            env=signing_env,
        )
        assert verify_result.exit_code == 0
        assert "VERIFIED" in verify_result.output

    def test_verify_fails_with_wrong_key(self, runner: CliRunner, tmp_path: Path, signing_env: dict[str, str]) -> None:
        signature_path = tmp_path / "package.signature.yaml"
        runner.invoke(
            main,
            [
                "sign",
                str(PACKAGE_FILE),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--key-id",
                "example-key",
                "--signer",
                "release-bot",
                "--output",
                str(signature_path),
            ],
            env=signing_env,
        )

        verify_result = runner.invoke(
            main,
            [
                "verify",
                str(PACKAGE_FILE),
                "--signature",
                str(signature_path),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
            ],
            env={"MTP_REGISTRY_SIGNING_KEY": "wrong-secret"},
        )
        assert verify_result.exit_code == 1

    def test_approve_publish_and_check_entry(self, runner: CliRunner, tmp_path: Path, signing_env: dict[str, str]) -> None:
        registry_dir = tmp_path / "registry"
        signature_path = tmp_path / "package.signature.yaml"
        approval_path = tmp_path / "package.approval.yaml"

        init_result = runner.invoke(main, ["init", str(registry_dir), "--name", "Test Registry"])
        assert init_result.exit_code == 0

        sign_result = runner.invoke(
            main,
            [
                "sign",
                str(PACKAGE_FILE),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--key-id",
                "example-key",
                "--signer",
                "release-bot",
                "--output",
                str(signature_path),
            ],
            env=signing_env,
        )
        assert sign_result.exit_code == 0

        approve_result = runner.invoke(
            main,
            [
                "approve",
                str(PACKAGE_FILE),
                "--signature",
                str(signature_path),
                "--approver-id",
                "risk-committee",
                "--approver-name",
                "Risk Committee",
                "--role",
                "governance",
                "--status",
                "approved",
                "--policy",
                "enterprise-release-v1",
                "--rationale",
                "Approved for internal registry publication.",
                "--output",
                str(approval_path),
            ],
        )
        assert approve_result.exit_code == 0

        publish_result = runner.invoke(
            main,
            [
                "publish",
                str(PACKAGE_FILE),
                "--registry-dir",
                str(registry_dir),
                "--signature",
                str(signature_path),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--approval",
                str(approval_path),
                "--status",
                "approved",
                "--channel",
                "internal",
                "--conformance-level",
                "l3",
                "--conformance-summary-hash",
                "sha256:" + ("a" * 64),
            ],
            env=signing_env,
        )
        assert publish_result.exit_code == 0

        entries = list((registry_dir / "entries").glob("*.registry-entry.yaml"))
        assert len(entries) == 1

        check_result = runner.invoke(
            main,
            [
                "check-entry",
                str(entries[0]),
                "--registry-dir",
                str(registry_dir),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--format",
                "json",
            ],
            env=signing_env,
        )
        assert check_result.exit_code == 0
        payload = json.loads(check_result.output)
        assert payload["verified"] is True

    def test_publish_approved_requires_approval(self, runner: CliRunner, tmp_path: Path, signing_env: dict[str, str]) -> None:
        registry_dir = tmp_path / "registry"
        signature_path = tmp_path / "package.signature.yaml"
        runner.invoke(main, ["init", str(registry_dir)])
        runner.invoke(
            main,
            [
                "sign",
                str(PACKAGE_FILE),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--key-id",
                "example-key",
                "--signer",
                "release-bot",
                "--output",
                str(signature_path),
            ],
            env=signing_env,
        )

        publish_result = runner.invoke(
            main,
            [
                "publish",
                str(PACKAGE_FILE),
                "--registry-dir",
                str(registry_dir),
                "--signature",
                str(signature_path),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--status",
                "approved",
                "--channel",
                "internal",
            ],
            env=signing_env,
        )
        assert publish_result.exit_code == 1

    def test_publish_approved_requires_signature_verification(self, runner: CliRunner, tmp_path: Path, signing_env: dict[str, str]) -> None:
        registry_dir = tmp_path / "registry"
        signature_path = tmp_path / "package.signature.yaml"
        approval_path = tmp_path / "package.approval.yaml"

        runner.invoke(main, ["init", str(registry_dir)])
        runner.invoke(
            main,
            [
                "sign",
                str(PACKAGE_FILE),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--key-id",
                "example-key",
                "--signer",
                "release-bot",
                "--output",
                str(signature_path),
            ],
            env=signing_env,
        )
        runner.invoke(
            main,
            [
                "approve",
                str(PACKAGE_FILE),
                "--signature",
                str(signature_path),
                "--approver-id",
                "risk-committee",
                "--approver-name",
                "Risk Committee",
                "--role",
                "governance",
                "--status",
                "approved",
                "--policy",
                "enterprise-release-v1",
                "--rationale",
                "Approved for internal registry publication.",
                "--output",
                str(approval_path),
            ],
        )

        publish_result = runner.invoke(
            main,
            [
                "publish",
                str(PACKAGE_FILE),
                "--registry-dir",
                str(registry_dir),
                "--signature",
                str(signature_path),
                "--approval",
                str(approval_path),
                "--status",
                "approved",
                "--channel",
                "internal",
            ],
        )
        assert publish_result.exit_code == 1

    def test_check_entry_fails_on_trust_claim_mismatch(self, runner: CliRunner, tmp_path: Path, signing_env: dict[str, str]) -> None:
        registry_dir = tmp_path / "registry"
        signature_path = tmp_path / "package.signature.yaml"
        approval_path = tmp_path / "package.approval.yaml"

        runner.invoke(main, ["init", str(registry_dir), "--name", "Test Registry"])
        runner.invoke(
            main,
            [
                "sign",
                str(PACKAGE_FILE),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--key-id",
                "example-key",
                "--signer",
                "release-bot",
                "--output",
                str(signature_path),
            ],
            env=signing_env,
        )
        runner.invoke(
            main,
            [
                "approve",
                str(PACKAGE_FILE),
                "--signature",
                str(signature_path),
                "--approver-id",
                "risk-committee",
                "--approver-name",
                "Risk Committee",
                "--role",
                "governance",
                "--status",
                "approved",
                "--policy",
                "enterprise-release-v1",
                "--rationale",
                "Approved for internal registry publication.",
                "--output",
                str(approval_path),
            ],
        )
        runner.invoke(
            main,
            [
                "publish",
                str(PACKAGE_FILE),
                "--registry-dir",
                str(registry_dir),
                "--signature",
                str(signature_path),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--approval",
                str(approval_path),
                "--status",
                "approved",
                "--channel",
                "internal",
            ],
            env=signing_env,
        )

        entry_file = next((registry_dir / "entries").glob("*.registry-entry.yaml"))
        entry = load_artifact(entry_file)
        entry["registry_entry"]["trust"]["approved"] = False
        dump_yaml(entry_file, entry)

        check_result = runner.invoke(
            main,
            [
                "check-entry",
                str(entry_file),
                "--registry-dir",
                str(registry_dir),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
            ],
            env=signing_env,
        )
        assert check_result.exit_code == 1

    def test_check_entry_without_key_passes_structurally_for_approved_entry(self, runner: CliRunner, tmp_path: Path, signing_env: dict[str, str]) -> None:
        """Structural-only check of a properly published approved entry should succeed.

        The entry was cryptographically verified at publish time; consumers who
        lack the key can still verify structural integrity (hashes, types,
        identities) without re-checking the HMAC.
        """
        registry_dir = tmp_path / "registry"
        signature_path = tmp_path / "package.signature.yaml"
        approval_path = tmp_path / "package.approval.yaml"

        runner.invoke(main, ["init", str(registry_dir)])
        runner.invoke(
            main,
            [
                "sign",
                str(PACKAGE_FILE),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--key-id",
                "example-key",
                "--signer",
                "release-bot",
                "--output",
                str(signature_path),
            ],
            env=signing_env,
        )
        runner.invoke(
            main,
            [
                "approve",
                str(PACKAGE_FILE),
                "--signature",
                str(signature_path),
                "--approver-id",
                "risk-committee",
                "--approver-name",
                "Risk Committee",
                "--role",
                "governance",
                "--status",
                "approved",
                "--policy",
                "enterprise-release-v1",
                "--rationale",
                "Approved for internal registry publication.",
                "--output",
                str(approval_path),
            ],
        )
        runner.invoke(
            main,
            [
                "publish",
                str(PACKAGE_FILE),
                "--registry-dir",
                str(registry_dir),
                "--signature",
                str(signature_path),
                "--key-env",
                "MTP_REGISTRY_SIGNING_KEY",
                "--approval",
                str(approval_path),
                "--status",
                "approved",
                "--channel",
                "internal",
            ],
            env=signing_env,
        )

        entry_file = next((registry_dir / "entries").glob("*.registry-entry.yaml"))
        check_result = runner.invoke(
            main,
            [
                "check-entry",
                str(entry_file),
                "--registry-dir",
                str(registry_dir),
                "--format",
                "json",
            ],
        )
        assert check_result.exit_code == 0
        payload = json.loads(check_result.output)
        assert payload["verified"] is True
        assert payload["signature_results"][0]["cryptographic_check"] == "skipped"
