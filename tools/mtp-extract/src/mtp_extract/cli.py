"""CLI for mtp-extract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
import yaml

from mtp_lint.schema_validator import detect_artifact_type, detect_version, load_package, validate_schema

from mtp_extract import __version__
from mtp_extract.conversation import load_conversation
from mtp_extract.heuristics import (
    build_draft_package,
    build_policy_from_scan,
    extract_provenance_map,
)
from mtp_extract.merge import merge_packages


@click.group()
@click.version_option(version=__version__, prog_name="mtp-extract")
def main() -> None:
    """MTP Extract — draft package extraction from conversations."""
    pass


@main.command()
@click.argument("conversation_file", type=click.Path(exists=True, path_type=Path))
@click.option("--name", default=None, help="Override package name")
@click.option("--author", default="mtp-extract", show_default=True)
@click.option("--source-platform", default=None)
@click.option("--precheck", is_flag=True, default=False, help="Populate policy envelope using the redaction scanner")
@click.option("--client-identifier", "client_identifiers", multiple=True, help="Optional client identifiers for policy precheck")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml")
def draft(
    conversation_file: Path,
    name: str | None,
    author: str,
    source_platform: str | None,
    precheck: bool,
    client_identifiers: tuple[str, ...],
    output: Path | None,
    output_format: str,
) -> None:
    """Generate a draft v0.2 MTP package from a conversation."""
    try:
        messages = load_conversation(conversation_file)
        package = build_draft_package(
            messages=messages,
            name=name,
            author=author,
            source_platform=source_platform,
            precheck=precheck,
            client_identifiers=list(client_identifiers) or None,
        )
        errors = validate_schema(package, "package", "0.2")
        if errors:
            raise ValueError(f"Generated package is not schema-valid: {errors}")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    _emit_artifact(package, output, output_format)


@main.command()
@click.argument("package_file", type=click.Path(exists=True, path_type=Path))
@click.option("--client-identifier", "client_identifiers", multiple=True, help="Optional client identifiers for policy precheck")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml")
def precheck(package_file: Path, client_identifiers: tuple[str, ...], output: Path | None, output_format: str) -> None:
    """Populate or refresh the package policy envelope using the redaction scanner."""
    try:
        package = load_package(package_file)
        if detect_artifact_type(package) != "package":
            raise ValueError("File must be an MTP package.")
        package["policy"] = build_policy_from_scan(package, list(client_identifiers) or None)
        errors = validate_schema(package, "package", detect_version(package, "package"))
        if errors:
            raise ValueError(f"Updated package is not schema-valid: {errors}")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    _emit_artifact(package, output, output_format)


@main.command(name="map")
@click.argument("package_file", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def provenance_map(package_file: Path, output_format: str) -> None:
    """Emit a provenance map for a package."""
    try:
        package = load_package(package_file)
        entries = extract_provenance_map(package)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if output_format == "json":
        click.echo(json.dumps({"entries": entries, "total": len(entries)}, indent=2))
        return

    click.echo(f"Provenance entries: {len(entries)}")
    for entry in entries:
        click.echo(f"- [{entry['kind']}] {entry['label']} -> {entry['source_ref']} ({entry['confidence']})")


@main.command()
@click.argument("base_file", type=click.Path(exists=True, path_type=Path))
@click.argument("overlay_file", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml")
def merge(base_file: Path, overlay_file: Path, output: Path | None, output_format: str) -> None:
    """Merge two MTP packages into one updated package."""
    try:
        base = load_package(base_file)
        overlay = load_package(overlay_file)
        merged = merge_packages(base, overlay)
        errors = validate_schema(merged, "package", "0.2")
        if errors:
            raise ValueError(f"Merged package is not schema-valid: {errors}")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    _emit_artifact(merged, output, output_format)


def _emit_artifact(data: dict[str, Any], output: Path | None, output_format: str) -> None:
    if output_format == "json":
        payload = json.dumps(data, indent=2)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(payload, encoding="utf-8")
        else:
            click.echo(payload)
        return

    payload = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    else:
        click.echo(payload)


if __name__ == "__main__":
    main()
