"""Tests for mtp-release CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from mtp_release.cli import main


HERE = Path(__file__).parent
PROJECT = HERE.parent.parent.parent
BENCHMARK_RESULT = PROJECT / "examples" / "benchmarks" / "churn-risk-benchmark-result-v0.7.yaml"
CERTIFICATION = PROJECT / "examples" / "benchmarks" / "mock-adapter-certification-v0.7.yaml"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestReleaseCli:
    def test_build_matrix(self, runner: CliRunner, tmp_path: Path) -> None:
        output = tmp_path / "matrix.yaml"
        result = runner.invoke(
            main,
            [
                "matrix",
                "--benchmark-result",
                str(BENCHMARK_RESULT),
                "--certification",
                str(CERTIFICATION),
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 0
        matrix = __import__("yaml").safe_load(output.read_text(encoding="utf-8"))
        assert matrix["provider_matrix"]["summary"]["certified"] == 1
        assert matrix["provider_matrix"]["summary"]["not_evaluated"] == 2

    def test_build_contract(self, runner: CliRunner, tmp_path: Path) -> None:
        matrix_file = tmp_path / "matrix.yaml"
        runner.invoke(
            main,
            [
                "matrix",
                "--benchmark-result",
                str(BENCHMARK_RESULT),
                "--certification",
                str(CERTIFICATION),
                "--output",
                str(matrix_file),
            ],
        )
        contract_file = tmp_path / "contract.yaml"
        result = runner.invoke(
            main,
            [
                "contract",
                "--release-version",
                "1.0.0",
                "--provider-matrix",
                str(matrix_file),
                "--conformance-level",
                "l3",
                "--architecture-ref",
                "docs/enterprise-reference-architecture-v1.0.md",
                "--output",
                str(contract_file),
            ],
        )
        assert result.exit_code == 0
        contract = __import__("yaml").safe_load(contract_file.read_text(encoding="utf-8"))
        assert contract["compatibility_contract"]["release"]["version"] == "1.0.0"

    def test_validate_json(self, runner: CliRunner, tmp_path: Path) -> None:
        matrix_file = tmp_path / "matrix.yaml"
        runner.invoke(
            main,
            [
                "matrix",
                "--benchmark-result",
                str(BENCHMARK_RESULT),
                "--certification",
                str(CERTIFICATION),
                "--output",
                str(matrix_file),
            ],
        )
        result = runner.invoke(main, ["validate", str(matrix_file), "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["valid"] is True
