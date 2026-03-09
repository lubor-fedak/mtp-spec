"""Tests for mtp-run CLI commands."""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from mtp_run.cli import main


_HERE = Path(__file__).parent          # tests/
_PROJECT = _HERE.parent.parent.parent  # mtp-spec/
EXAMPLES_DIR = str(_PROJECT / "examples")
PACKAGE_FILE = os.path.join(EXAMPLES_DIR, "churn-risk-scoring-v0.2.yaml")
DATA_FILE = os.path.join(EXAMPLES_DIR, "test-data-churn.csv")
MOCK_REPORT_FILE = os.path.join(EXAMPLES_DIR, "churn-risk-scoring-mock-execution-report-v0.2.yaml")
REAL_REPORT_FILE = os.path.join(EXAMPLES_DIR, "churn-risk-scoring-execution-report-v0.2.yaml")


@pytest.fixture
def runner():
    return CliRunner()


class TestExecCommand:
    def test_exec_mock_success(self, runner):
        result = runner.invoke(main, [
            "exec", PACKAGE_FILE, "--data", DATA_FILE, "--adapter", "mock", "-q",
        ])
        assert result.exit_code == 0

    def test_exec_mock_yaml_output(self, runner):
        result = runner.invoke(main, [
            "exec", PACKAGE_FILE, "--data", DATA_FILE, "--adapter", "mock",
            "-q", "--format", "yaml",
        ])
        assert result.exit_code == 0
        assert "execution_report" in result.output

    def test_exec_mock_json_output(self, runner):
        result = runner.invoke(main, [
            "exec", PACKAGE_FILE, "--data", DATA_FILE, "--adapter", "mock",
            "-q", "--format", "json",
        ])
        assert result.exit_code == 0
        report = json.loads(result.output)
        assert "execution_report" in report

    def test_exec_missing_file(self, runner):
        result = runner.invoke(main, ["exec", "nonexistent.yaml"])
        assert result.exit_code != 0


class TestAdaptersCommand:
    def test_adapters_list(self, runner):
        result = runner.invoke(main, ["adapters"])
        assert result.exit_code == 0
        assert "mock" in result.output


class TestScoreCommand:
    def test_score_text(self, runner):
        result = runner.invoke(main, ["score", MOCK_REPORT_FILE])
        assert result.exit_code == 0
        assert "Composite" in result.output
        assert "Components" in result.output

    def test_score_json(self, runner):
        result = runner.invoke(main, ["score", MOCK_REPORT_FILE, "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "composite" in data
        assert "components" in data

    def test_score_invalid_file(self, runner):
        result = runner.invoke(main, ["score", PACKAGE_FILE])
        assert result.exit_code == 2


class TestDriftCommand:
    def test_drift_text(self, runner):
        result = runner.invoke(main, ["drift", MOCK_REPORT_FILE, REAL_REPORT_FILE])
        assert result.exit_code == 0
        assert "Drift Comparison" in result.output

    def test_drift_json(self, runner):
        result = runner.invoke(main, [
            "drift", MOCK_REPORT_FILE, REAL_REPORT_FILE, "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "comparison_drift" in data
        assert "state_agreement" in data
