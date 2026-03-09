"""CLI for mtp-conformance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from mtp_conformance import __version__
from mtp_conformance.fixtures import default_fixtures_root
from mtp_conformance.runner import run_conformance


@click.group()
@click.version_option(version=__version__, prog_name="mtp-conformance")
def main():
    """Fixture-driven conformance runner for MTP."""
    pass


@main.command()
@click.option("--level", type=click.Choice(["l1", "l2", "l3", "all"]), required=True,
              help="Conformance level to run")
@click.option("--fixtures-root", type=click.Path(file_okay=False, path_type=Path),
              default=default_fixtures_root, show_default="repo conformance/fixtures",
              help="Fixture root directory")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text",
              help="Output format")
def run(level: str, fixtures_root: Path, output_format: str):
    """Run the conformance suite for the selected level."""
    try:
        summary = run_conformance(level=level, fixtures_root=fixtures_root)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    if output_format == "json":
        click.echo(json.dumps(summary, indent=2))
    else:
        status = "PASS" if summary["failed"] == 0 else "FAIL"
        click.echo(f"{status} — conformance {summary['level']}")
        click.echo(
            f"Fixtures: {summary['passed']}/{summary['total_fixtures']} passed "
            f"({summary['failed']} failed)"
        )
        click.echo(f"Summary hash: {summary['summary_hash']}")
        failed = [fixture for fixture in summary["fixtures"] if not fixture["passed"]]
        if failed:
            click.echo("")
            click.echo("Failures:")
            for fixture in failed:
                click.echo(f"  - {fixture['id']} ({fixture['kind']})")
                details = fixture["details"]
                if "error" in details:
                    click.echo(f"    {details['error']}")
                elif "mismatches" in details and details["mismatches"]:
                    for mismatch in details["mismatches"]:
                        click.echo(f"    {mismatch}")
                elif "component_mismatches" in details and details["component_mismatches"]:
                    for mismatch in details["component_mismatches"]:
                        click.echo(f"    {mismatch}")
                elif "missing" in details and details["missing"]:
                    click.echo(f"    Missing: {', '.join(details['missing'])}")

    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
