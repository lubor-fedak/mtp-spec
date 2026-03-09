"""CLI for mtp-benchmark."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml

from mtp_benchmark import __version__
from mtp_benchmark.artifacts import detect_artifact_type, dump_yaml, load_artifact, validate_artifact
from mtp_benchmark.runner import create_certification, run_suite, write_result_bundle


@click.group()
@click.version_option(version=__version__, prog_name="mtp-benchmark")
def main() -> None:
    """MTP Benchmark — benchmark suites and adapter certifications."""
    pass


@main.command()
@click.argument("artifact_file", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def validate(artifact_file: Path, output_format: str) -> None:
    """Validate a benchmark suite, result, or certification artifact."""
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
@click.argument("suite_file", type=click.Path(exists=True, path_type=Path))
@click.option("--output-dir", type=click.Path(path_type=Path), required=True)
@click.option("--strict", is_flag=True, default=False, help="Fail the suite when an optional adapter is unavailable.")
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml")
def run(suite_file: Path, output_dir: Path, strict: bool, output_format: str) -> None:
    """Run a benchmark suite and emit a result artifact."""
    try:
        suite = load_artifact(suite_file)
        result = run_suite(suite=suite, suite_path=suite_file, output_dir=output_dir, strict=strict)
        result_path = write_result_bundle(result, output_dir)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if output_format == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(yaml.safe_dump(result, sort_keys=False, allow_unicode=False))
    click.echo(f"Benchmark result written to {result_path}", err=True)
    sys.exit(0 if result["benchmark_result"]["summary"]["suite_passed"] else 1)


@main.command()
@click.argument("result_file", type=click.Path(exists=True, path_type=Path))
@click.option("--adapter", "adapter_name", required=True)
@click.option("--variant", default="default", show_default=True)
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None)
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml")
def certify(result_file: Path, adapter_name: str, variant: str, output: Path | None, output_format: str) -> None:
    """Generate an adapter certification artifact from a benchmark result."""
    try:
        result = load_artifact(result_file)
        certification = create_certification(
            benchmark_result=result,
            benchmark_result_ref=str(result_file),
            adapter_name=adapter_name,
            variant=variant,
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    output_path = output or result_file.with_name(f"{adapter_name}-{variant}.certification.v0.7.yaml")
    if output_format == "json":
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(certification, indent=2), encoding="utf-8")
        click.echo(json.dumps(certification, indent=2))
    else:
        dump_yaml(output_path, certification)
        click.echo(yaml.safe_dump(certification, sort_keys=False, allow_unicode=False))
    click.echo(f"Certification written to {output_path}", err=True)
    sys.exit(0 if certification["adapter_certification"]["status"] == "certified" else 1)


if __name__ == "__main__":
    main()
