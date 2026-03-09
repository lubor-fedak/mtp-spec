"""CLI for mtp-registry."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from mtp_registry import __version__
from mtp_registry.artifacts import dump_yaml, load_artifact
from mtp_registry.workflows import (
    create_approval_record,
    create_signature_envelope,
    init_registry,
    list_entries,
    publish_artifact,
    verify_registry_entry,
    verify_signature_envelope,
)


@click.group()
@click.version_option(version=__version__, prog_name="mtp-registry")
def main():
    """MTP Registry — registry, signing, and approval workflows."""
    pass


@main.command()
@click.argument("registry_dir", type=click.Path(path_type=Path))
@click.option("--name", default="MTP Registry", show_default=True, help="Registry display name")
def init(registry_dir: Path, name: str):
    """Initialize a local MTP registry directory."""
    manifest_path = init_registry(registry_dir, name=name)
    click.echo(f"Initialized registry at {manifest_path}")


@main.command()
@click.argument("artifact_file", type=click.Path(exists=True, path_type=Path))
@click.option("--key-env", required=True, help="Environment variable containing the signing key")
@click.option("--key-id", required=True, help="Logical key identifier stored in the signature envelope")
@click.option("--signer", "signer_id", required=True, help="Signer identifier")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None, help="Output envelope file")
def sign(artifact_file: Path, key_env: str, key_id: str, signer_id: str, output: Path | None):
    """Create a detached signature envelope for a package or execution report."""
    key = os.environ.get(key_env)
    if not key:
        click.echo(f"Error: environment variable '{key_env}' is not set.", err=True)
        sys.exit(2)

    artifact = load_artifact(artifact_file)
    try:
        envelope = create_signature_envelope(
            artifact=artifact,
            artifact_ref=str(artifact_file),
            key=key,
            key_id=key_id,
            signer_id=signer_id,
            key_source=f"env:{key_env}",
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    output_path = output or artifact_file.with_name(f"{artifact_file.stem}.signature.v0.6.yaml")
    dump_yaml(output_path, envelope)
    click.echo(f"Signature envelope written to {output_path}")


@main.command()
@click.argument("artifact_file", type=click.Path(exists=True, path_type=Path))
@click.option("--signature", "signature_file", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--key-env", required=True, help="Environment variable containing the signing key")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def verify(artifact_file: Path, signature_file: Path, key_env: str, output_format: str):
    """Verify a detached signature envelope against an artifact."""
    key = os.environ.get(key_env)
    if not key:
        click.echo(f"Error: environment variable '{key_env}' is not set.", err=True)
        sys.exit(2)

    artifact = load_artifact(artifact_file)
    envelope = load_artifact(signature_file)

    try:
        result = verify_signature_envelope(artifact=artifact, envelope=envelope, key=key)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if output_format == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo("VERIFIED" if result["verified"] else "FAILED")
        for field in ("hash_matches", "signature_matches", "artifact_type_matches", "identity_matches"):
            click.echo(f"{field}: {result[field]}")

    sys.exit(0 if result["verified"] else 1)


@main.command()
@click.argument("artifact_file", type=click.Path(exists=True, path_type=Path))
@click.option("--signature", "signature_file", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--approver-id", required=True)
@click.option("--approver-name", required=True)
@click.option("--role", required=True)
@click.option("--status", type=click.Choice(["approved", "rejected"]), required=True)
@click.option("--policy", required=True)
@click.option("--rationale", required=True)
@click.option("--ticket-ref", default=None)
@click.option("--conformance-ref", default=None)
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
def approve(
    artifact_file: Path,
    signature_file: Path,
    approver_id: str,
    approver_name: str,
    role: str,
    status: str,
    policy: str,
    rationale: str,
    ticket_ref: str | None,
    conformance_ref: str | None,
    output: Path | None,
):
    """Create an approval record for a signed artifact."""
    artifact = load_artifact(artifact_file)
    signature = load_artifact(signature_file)

    try:
        approval = create_approval_record(
            artifact=artifact,
            artifact_ref=str(artifact_file),
            signature=signature,
            signature_ref=str(signature_file),
            approver_id=approver_id,
            approver_name=approver_name,
            role=role,
            status=status,
            policy=policy,
            rationale=rationale,
            ticket_ref=ticket_ref,
            conformance_ref=conformance_ref,
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    output_path = output or artifact_file.with_name(f"{artifact_file.stem}.approval.v0.6.yaml")
    dump_yaml(output_path, approval)
    click.echo(f"Approval record written to {output_path}")


@main.command()
@click.argument("artifact_file", type=click.Path(exists=True, path_type=Path))
@click.option("--registry-dir", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--signature", "signature_file", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--key-env", default=None, help="Optional environment variable for cryptographic verification during publish")
@click.option("--approval", "approval_files", multiple=True, type=click.Path(exists=True, path_type=Path))
@click.option("--status", type=click.Choice(["draft", "review", "approved", "deprecated"]), required=True)
@click.option("--channel", default="internal", show_default=True)
@click.option("--conformance-level", type=click.Choice(["l1", "l2", "l3"]), default=None)
@click.option("--conformance-summary-hash", default=None)
@click.option("--conformance-summary-ref", default=None)
@click.option("--source-repo", default=None)
@click.option("--source-commit", default=None)
def publish(
    artifact_file: Path,
    registry_dir: Path,
    signature_file: Path,
    key_env: str | None,
    approval_files: tuple[Path, ...],
    status: str,
    channel: str,
    conformance_level: str | None,
    conformance_summary_hash: str | None,
    conformance_summary_ref: str | None,
    source_repo: str | None,
    source_commit: str | None,
):
    """Publish an artifact plus trust sidecars into a local registry."""
    artifact = load_artifact(artifact_file)
    signature = load_artifact(signature_file)
    approvals = [load_artifact(path) for path in approval_files]
    signing_key = os.environ.get(key_env) if key_env else None
    if key_env and signing_key is None:
        click.echo(f"Error: environment variable '{key_env}' is not set.", err=True)
        sys.exit(2)

    try:
        entry_path = publish_artifact(
            artifact_path=artifact_file,
            artifact=artifact,
            registry_dir=registry_dir,
            signature_path=signature_file,
            signature=signature,
            signing_key=signing_key,
            approval_paths=list(approval_files),
            approvals=approvals,
            status=status,
            channel=channel,
            conformance_level=conformance_level,
            conformance_summary_hash=conformance_summary_hash,
            conformance_summary_ref=conformance_summary_ref,
            source_repo=source_repo,
            source_commit=source_commit,
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Registry entry written to {entry_path}")


@main.command(name="list")
@click.argument("registry_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--status", type=click.Choice(["draft", "review", "approved", "deprecated"]), default=None,
              help="Filter by registry status")
@click.option("--channel", default=None, help="Filter by channel")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def list_cmd(registry_dir: Path, status: str | None, channel: str | None, output_format: str):
    """List registry entries, optionally filtered by status or channel."""
    entries = list_entries(registry_dir, status=status, channel=channel)

    if output_format == "json":
        click.echo(json.dumps(entries, indent=2))
    else:
        if not entries:
            click.echo("No entries found.")
            return
        click.echo(f"{'Name':30s} {'Version':10s} {'Status':12s} {'Channel':12s} {'Type':10s}")
        click.echo("-" * 74)
        for entry in entries:
            click.echo(
                f"{entry['name']:30s} {entry['version']:10s} "
                f"{entry['status']:12s} {entry['channel']:12s} {entry['artifact_type']:10s}"
            )
        click.echo(f"\nTotal: {len(entries)} entries")


@main.command(name="check-entry")
@click.argument("entry_file", type=click.Path(exists=True, path_type=Path))
@click.option("--registry-dir", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--key-env", default=None, help="Optional environment variable for cryptographic signature verification")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def check_entry(entry_file: Path, registry_dir: Path, key_env: str | None, output_format: str):
    """Validate a registry entry and all referenced trust artifacts."""
    key = os.environ.get(key_env) if key_env else None

    try:
        result = verify_registry_entry(
            registry_dir=registry_dir,
            entry_path=entry_file,
            key=key,
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if output_format == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo("VERIFIED" if result["verified"] else "FAILED")
        click.echo(f"artifact_hash_matches: {result['artifact_hash_matches']}")
        click.echo(f"approved_requirement_met: {result['approved_requirement_met']}")
        click.echo(f"signatures_checked: {len(result['signature_results'])}")
        click.echo(f"approvals_checked: {len(result['approval_results'])}")

    sys.exit(0 if result["verified"] else 1)


if __name__ == "__main__":
    main()
