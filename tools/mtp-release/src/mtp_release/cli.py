"""CLI for mtp-release."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml

from mtp_release import __version__
from mtp_release.artifacts import detect_artifact_type, dump_yaml, load_artifact, validate_artifact
from mtp_release.builder import build_compatibility_contract, build_provider_matrix


@click.group()
@click.version_option(version=__version__, prog_name="mtp-release")
def main() -> None:
    """MTP Release — build provider matrices and compatibility contracts."""
    pass


@main.command()
@click.argument("artifact_file", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def validate(artifact_file: Path, output_format: str) -> None:
    """Validate a provider matrix or compatibility contract."""
    try:
        artifact = load_artifact(artifact_file)
        artifact_type = detect_artifact_type(artifact)
        errors = validate_artifact(artifact)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    payload = {
        "artifact_type": artifact_type,
        "valid": not errors,
        "errors": errors,
    }
    if output_format == "json":
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo(f"Artifact type: {artifact_type}")
        click.echo("VALID" if not errors else "INVALID")
        for error in errors:
            click.echo(f"- {error}")
    sys.exit(0 if not errors else 1)


@main.command()
@click.option("--benchmark-result", "benchmark_result_file", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--certification", "certification_files", multiple=True, type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), required=True)
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml")
def matrix(
    benchmark_result_file: Path,
    certification_files: tuple[Path, ...],
    output: Path,
    output_format: str,
) -> None:
    """Build a provider certification matrix from benchmark artifacts."""
    try:
        benchmark_result = load_artifact(benchmark_result_file)
        certifications = [(str(path), load_artifact(path)) for path in certification_files]
        matrix_artifact = build_provider_matrix(
            benchmark_result=benchmark_result,
            benchmark_result_ref=str(benchmark_result_file),
            certifications=certifications,
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    _emit(output, output_format, matrix_artifact)


@main.command(name="contract")
@click.option("--release-version", required=True)
@click.option("--provider-matrix", "provider_matrix_ref", required=True)
@click.option("--conformance-level", default="l3", show_default=True, type=click.Choice(["l1", "l2", "l3", "all"]))
@click.option("--conformance-summary-hash", default=None)
@click.option("--conformance-summary-ref", default=None)
@click.option("--architecture-ref", required=True)
@click.option("--core-spec-ref", default="spec/MTP-SPEC-v0.2.md", show_default=True)
@click.option("--registry-spec-ref", default="spec/MTP-REGISTRY-v0.6.md", show_default=True)
@click.option("--compatibility-spec-ref", default="spec/MTP-COMPATIBILITY-v1.0.md", show_default=True)
@click.option("--output", "-o", type=click.Path(path_type=Path), required=True)
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml")
def contract_cmd(
    release_version: str,
    provider_matrix_ref: str,
    conformance_level: str,
    conformance_summary_hash: str | None,
    conformance_summary_ref: str | None,
    architecture_ref: str,
    core_spec_ref: str,
    registry_spec_ref: str,
    compatibility_spec_ref: str,
    output: Path,
    output_format: str,
) -> None:
    """Build a compatibility contract for a production release."""
    try:
        contract = build_compatibility_contract(
            release_version=release_version,
            provider_matrix_ref=provider_matrix_ref,
            conformance_level=conformance_level,
            architecture_ref=architecture_ref,
            core_spec_ref=core_spec_ref,
            registry_spec_ref=registry_spec_ref,
            compatibility_spec_ref=compatibility_spec_ref,
            conformance_summary_hash=conformance_summary_hash,
            conformance_summary_ref=conformance_summary_ref,
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    _emit(output, output_format, contract)


def _emit(output: Path, output_format: str, payload: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        click.echo(json.dumps(payload, indent=2))
        return
    dump_yaml(output, payload)
    click.echo(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False))


if __name__ == "__main__":
    main()
