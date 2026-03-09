"""Pytest configuration for mtp-benchmark."""

from __future__ import annotations

import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parent.parent / "src"
RUN_SRC_DIR = Path(__file__).resolve().parents[3] / "tools" / "mtp-run" / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(RUN_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(RUN_SRC_DIR))
