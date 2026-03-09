"""Tests for mtp-conformance CLI."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from mtp_conformance.cli import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestRunCommand:
    @pytest.mark.parametrize(
        ("level", "minimum_total"),
        [
            ("l1", 2),
            ("l2", 8),
            ("l3", 17),
            ("all", 17),
        ],
    )
    def test_run_levels_json(self, runner: CliRunner, level: str, minimum_total: int) -> None:
        result = runner.invoke(main, ["run", "--level", level, "--format", "json"])
        assert result.exit_code == 0

        payload = json.loads(result.output)
        assert payload["level"] == level
        assert payload["failed"] == 0
        assert payload["passed"] == payload["total_fixtures"]
        assert payload["total_fixtures"] >= minimum_total
        assert payload["summary_hash"].startswith("sha256:")

    def test_run_text_output(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["run", "--level", "l1"])
        assert result.exit_code == 0
        assert "PASS" in result.output
        assert "Summary hash:" in result.output

    def test_summary_hash_is_stable_across_runs(self, runner: CliRunner) -> None:
        first = runner.invoke(main, ["run", "--level", "l3", "--format", "json"])
        second = runner.invoke(main, ["run", "--level", "l3", "--format", "json"])

        assert first.exit_code == 0
        assert second.exit_code == 0

        first_payload = json.loads(first.output)
        second_payload = json.loads(second.output)
        assert first_payload["summary_hash"] == second_payload["summary_hash"]

    def test_invalid_level(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["run", "--level", "l4"])
        assert result.exit_code == 2
