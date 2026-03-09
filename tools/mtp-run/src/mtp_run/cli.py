"""MTP Run CLI — execute MTP packages, compare execution reports."""

from __future__ import annotations

import json
import sys
import time

import click

from mtp_run import __version__
from mtp_run.adapters import get_adapter, list_adapter_statuses
from mtp_run.drift import compare_reports, compute_report_drift
from mtp_run.executor import execute_package
from mtp_run.io_utils import dump_yaml, load_artifact, validate_execution_report, validate_package
from mtp_run.report_builder import build_execution_report, mock_quality_checks


def _run_execution(
    package: dict,
    data: str,
    adapter_name: str,
    model: str | None,
    azure: bool,
    quiet: bool,
    baseline_ref: str | None = None,
    baseline_type: str | None = None,
    baseline_report: dict | None = None,
) -> dict:
    adapter = get_adapter(adapter_name, model=model, azure=azure)
    if not adapter.is_available():
        raise RuntimeError(f"Adapter '{adapter_name}' is not available. Check SDK installation and API keys.")

    step_count = len(package.get("methodology", {}).get("steps", []))

    def on_start(step_num: int, step_name: str) -> None:
        if not quiet:
            click.echo(f"  [{step_num}/{step_count}] {step_name}...", nl=False, err=True)

    def on_end(step_num: int, step_name: str, result) -> None:
        if not quiet:
            state = result.state.upper()
            colors = {
                "SUCCESS": "green", "PASS": "green",
                "PARTIAL": "yellow", "DEVIATION": "yellow",
                "FAILURE": "red", "ESCALATED": "red",
                "SKIPPED": "white",
            }
            click.echo(f" {click.style(state, fg=colors.get(state, 'white'))}", err=True)

    if not quiet:
        click.echo(f"MTP Run — executing with {adapter.platform_id()}", err=True)
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

    report = build_execution_report(
        package=package,
        raw_results=raw_results,
        duration_seconds=duration,
        executor_id=f"mtp-run v{__version__}",
        quality_checks=mock_quality_checks(package) if adapter_name == "mock" else [],
        baseline_ref=baseline_ref,
        baseline_type=baseline_type,
        baseline_report=baseline_report,
    )

    report_errors = validate_execution_report(report)
    if report_errors:
        errors = "\n".join(f"  - {error}" for error in report_errors)
        raise RuntimeError(f"Generated execution report is not schema-valid:\n{errors}")

    return report


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

    package_errors = validate_package(package)
    if package_errors:
        click.echo("Error: package is not schema-valid:", err=True)
        for error in package_errors:
            click.echo(f"  - {error}", err=True)
        sys.exit(1)

    # Load data
    if data_file is None:
        data = ""
    else:
        try:
            with open(data_file, encoding="utf-8") as handle:
                data = handle.read()
        except Exception as e:
            click.echo(f"Error loading data: {e}", err=True)
            sys.exit(2)

    azure = adapter_name == "azure-openai"

    try:
        report = _run_execution(
            package=package,
            data=data,
            adapter_name=adapter_name,
            model=model,
            azure=azure,
            quiet=quiet,
        )
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)
    except Exception as e:
        click.echo(f"Error: execution failed: {e}", err=True)
        sys.exit(1)

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
        if fmt == "yaml":
            dump_yaml(output, report)
        else:
            with open(output, "w", encoding="utf-8") as handle:
                handle.write(formatted)
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
@click.argument("report_file", type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def score(report_file: str, fmt: str):
    """Compute weighted drift score for a single execution report (spec §8.3)."""
    try:
        report = load_artifact(report_file)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)

    if "execution_report" not in report:
        click.echo("Error: file must be an MTP execution report.", err=True)
        sys.exit(2)

    errors = validate_execution_report(report)
    if errors:
        click.echo("Error: report is not schema-valid:", err=True)
        for error in errors:
            click.echo(f"  - {error}", err=True)
        sys.exit(1)

    drift_result = compute_report_drift(report)

    if fmt == "json":
        click.echo(json.dumps(drift_result, indent=2))
    else:
        click.echo("Drift Score (self)")
        click.echo(f"{'=' * 50}")
        click.echo(f"Report:    {report_file}")
        er = report["execution_report"]
        click.echo(f"Platform:  {er.get('target_platform', 'unknown')}")
        click.echo(f"Status:    {er.get('overall_status', 'unknown')}")
        click.echo(f"Composite: {drift_result['composite']:.4f}")
        click.echo("")
        click.echo("Components:")
        for name, value in drift_result["components"].items():
            weight = drift_result["weights_used"].get(name)
            if value is None:
                click.echo(f"  {name:25s} —  (excluded, no data)")
            else:
                w_str = f"  weight {weight:.4f}" if weight is not None else ""
                click.echo(f"  {name:25s} {value:.4f}{w_str}")

    sys.exit(0)


@main.command()
def adapters():
    """List available adapters and their status."""
    statuses = list_adapter_statuses()
    click.echo("Available adapters:")
    click.echo("")
    for item in statuses:
        color = {
            "ready": "green",
            "not_configured": "yellow",
            "missing_dependency": "red",
        }.get(item.status, "white")
        status = click.style(item.status.upper(), fg=color)
        label = item.name if item.variant == "default" else f"{item.name} ({item.variant})"
        click.echo(f"  {label:20s} {status:18s} {item.notes}")


@main.command()
@click.argument("package_file", type=click.Path(exists=True))
@click.option("--data", "data_file", type=click.Path(exists=True), required=True,
              help="Path to data file used for both runs")
@click.option("--real-adapter", type=click.Choice(["anthropic", "openai"]), default=None,
              help="Real adapter to use. Default: first configured real adapter")
@click.option("--real-model", default=None, help="Model override for the real adapter")
@click.option("--azure", is_flag=True, default=False, help="Use Azure OpenAI for `--real-adapter openai`")
@click.option("--output-dir", type=click.Path(file_okay=False), required=True,
              help="Directory where mock/real reports and comparison JSON will be written")
@click.option("--strict", is_flag=True, default=False,
              help="Fail if no real adapter is configured instead of skipping the real-adapter run")
def e2e(package_file: str, data_file: str, real_adapter: str | None, real_model: str | None,
        azure: bool, output_dir: str, strict: bool):
    """Run mock + real-adapter execution and compare the resulting reports."""
    try:
        package = load_artifact(package_file)
        with open(data_file, encoding="utf-8") as handle:
            data = handle.read()
    except Exception as e:
        click.echo(f"Error loading inputs: {e}", err=True)
        sys.exit(2)

    package_errors = validate_package(package)
    if package_errors:
        click.echo("Error: package is not schema-valid:", err=True)
        for error in package_errors:
            click.echo(f"  - {error}", err=True)
        sys.exit(1)

    import os

    os.makedirs(output_dir, exist_ok=True)

    mock_report = _run_execution(
        package=package,
        data=data,
        adapter_name="mock",
        model=None,
        azure=False,
        quiet=True,
    )
    mock_path = f"{output_dir.rstrip('/')}/mock-report.yaml"
    dump_yaml(mock_path, mock_report)

    statuses = list_adapter_statuses()
    ready_real = [
        status for status in statuses
        if status.name in {"anthropic", "openai"} and status.status == "ready"
    ]

    selected_adapter = real_adapter
    if selected_adapter is None:
        if azure and any(s.name == "openai" and s.variant == "azure" and s.status == "ready" for s in statuses):
            selected_adapter = "openai"
        elif ready_real:
            selected_adapter = ready_real[0].name

    if selected_adapter is None:
        click.echo(f"Mock report written to {mock_path}")
        message = "No real adapter is configured. Skipping real-adapter e2e run."
        if strict:
            click.echo(f"Error: {message}", err=True)
            sys.exit(2)
        click.echo(f"SKIP — {message}")
        sys.exit(0)

    if selected_adapter == "anthropic":
        anthropic_ready = any(s.name == "anthropic" and s.status == "ready" for s in statuses)
        if not anthropic_ready:
            click.echo(f"Mock report written to {mock_path}")
            message = "Anthropic adapter is not configured."
            if strict:
                click.echo(f"Error: {message}", err=True)
                sys.exit(2)
            click.echo(f"SKIP — {message}")
            sys.exit(0)

    if selected_adapter == "openai":
        variant = "azure" if azure else "default"
        openai_ready = any(
            s.name == "openai" and s.variant == variant and s.status == "ready"
            for s in statuses
        )
        if not openai_ready:
            click.echo(f"Mock report written to {mock_path}")
            message = f"OpenAI adapter ({variant}) is not configured."
            if strict:
                click.echo(f"Error: {message}", err=True)
                sys.exit(2)
            click.echo(f"SKIP — {message}")
            sys.exit(0)

    try:
        real_report = _run_execution(
            package=package,
            data=data,
            adapter_name=selected_adapter,
            model=real_model,
            azure=azure,
            quiet=True,
            baseline_ref=mock_path,
            baseline_type="reference_run",
            baseline_report=mock_report,
        )
    except Exception as e:
        click.echo(f"Error: real-adapter execution failed: {e}", err=True)
        sys.exit(1)

    real_suffix = "openai-azure" if selected_adapter == "openai" and azure else selected_adapter
    real_path = f"{output_dir.rstrip('/')}/{real_suffix}-report.yaml"
    dump_yaml(real_path, real_report)

    comparison = compare_reports(mock_report, real_report)
    comparison_path = f"{output_dir.rstrip('/')}/comparison.json"
    with open(comparison_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(comparison, indent=2))

    click.echo(f"Mock report:  {mock_path}")
    click.echo(f"Real report:  {real_path}")
    click.echo(f"Comparison:   {comparison_path}")
    click.echo(f"Cross-report drift: {comparison['comparison_drift']['composite']:.4f}")
    click.echo(f"Step agreement: {int(comparison['state_agreement'] * 100)}%")


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

    errors1 = validate_execution_report(r1)
    errors2 = validate_execution_report(r2)
    if errors1 or errors2:
        click.echo("Error: both inputs must be schema-valid execution reports.", err=True)
        for label, errors in (("report1", errors1), ("report2", errors2)):
            for error in errors:
                click.echo(f"  - {label}: {error}", err=True)
        sys.exit(1)

    comparison = compare_reports(r1, r2)

    if fmt == "json":
        click.echo(json.dumps(comparison, indent=2))
    else:
        click.echo("Drift Comparison")
        click.echo(f"{'=' * 50}")
        click.echo(f"Baseline:  {report1} ({comparison['baseline']['target_platform']})")
        click.echo(f"Candidate: {report2} ({comparison['candidate']['target_platform']})")
        click.echo("")
        click.echo(
            f"Baseline self-score:  {comparison['baseline']['drift_score']['composite']:.4f} "
            f"[{comparison['baseline']['overall_status']}]"
        )
        click.echo(
            f"Candidate self-score: {comparison['candidate']['drift_score']['composite']:.4f} "
            f"[{comparison['candidate']['overall_status']}]"
        )
        click.echo(
            f"Cross-report drift:   {comparison['comparison_drift']['composite']:.4f}"
        )
        click.echo(
            f"Step agreement:       {int(comparison['state_agreement'] * 100)}% "
            f"({comparison['matching_steps']}/{comparison['total_steps']})"
        )
        if comparison["differences"]:
            click.echo("")
            click.echo("Differences:")
            for diff in comparison["differences"]:
                click.echo(
                    f"  - step {diff['step']}: "
                    f"{diff['baseline_state']} != {diff['candidate_state']}"
                )

    sys.exit(0)


if __name__ == "__main__":
    main()
