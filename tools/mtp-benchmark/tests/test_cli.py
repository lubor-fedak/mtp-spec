"""Tests for mtp-benchmark CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from mtp_benchmark.cli import main


HERE = Path(__file__).parent
PROJECT = HERE.parent.parent.parent
SUITE_FILE = PROJECT / "examples" / "benchmarks" / "churn-risk-benchmark-suite-v0.7.yaml"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestBenchmarkCli:
    def test_validate_suite(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["validate", str(SUITE_FILE), "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["artifact_type"] == "benchmark_suite"
        assert payload["valid"] is True

    def test_run_suite_with_mock(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(
            main,
            [
                "run",
                str(SUITE_FILE),
                "--output-dir",
                str(tmp_path),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output.split("\nBenchmark result written", 1)[0])
        assert payload["benchmark_result"]["summary"]["suite_passed"] is True
        assert payload["benchmark_result"]["summary"]["passed"] == 1
        assert payload["benchmark_result"]["summary"]["skipped"] == 2
        assert (tmp_path / "churn-risk-benchmark-result-v0.7.yaml").exists()

    def test_certify_mock_adapter(self, runner: CliRunner, tmp_path: Path) -> None:
        run_result = runner.invoke(
            main,
            [
                "run",
                str(SUITE_FILE),
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert run_result.exit_code == 0
        result_file = tmp_path / "churn-risk-benchmark-result-v0.7.yaml"
        certify_result = runner.invoke(
            main,
            [
                "certify",
                str(result_file),
                "--adapter",
                "mock",
                "--output",
                str(tmp_path / "mock.cert.yaml"),
            ],
        )
        assert certify_result.exit_code == 0
        certification = __import__("yaml").safe_load((tmp_path / "mock.cert.yaml").read_text(encoding="utf-8"))
        assert certification["adapter_certification"]["status"] == "certified"

    def test_certify_json_creates_missing_output_parent(self, runner: CliRunner, tmp_path: Path) -> None:
        runner.invoke(
            main,
            [
                "run",
                str(SUITE_FILE),
                "--output-dir",
                str(tmp_path),
            ],
        )
        output = tmp_path / "nested" / "mock.cert.json"
        result = runner.invoke(
            main,
            [
                "certify",
                str(tmp_path / "churn-risk-benchmark-result-v0.7.yaml"),
                "--adapter",
                "mock",
                "--format",
                "json",
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 0
        assert output.exists()
