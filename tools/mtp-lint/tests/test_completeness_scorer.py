"""Tests for completeness scorer."""

import os
from pathlib import Path

from mtp_lint.completeness_scorer import score_package
from mtp_lint.schema_validator import load_package


_HERE = Path(__file__).parent          # tests/
_PROJECT = _HERE.parent.parent.parent  # mtp-spec/
EXAMPLES_DIR = str(_PROJECT / "examples")
PACKAGE_V02 = os.path.join(EXAMPLES_DIR, "churn-risk-scoring-v0.2.yaml")


class TestScorePackage:
    def test_golden_package_scores_high(self):
        data = load_package(PACKAGE_V02)
        result = score_package(data)
        assert result["composite_score"] >= 0.7
        assert result["rating"] in ("excellent", "good")

    def test_minimal_package_scores_low(self):
        data = {
            "mtp_version": "0.2",
            "package": {"id": "test", "version": "1.0.0"},
            "intent": {"goal": "Do something"},
            "methodology": {"approach": "Do it", "steps": [{"step": 1, "name": "S1", "action": "Act"}]},
        }
        result = score_package(data)
        assert result["composite_score"] < 0.7
        assert result["rating"] in ("fair", "poor")

    def test_result_structure(self):
        data = load_package(PACKAGE_V02)
        result = score_package(data)
        assert "composite_score" in result
        assert "rating" in result
        assert "area_scores" in result
        assert isinstance(result["area_scores"], dict)

    def test_empty_package(self):
        data = {"mtp_version": "0.2"}
        result = score_package(data)
        assert result["composite_score"] >= 0
        assert result["rating"] is not None
