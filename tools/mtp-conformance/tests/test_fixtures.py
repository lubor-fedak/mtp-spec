"""Tests for mtp-conformance fixture discovery and loading."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from mtp_conformance.fixtures import (
    VALID_LEVELS,
    FixtureManifest,
    discover_fixtures,
    load_fixture,
)


@pytest.fixture
def tmp_fixtures(tmp_path: Path) -> Path:
    """Create a minimal fixture tree for testing."""
    fixture_dir = tmp_path / "l1-test" / "case-a"
    fixture_dir.mkdir(parents=True)
    manifest = {
        "id": "l1-test-case-a",
        "level": "l1",
        "kind": "package_validation",
        "description": "Test fixture A.",
        "artifact": "package.yaml",
        "expect": {"valid": True},
    }
    (fixture_dir / "fixture.yaml").write_text(yaml.dump(manifest))
    (fixture_dir / "package.yaml").write_text("mtp_version: '0.2'\n")
    return tmp_path


class TestLoadFixture:
    def test_load_valid_fixture(self, tmp_fixtures: Path) -> None:
        manifest_path = tmp_fixtures / "l1-test" / "case-a" / "fixture.yaml"
        fixture = load_fixture(manifest_path)
        assert fixture.id == "l1-test-case-a"
        assert fixture.level == "l1"
        assert fixture.kind == "package_validation"
        assert fixture.description == "Test fixture A."

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "fixture.yaml"
        manifest_path.write_text(yaml.dump({"id": "test", "level": "l1"}))
        with pytest.raises(ValueError, match="missing required fields"):
            load_fixture(manifest_path)

    def test_non_mapping_manifest(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "fixture.yaml"
        manifest_path.write_text("- item1\n- item2\n")
        with pytest.raises(ValueError, match="must be a mapping"):
            load_fixture(manifest_path)

    def test_invalid_level_rejected(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "fixture.yaml"
        manifest = {
            "id": "bad-level",
            "level": "l4",
            "kind": "package_validation",
            "description": "Invalid level fixture.",
        }
        manifest_path.write_text(yaml.dump(manifest))
        with pytest.raises(ValueError, match="Invalid fixture level 'l4'"):
            load_fixture(manifest_path)

    @pytest.mark.parametrize("level", sorted(VALID_LEVELS))
    def test_valid_levels_accepted(self, tmp_path: Path, level: str) -> None:
        manifest_path = tmp_path / "fixture.yaml"
        manifest = {
            "id": f"test-{level}",
            "level": level,
            "kind": "package_validation",
            "description": f"Level {level} fixture.",
        }
        manifest_path.write_text(yaml.dump(manifest))
        fixture = load_fixture(manifest_path)
        assert fixture.level == level


class TestResolvePathMethod:
    def test_resolve_existing_key(self, tmp_fixtures: Path) -> None:
        manifest_path = tmp_fixtures / "l1-test" / "case-a" / "fixture.yaml"
        fixture = load_fixture(manifest_path)
        resolved = fixture.resolve_path("artifact")
        assert resolved is not None
        assert resolved.name == "package.yaml"

    def test_resolve_missing_key(self, tmp_fixtures: Path) -> None:
        manifest_path = tmp_fixtures / "l1-test" / "case-a" / "fixture.yaml"
        fixture = load_fixture(manifest_path)
        assert fixture.resolve_path("nonexistent") is None


class TestDiscoverFixtures:
    def test_discover_finds_fixtures(self, tmp_fixtures: Path) -> None:
        fixtures = discover_fixtures(tmp_fixtures)
        assert len(fixtures) == 1
        assert fixtures[0].id == "l1-test-case-a"

    def test_discover_empty_directory(self, tmp_path: Path) -> None:
        fixtures = discover_fixtures(tmp_path)
        assert fixtures == []

    def test_discover_multiple_fixtures_sorted(self, tmp_path: Path) -> None:
        for name, fixture_id in [("b-case", "l1-b"), ("a-case", "l1-a")]:
            fixture_dir = tmp_path / name
            fixture_dir.mkdir()
            manifest = {
                "id": fixture_id,
                "level": "l1",
                "kind": "package_validation",
                "description": f"Fixture {fixture_id}.",
            }
            (fixture_dir / "fixture.yaml").write_text(yaml.dump(manifest))

        fixtures = discover_fixtures(tmp_path)
        assert len(fixtures) == 2
        assert fixtures[0].id == "l1-a"
        assert fixtures[1].id == "l1-b"

    def test_discover_real_fixtures(self) -> None:
        """Smoke test: discover real fixtures from the repo."""
        fixtures = discover_fixtures()
        assert len(fixtures) >= 17
        levels = {f.level for f in fixtures}
        assert levels == {"l1", "l2", "l3"}
