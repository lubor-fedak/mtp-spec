"""Pytest configuration for mtp-extract."""

from __future__ import annotations

import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parent.parent / "src"
LINT_SRC_DIR = Path(__file__).resolve().parents[3] / "tools" / "mtp-lint" / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(LINT_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(LINT_SRC_DIR))
