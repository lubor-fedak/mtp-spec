"""Tests for mtp-lint CLI commands."""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from mtp_lint.cli import main


_HERE = Path(__file__).parent          # tests/
_PROJECT = _HERE.parent.parent.parent  # mtp-spec/
EXAMPLES_DIR = str(_PROJECT / "examples")
PACKAGE_V02 = os.path.join(EXAMPLES_DIR, "churn-risk-scoring-v0.2.yaml")
EXEC_REPORT = os.path.join(EXAMPLES_DIR, "churn-risk-scoring-execution-report-v0.2.yaml")


@pytest.fixture
def runner():
    return CliRunner()


class TestValidateCommand:
    def test_valid_package(self, runner):
        result = runner.invoke(main, ["validate", PACKAGE_V02])
        assert result.exit_code == 0

    def test_valid_execution_report(self, runner):
        result = runner.invoke(main, ["validate", EXEC_REPORT])
        assert result.exit_code == 0


class TestRedactCommand:
    def test_clean_package(self, runner):
        result = runner.invoke(main, ["redact", PACKAGE_V02])
        assert result.exit_code == 0

    def test_json_output(self, runner):
        result = runner.invoke(main, ["redact", PACKAGE_V02, "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)


class TestScoreCommand:
    def test_score_package(self, runner):
        result = runner.invoke(main, ["score", PACKAGE_V02])
        assert result.exit_code == 0

    def test_score_rejects_exec_report(self, runner):
        result = runner.invoke(main, ["score", EXEC_REPORT])
        assert result.exit_code == 2


class TestCheckCommand:
    def test_check_package(self, runner):
        result = runner.invoke(main, ["check", PACKAGE_V02])
        # May pass or warn depending on policy state
        assert result.exit_code in (0, 1)

    def test_check_json_output(self, runner):
        result = runner.invoke(main, ["check", PACKAGE_V02, "--format", "json"])
        assert result.exit_code in (0, 1)
        data = json.loads(result.output)
        assert "overall_status" in data
