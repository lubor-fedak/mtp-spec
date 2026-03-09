"""MTP Lint CLI — validate, scan, and score MTP packages."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from mtp_lint import __version__
from mtp_lint.schema_validator import load_package, detect_artifact_type, detect_version, validate_schema
from mtp_lint.redaction_scanner import scan_all
from mtp_lint.completeness_scorer import score_package
from mtp_lint.policy_gate import check_policy
from mtp_lint.report import generate_report, format_text


@click.group()
@click.version_option(version=__version__, prog_name="mtp-lint")
def main():
    """MTP Lint — Validator, redaction checker, and linter for MTP packages."""
    pass


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text",
              help="Output format (text or json)")
@click.option("--strict", is_flag=True, default=False,
              help="Exit with code 1 on any warning (not just errors)")
@click.option("--client-dict", type=click.Path(exists=True), default=None,
              help="Path to client identifier dictionary (one term per line)")
@click.option("--skip-redaction", is_flag=True, default=False,
              help="Skip redaction scanning")
@click.option("--skip-completeness", is_flag=True, default=False,
              help="Skip completeness scoring")
def check(file: str, output_format: str, strict: bool, client_dict: str | None,
          skip_redaction: bool, skip_completeness: bool):
    """Run all checks on an MTP package or execution report.

    Validates schema, scans for data leakage, scores completeness,
    and checks the policy gate. Produces a machine-readable report.
    """
    # Load
    try:
        data = load_package(file)
    except Exception as e:
        click.echo(f"Error loading {file}: {e}", err=True)
        sys.exit(2)

    # Detect type and version
    try:
        artifact_type = detect_artifact_type(data)
        version = detect_version(data, artifact_type)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)

    # 1. Schema validation
    schema_errors = validate_schema(data, artifact_type, version)

    # 2. Redaction scan (packages only)
    redaction_results = None
    if artifact_type == "package" and not skip_redaction:
        client_dictionary = None
        if client_dict:
            client_dictionary = Path(client_dict).read_text().strip().splitlines()
        redaction_results = scan_all(data, client_dictionary)

    # 3. Completeness scoring (packages only)
    completeness_results = None
    if artifact_type == "package" and not skip_completeness:
        completeness_results = score_package(data)

    # 4. Policy gate (packages only, v0.2+)
    policy_results = None
    if artifact_type == "package" and version >= "0.2":
        policy_results = check_policy(data)

    # Assemble report
    report = generate_report(
        file_path=file,
        artifact_type=artifact_type,
        version=version,
        schema_errors=schema_errors,
        redaction_results=redaction_results,
        completeness_results=completeness_results,
        policy_results=policy_results,
    )

    # Output
    if output_format == "json":
        click.echo(json.dumps(report, indent=2, default=str))
    else:
        click.echo(format_text(report))

    # Exit code
    if report["overall_status"] == "fail":
        sys.exit(1)
    elif report["overall_status"] == "warn" and strict:
        sys.exit(1)
    else:
        sys.exit(0)


@main.command()
@click.argument("file", type=click.Path(exists=True))
def validate(file: str):
    """Validate an MTP file against its JSON Schema only."""
    try:
        data = load_package(file)
        artifact_type = detect_artifact_type(data)
        version = detect_version(data, artifact_type)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)

    errors = validate_schema(data, artifact_type, version)

    if not errors:
        click.echo(f"PASS — {artifact_type} v{version} is schema-valid.")
        sys.exit(0)
    else:
        click.echo(f"FAIL — {len(errors)} schema error(s):")
        for err in errors:
            click.echo(f"  [{err['path']}] {err['message']}")
        sys.exit(1)


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--client-dict", type=click.Path(exists=True), default=None,
              help="Path to client identifier dictionary (one term per line)")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def redact(file: str, client_dict: str | None, output_format: str):
    """Run redaction scan only — check for PII, secrets, and data leakage."""
    try:
        data = load_package(file)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)

    client_dictionary = None
    if client_dict:
        client_dictionary = Path(client_dict).read_text().strip().splitlines()

    results = scan_all(data, client_dictionary)

    if output_format == "json":
        click.echo(json.dumps(results, indent=2))
    else:
        if results["passed"]:
            click.echo(f"PASS — No data leakage detected.")
        else:
            click.echo(f"FAIL — {results['total_findings']} finding(s):")
            for f in results["findings"]:
                click.echo(f"  [{f['severity'].upper()}] {f['category']}/{f['pattern']} at {f['path']}")

    sys.exit(0 if results["passed"] else 1)


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def score(file: str, output_format: str):
    """Score completeness of an MTP package."""
    try:
        data = load_package(file)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)

    results = score_package(data)

    if output_format == "json":
        click.echo(json.dumps(results, indent=2))
    else:
        pct = int(results["composite_score"] * 100)
        click.echo(f"Completeness: {pct}% ({results['rating']})")
        click.echo(f"Checks: {results['passed_checks']}/{results['total_checks']} passed")
        click.echo("")
        click.echo("Area scores:")
        for area, scores in results["area_scores"].items():
            area_pct = int(scores["score"] * 100)
            click.echo(f"  {area:20s} {area_pct:3d}%  ({scores['passed']}/{scores['total']})")

        failed = [c for c in results["checks"] if not c["passed"]]
        if failed:
            click.echo(f"\nMissing ({len(failed)}):")
            for c in failed:
                click.echo(f"  - {c['area']}: {c['check']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
