"""Tests for schema validation."""

import os
from pathlib import Path

import pytest

from mtp_lint.schema_validator import (
    detect_artifact_type,
    detect_version,
    load_package,
    validate_schema,
    version_at_least,
)


_HERE = Path(__file__).parent          # tests/
_PROJECT = _HERE.parent.parent.parent  # mtp-spec/
EXAMPLES_DIR = str(_PROJECT / "examples")
PACKAGE_V02 = os.path.join(EXAMPLES_DIR, "churn-risk-scoring-v0.2.yaml")
PACKAGE_V01 = os.path.join(EXAMPLES_DIR, "valuation-report-extraction.yaml")
EXEC_REPORT = os.path.join(EXAMPLES_DIR, "churn-risk-scoring-execution-report-v0.2.yaml")


class TestDetectArtifactType:
    def test_package_detected(self):
        data = {"mtp_version": "0.2", "intent": {}}
        assert detect_artifact_type(data) == "package"

    def test_execution_report_detected(self):
        data = {"execution_report": {"steps": []}}
        assert detect_artifact_type(data) == "execution-report"

    def test_unknown_raises(self):
        data = {"random": "data"}
        with pytest.raises(ValueError):
            detect_artifact_type(data)


class TestDetectVersion:
    def test_package_v02(self):
        data = {"mtp_version": "0.2"}
        assert detect_version(data, "package") == "0.2"

    def test_package_v01(self):
        data = {"mtp_version": "0.1"}
        assert detect_version(data, "package") == "0.1"

    def test_execution_report_v02(self):
        data = {"execution_report": {"mtp_spec_version": "0.2"}}
        assert detect_version(data, "execution-report") == "0.2"


class TestVersionAtLeast:
    def test_equal(self):
        assert version_at_least("0.2", "0.2") is True

    def test_greater(self):
        assert version_at_least("0.10", "0.2") is True

    def test_less(self):
        assert version_at_least("0.1", "0.2") is False

    def test_major_version(self):
        assert version_at_least("1.0", "0.9") is True


class TestValidateSchema:
    def test_valid_v02_package(self):
        data = load_package(PACKAGE_V02)
        errors = validate_schema(data, "package", "0.2")
        assert errors == []

    def test_valid_v01_package(self):
        data = load_package(PACKAGE_V01)
        errors = validate_schema(data, "package", "0.1")
        assert errors == []

    def test_valid_execution_report(self):
        data = load_package(EXEC_REPORT)
        errors = validate_schema(data, "execution-report", "0.2")
        assert errors == []

    def test_empty_package_has_errors(self):
        errors = validate_schema({"mtp_version": "0.2"}, "package", "0.2")
        assert len(errors) > 0
