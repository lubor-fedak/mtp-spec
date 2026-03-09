"""MTP Run CLI — execute MTP packages, compare execution reports."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from mtp_run import __version__
from mtp_run.adapters import get_adapter, list_adapters
from mtp_run.drift import compare_reports
from mtp_run.io_utils import load_artifact, dump_yaml, validate_package, validate_execution_report
from mtp_run.reporting import build_execution_report


@click.group()
@click.version_option(version=__version__, prog_name="mtp-run")
def main():
    """MTP Run — Reference runtime for executing MTP packages."""
    pass


@main.command(name="exec")
@click.argument("package_file", type=click.Path(exists=True))
@click.option("--data", "data_file", type=click.Path(exists=True), default=None,
              help="Path to data file (CSV, JSON, text). Optional for mock adapter.")
@click.option("--adapter", "adapter_name", default="mock",
              help="Adapter name: mock, anthropic, openai, azure-openai")
@click.option("--model", default=None,
              help="Model override (e.g. claude-opus-4-20250514, gpt-4o)")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Write execution report to file (default: stdout)")
@click.option("--format", "fmt", type=click.Choice(["yaml", "json"]), default="yaml")
@click.option("--quiet", "-q", is_flag=True, default=False)
def exec_cmd(package_file: str, data_file: str | None, adapter_name: str,
             model: str | None, output: str | None, fmt: str, quiet: bool):
    """Execute an MTP package through an LLM adapter.

    \b
    Examples:
      mtp-run exec package.yaml --adapter mock
      mtp-run exec package.yaml --data input.csv --adapter anthropic
      mtp-run exec package.yaml --data input.csv --adapter openai --model gpt-4o
    """
    # Load package
    try:
        package = load_artifact(package_file)
    except Exception as e:
        click.echo(f"Error loading package: {e}", err=True)
        sys.exit(2)

    if "mtp_version" not in package:
        click.echo("Error: not an MTP package (no mtp_version).", err=True)
        sys.exit(2)

    # Validate package
    errors = validate_package(package)
    if errors:
        click.echo(f"Package validation failed ({len(errors)} errors):", err=True)
        for e in errors[:5]:
            click.echo(f"  {e}", err=True)
        sys.exit(2)

    # Get adapter
    azure = adapter_name == "azure-openai"
    effective_name = "openai" if adapter_name == "azure-openai" else adapter_name
    try:
        adapter = get_adapter(effective_name, model=model, azure=azure)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)

    step_count = len(package.get("methodology", {}).get("steps", []))

    if not quiet:
        click.echo(f"MTP Run — {package_file}", err=True)
        click.echo(f"  Adapter:  {adapter.target_platform}", err=True)
        click.echo(f"  Steps:    {step_count}", err=True)
        click.echo("", err=True)

    # Execute
    raw_result = adapter.execute(package, __version__)

    # Build report
    report = build_execution_report(package, raw_result)

    # Validate generated report
    report_errors = validate_execution_report(report)
    if report_errors and not quiet:
        click.echo(f"Warning: generated report has {len(report_errors)} schema issues.", err=True)

    # Output
    if fmt == "json":
        formatted = json.dumps(report, indent=2, default=str)
    else:
        import yaml
        formatted = yaml.safe_dump(report, sort_keys=False, allow_unicode=True)

    if output:
        Path(output).write_text(formatted)
        if not quiet:
            click.echo(f"Report written to {output}", err=True)
    else:
        click.echo(formatted)

    # Summary
    if not quiet:
        er = report["execution_report"]
        click.echo("", err=True)
        click.echo(f"  Overall:    {er['overall_status'].upper()}", err=True)
        click.echo(f"  Confidence: {er['overall_confidence']}", err=True)
        drift = er.get("drift_score", {})
        if drift.get("composite") is not None:
            click.echo(f"  Drift:      {drift['composite']}", err=True)
        click.echo(f"  Duration:   {er['duration_seconds']}s", err=True)

    status = report["execution_report"]["overall_status"]
    sys.exit(1 if status in ("failure", "escalated") else 0)


@main.command()
def adapters():
    """List available adapters and their status."""
    click.echo("Available adapters:")
    click.echo("")
    for info in list_adapters():
        colors = {"ready": "green", "available": "yellow", "unavailable": "red", "planned": "white"}
        badge = click.style(info.status.upper(), fg=colors.get(info.status, "white"))
        click.echo(f"  {info.name:16s} {badge:28s} {info.notes}")


@main.command()
@click.argument("report1", type=click.Path(exists=True))
@click.argument("report2", type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def drift(report1: str, report2: str, fmt: str):
    """Compare two execution reports — state agreement and drift."""
    try:
        r1 = load_artifact(report1)
        r2 = load_artifact(report2)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)

    if "execution_report" not in r1 or "execution_report" not in r2:
        click.echo("Error: Both files must be MTP execution reports.", err=True)
        sys.exit(2)

    comparison = compare_reports(r1, r2)

    if fmt == "json":
        click.echo(json.dumps(comparison, indent=2))
    else:
        click.echo("Drift Comparison")
        click.echo("=" * 55)
        click.echo(f"  Left:  {report1} ({comparison['left_platform']})")
        click.echo(f"  Right: {report2} ({comparison['right_platform']})")
        click.echo("")
        click.echo(f"  Status: {comparison['left_status']} vs {comparison['right_status']}")
        pct = int(comparison["step_state_agreement"] * 100)
        click.echo(f"  State agreement: {pct}% ({comparison['matching_steps']}/{comparison['total_steps']})")

        if "left_drift_score" in comparison:
            click.echo(f"  Left drift score:  {comparison['left_drift_score']}")
        if "right_drift_score" in comparison:
            click.echo(f"  Right drift score: {comparison['right_drift_score']}")

        click.echo("")
        for sc in comparison["step_comparison"]:
            icon = click.style("✓", fg="green") if sc["match"] else click.style("✗", fg="red")
            click.echo(f"  Step {sc['step']:2d}: {sc['left_state']:12s} vs {sc['right_state']:12s} {icon}")

    sys.exit(0)


if __name__ == "__main__":
    main()
