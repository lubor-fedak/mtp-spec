"""Fixture discovery and loading for mtp-conformance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

VALID_LEVELS = {"l1", "l2", "l3"}


@dataclass(frozen=True)
class FixtureManifest:
    """Loaded fixture manifest."""

    id: str
    level: str
    kind: str
    description: str
    manifest_path: Path
    data: dict[str, Any]

    def resolve_path(self, key: str) -> Path | None:
        value = self.data.get(key)
        if value is None:
            return None
        return (self.manifest_path.parent / value).resolve()


def default_fixtures_root() -> Path:
    return Path(__file__).parent.parent.parent.parent.parent / "conformance" / "fixtures"


def discover_fixtures(fixtures_root: Path | None = None) -> list[FixtureManifest]:
    root = fixtures_root or default_fixtures_root()
    manifests = sorted(root.rglob("fixture.yaml"))
    fixtures = [load_fixture(manifest_path) for manifest_path in manifests]
    return sorted(fixtures, key=lambda item: item.id)


def load_fixture(manifest_path: str | Path) -> FixtureManifest:
    path = Path(manifest_path)
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Fixture manifest must be a mapping: {path}")

    required = ["id", "level", "kind", "description"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Fixture manifest missing required fields {missing}: {path}")

    level = str(data["level"])
    if level not in VALID_LEVELS:
        raise ValueError(
            f"Invalid fixture level '{level}' in {path}. "
            f"Must be one of: {', '.join(sorted(VALID_LEVELS))}"
        )

    return FixtureManifest(
        id=str(data["id"]),
        level=level,
        kind=str(data["kind"]),
        description=str(data["description"]),
        manifest_path=path.resolve(),
        data=data,
    )
