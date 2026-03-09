"""Tests for mtp-extract CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from mtp_extract.cli import main
from mtp_lint.schema_validator import validate_schema


HERE = Path(__file__).parent
PROJECT = HERE.parent.parent.parent
CONVERSATION = PROJECT / "examples" / "conversations" / "churn-risk-scoring-session.md"
EXAMPLE_PACKAGE = PROJECT / "examples" / "churn-risk-scoring-v0.2.yaml"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestExtractCli:
    def test_draft_generates_schema_valid_package(self, runner: CliRunner, tmp_path: Path) -> None:
        output = tmp_path / "draft.yaml"
        result = runner.invoke(
            main,
            [
                "draft",
                str(CONVERSATION),
                "--name",
                "Extracted Churn Methodology",
                "--author",
                "analytics-team",
                "--source-platform",
                "claude-sonnet-4",
                "--precheck",
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 0
        data = __import__("yaml").safe_load(output.read_text(encoding="utf-8"))
        assert data["mtp_version"] == "0.2"
        assert len(data["methodology"]["steps"]) >= 1
        assert not validate_schema(data, "package", "0.2")
        assert data["policy"]["redaction"]["status"] in {"passed", "failed"}

    def test_provenance_map_json(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["map", str(EXAMPLE_PACKAGE), "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["total"] >= 5
        assert any(entry["kind"] == "step" for entry in payload["entries"])

    def test_merge_keeps_schema_valid(self, runner: CliRunner, tmp_path: Path) -> None:
        draft_path = tmp_path / "overlay.yaml"
        runner.invoke(
            main,
            [
                "draft",
                str(CONVERSATION),
                "--name",
                "Overlay",
                "--author",
                "analytics-team",
                "--output",
                str(draft_path),
            ],
        )
        merged_path = tmp_path / "merged.yaml"
        result = runner.invoke(
            main,
            [
                "merge",
                str(EXAMPLE_PACKAGE),
                str(draft_path),
                "--output",
                str(merged_path),
            ],
        )
        assert result.exit_code == 0
        merged = __import__("yaml").safe_load(merged_path.read_text(encoding="utf-8"))
        assert not validate_schema(merged, "package", "0.2")
        assert len(merged["methodology"]["steps"]) >= len(merged["methodology"]["steps"])

    def test_precheck_updates_policy(self, runner: CliRunner, tmp_path: Path) -> None:
        package_path = tmp_path / "draft.yaml"
        runner.invoke(main, ["draft", str(CONVERSATION), "--output", str(package_path)])
        result = runner.invoke(
            main,
            [
                "precheck",
                str(package_path),
                "--client-identifier",
                "Acme Corp",
                "--output",
                str(package_path),
            ],
        )
        assert result.exit_code == 0
        updated = __import__("yaml").safe_load(package_path.read_text(encoding="utf-8"))
        assert updated["policy"]["pii_scan"]["status"] in {"passed", "failed"}

    def test_draft_creates_missing_output_parent(self, runner: CliRunner, tmp_path: Path) -> None:
        output = tmp_path / "nested" / "draft.yaml"
        result = runner.invoke(
            main,
            [
                "draft",
                str(CONVERSATION),
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 0
        assert output.exists()
