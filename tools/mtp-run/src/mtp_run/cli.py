"""MTP Run CLI — execute MTP packages against data via LLM adapters."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import click
import yaml

from mtp_run import __version__
from mtp_run.executor import execute_package
from mtp_run.report_builder import build_execution_report, format_report_yaml, format_report_json


def _load_yaml(path: str) -> dict:
    p = Path(path)
    with open(p) as f:
        if p.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)
        else:
            return json.load(f)


def _get_adapter(name: str, model: str | None, azure: bool):
    """Instantiate the requested adapter."""
    if name == "mock":
        from mtp_run.adapters.mock import MockAdapter
        return MockAdapter(seed=42)

    if name == "anthropic":
        from mtp_run.adapters.anthropic import AnthropicAdapter
        return AnthropicAdapter(model=model or "claude-sonnet-4-20250514")

    if name == "openai":
        from mtp_run.adapters.openai import OpenAIAdapter
        return OpenAIAdapter(model=model or "gpt-4o", azure=azure)

    raise click.BadParameter(f"Unknown adapter: {name}. Use: mock, anthropic, openai")


@click.group()
@click.version_option(version=__version__, prog_name="mtp-run")
def main():
    """MTP Run — Reference runtime for executing MTP packages."""
    pass


@main.command(name="exec")
@click.argument("package_file", type=click.Path(exists=True))
@click.option("--data", "data_file", type=click.Path(exists=True), required=True,
              help="Path to data file (CSV, JSON, text, etc.)")
@click.option("--adapter", "adapter_name", type=click.Choice(["mock", "anthropic", "openai"]),
              default="mock", help="LLM adapter to use")
@click.option("--model", default=None, help="Model name override (e.g., claude-opus-4-20250514, gpt-4o)")
@click.option("--azure", is_flag=True, default=False, help="Use Azure OpenAI endpoint")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Write execution report to file (default: stdout)")
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml",
              help="Output format")
@click.option("--baseline", type=click.Path(exists=True), default=None,
              help="Baseline execution report for drift comparison")
@click.option("--quiet", "-q", is_flag=True, default=False,
              help="Suppress progress output")
def exec_cmd(package_file: str, data_file: str, adapter_name: str, model: str | None,
             azure: bool, output: str | None, output_format: str, baseline: str | None,
             quiet: bool):
    """Execute an MTP package against data.

    Runs each methodology step through the selected LLM adapter,
    respects execution semantics, and produces a standardized report.

    Examples:

        mtp-run exec package.yaml --data input.csv --adapter mock

        mtp-run exec package.yaml --data input.json --adapter anthropic --model claude-sonnet-4-20250514

        mtp-run exec package.yaml --data input.csv --adapter openai --azure --model gpt-4o
    """
    # Load package
    try:
        package = _load_yaml(package_file)
    except Exception as e:
        click.echo(f"Error loading package: {e}", err=True)
        sys.exit(2)

    if "mtp_version" not in package:
        click.echo("Error: File does not appear to be an MTP package (no mtp_version).", err=True)
        sys.exit(2)

    # Load data
    try:
        data = Path(data_file).read_text(encoding="utf-8")
    except Exception as e:
        click.echo(f"Error loading data: {e}", err=True)
        sys.exit(2)

    # Get adapter
    try:
        adapter = _get_adapter(adapter_name, model, azure)
    except Exception as e:
        click.echo(f"Error initializing adapter: {e}", err=True)
        sys.exit(2)

    if not adapter.is_available():
        click.echo(f"Error: Adapter '{adapter_name}' is not available. Check API keys.", err=True)
        sys.exit(2)

    # Progress callbacks
    step_count = len(package.get("methodology", {}).get("steps", []))

    def on_start(step_num, step_name):
        if not quiet:
            click.echo(f"  [{step_num}/{step_count}] {step_name}...", nl=False, err=True)

    def on_end(step_num, step_name, result):
        if not quiet:
            state = result.state.upper()
            colors = {
                "SUCCESS": "green", "PASS": "green",
                "PARTIAL": "yellow", "DEVIATION": "yellow",
                "FAILURE": "red", "ESCALATED": "red",
                "SKIPPED": "white",
            }
            click.echo(f" {click.style(state, fg=colors.get(state, 'white'))}", err=True)

    # Execute
    if not quiet:
        click.echo(f"MTP Run — executing {package_file}", err=True)
        click.echo(f"  Adapter: {adapter.platform_id()}", err=True)
        click.echo(f"  Steps: {step_count}", err=True)
        click.echo("", err=True)

    t0 = time.time()
    raw_results = execute_package(
        package=package,
        data=data,
        adapter=adapter,
        on_step_start=on_start,
        on_step_end=on_end,
    )
    duration = time.time() - t0

    # Load baseline if provided
    baseline_ref = None
    baseline_type = None
    if baseline:
        baseline_ref = baseline
        baseline_type = "reference_run"

    # Build report
    report = build_execution_report(
        package=package,
        raw_results=raw_results,
        duration_seconds=duration,
        executor_id=f"mtp-run v{__version__}",
        baseline_ref=baseline_ref,
        baseline_type=baseline_type,
    )

    # Format output
    if output_format == "yaml":
        formatted = format_report_yaml(report)
    else:
        formatted = format_report_json(report)

    # Write
    if output:
        Path(output).write_text(formatted)
        if not quiet:
            click.echo(f"\nReport written to {output}", err=True)
    else:
        click.echo(formatted)

    # Summary
    if not quiet:
        er = report["execution_report"]
        click.echo("", err=True)
        click.echo(f"  Overall: {er['overall_status'].upper()}", err=True)
        click.echo(f"  Confidence: {er['overall_confidence']}", err=True)
        drift = er.get("drift_score", {})
        if drift.get("composite") is not None:
            click.echo(f"  Drift score: {drift['composite']}", err=True)
        click.echo(f"  Duration: {er['duration_seconds']}s", err=True)

    # Exit code
    status = report["execution_report"]["overall_status"]
    if status in ("failure", "escalated"):
        sys.exit(1)
    sys.exit(0)


@main.command()
def adapters():
    """List available adapters and their status."""
    adapters_info = [
        ("mock", "Mock adapter (deterministic, no API key needed)", True),
    ]

    # Check anthropic
    try:
        from mtp_run.adapters.anthropic import AnthropicAdapter
        a = AnthropicAdapter()
        adapters_info.append(("anthropic", f"Anthropic Claude API", a.is_available()))
    except ImportError:
        adapters_info.append(("anthropic", "Anthropic Claude API (SDK not installed: pip install mtp-run[anthropic])", False))

    # Check openai
    try:
        from mtp_run.adapters.openai import OpenAIAdapter
        a_oai = OpenAIAdapter()
        a_azure = OpenAIAdapter(azure=True)
        adapters_info.append(("openai", "OpenAI API", a_oai.is_available()))
        adapters_info.append(("openai --azure", "Azure OpenAI API", a_azure.is_available()))
    except ImportError:
        adapters_info.append(("openai", "OpenAI API (SDK not installed: pip install mtp-run[openai])", False))

    click.echo("Available adapters:")
    click.echo("")
    for name, desc, available in adapters_info:
        status = click.style("READY", fg="green") if available else click.style("NOT AVAILABLE", fg="red")
        click.echo(f"  {name:20s} {status}  {desc}")


@main.command()
@click.argument("report1", type=click.Path(exists=True))
@click.argument("report2", type=click.Path(exists=True))
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def drift(report1: str, report2: str, output_format: str):
    """Compare two execution reports and compute drift.

    Useful for measuring platform-to-platform or temporal drift.
    """
    try:
        r1 = _load_yaml(report1)
        r2 = _load_yaml(report2)
    except Exception as e:
        click.echo(f"Error loading reports: {e}", err=True)
        sys.exit(2)

    er1 = r1.get("execution_report", {})
    er2 = r2.get("execution_report", {})

    if not er1 or not er2:
        click.echo("Error: Both files must be MTP execution reports.", err=True)
        sys.exit(2)

    # Compare step states
    steps1 = {s["step"]: s for s in er1.get("steps", [])}
    steps2 = {s["step"]: s for s in er2.get("steps", [])}

    all_steps = sorted(set(steps1.keys()) | set(steps2.keys()))

    comparison = {
        "report1": report1,
        "report2": report2,
        "report1_platform": er1.get("target_platform", "unknown"),
        "report2_platform": er2.get("target_platform", "unknown"),
        "report1_status": er1.get("overall_status", "unknown"),
        "report2_status": er2.get("overall_status", "unknown"),
        "step_comparison": [],
        "matching_states": 0,
        "divergent_states": 0,
    }

    for step_num in all_steps:
        s1 = steps1.get(step_num, {})
        s2 = steps2.get(step_num, {})
        state1 = s1.get("state", "missing")
        state2 = s2.get("state", "missing")
        match = state1 == state2

        if match:
            comparison["matching_states"] += 1
        else:
            comparison["divergent_states"] += 1

        comparison["step_comparison"].append({
            "step": step_num,
            "report1_state": state1,
            "report2_state": state2,
            "match": match,
        })

    total = comparison["matching_states"] + comparison["divergent_states"]
    comparison["state_agreement"] = round(comparison["matching_states"] / total, 4) if total > 0 else 0.0

    if output_format == "json":
        click.echo(json.dumps(comparison, indent=2))
    else:
        click.echo(f"Drift Comparison")
        click.echo(f"{'=' * 50}")
        click.echo(f"Report 1: {report1} ({comparison['report1_platform']})")
        click.echo(f"Report 2: {report2} ({comparison['report2_platform']})")
        click.echo(f"")
        click.echo(f"Overall: {comparison['report1_status']} vs {comparison['report2_status']}")
        click.echo(f"State agreement: {int(comparison['state_agreement'] * 100)}% ({comparison['matching_states']}/{total})")
        click.echo(f"")

        for sc in comparison["step_comparison"]:
            icon = "✓" if sc["match"] else "✗"
            click.echo(f"  Step {sc['step']:2d}: {sc['report1_state']:12s} vs {sc['report2_state']:12s} {icon}")

    sys.exit(0)


if __name__ == "__main__":
    main()
