"""Tests for mtp-conformance runner functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mtp_conformance.fixtures import discover_fixtures
from mtp_conformance.runner import (
    _normalize_for_hash,
    _summary_hash,
    run_conformance,
    run_fixture,
)


class TestRunConformance:
    def test_invalid_level_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported level"):
            run_conformance(level="l4")

    def test_l1_passes(self) -> None:
        summary = run_conformance(level="l1")
        assert summary["level"] == "l1"
        assert summary["failed"] == 0
        assert summary["total_fixtures"] >= 2

    def test_l2_passes(self) -> None:
        summary = run_conformance(level="l2")
        assert summary["level"] == "l2"
        assert summary["failed"] == 0
        assert summary["total_fixtures"] >= 8

    def test_summary_has_hash(self) -> None:
        summary = run_conformance(level="l1")
        assert summary["summary_hash"].startswith("sha256:")


class TestRunFixture:
    def test_individual_fixture_result(self) -> None:
        fixtures = discover_fixtures()
        l1_fixture = next(f for f in fixtures if f.level == "l1")
        result = run_fixture(l1_fixture)
        assert result.id == l1_fixture.id
        assert result.level == l1_fixture.level
        assert isinstance(result.passed, bool)
        assert result.duration_ms >= 0

    def test_unknown_kind_fails(self) -> None:
        from mtp_conformance.fixtures import FixtureManifest
        fake = FixtureManifest(
            id="fake",
            level="l1",
            kind="nonexistent_kind",
            description="Fake fixture",
            manifest_path=Path("/dev/null"),
            data={},
        )
        result = run_fixture(fake)
        assert not result.passed
        assert "Unknown fixture kind" in result.details.get("error", "")


class TestNormalization:
    def test_duration_ms_excluded_from_hash(self) -> None:
        data = {"level": "l1", "duration_ms": 123, "fixtures": []}
        normalized = _normalize_for_hash(data)
        assert "duration_ms" not in normalized

    def test_summary_hash_excluded_from_hash(self) -> None:
        data = {"level": "l1", "summary_hash": "sha256:abc", "fixtures": []}
        normalized = _normalize_for_hash(data)
        assert "summary_hash" not in normalized

    def test_hash_is_deterministic(self) -> None:
        summary = {"level": "l1", "total_fixtures": 1, "passed": 1, "failed": 0, "fixtures": []}
        h1 = _summary_hash(summary)
        h2 = _summary_hash(summary)
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_hash_differs_with_different_data(self) -> None:
        s1 = {"level": "l1", "total_fixtures": 1, "passed": 1, "failed": 0, "fixtures": []}
        s2 = {"level": "l2", "total_fixtures": 1, "passed": 1, "failed": 0, "fixtures": []}
        assert _summary_hash(s1) != _summary_hash(s2)
