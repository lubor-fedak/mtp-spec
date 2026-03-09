"""Tests for execution report builder."""

from mtp_run.report_builder import build_execution_report, _derive_overall_status


class TestDeriveOverallStatus:
    def test_all_success(self):
        steps = [{"state": "success"}, {"state": "success"}]
        assert _derive_overall_status(steps, []) == "success"

    def test_escalated_takes_priority(self):
        steps = [{"state": "success"}, {"state": "escalated"}]
        assert _derive_overall_status(steps, []) == "escalated"

    def test_blocking_failure(self):
        steps = [{"state": "success"}, {"state": "failure", "failure_blocking": True}]
        assert _derive_overall_status(steps, []) == "failure"

    def test_non_blocking_failure_not_failure(self):
        steps = [{"state": "success"}, {"state": "failure", "failure_blocking": False}]
        assert _derive_overall_status(steps, []) != "failure"

    def test_blocking_quality_check_failure(self):
        steps = [{"state": "success"}]
        qc = [{"is_blocking": True, "result": "fail"}]
        assert _derive_overall_status(steps, qc) == "failure"

    def test_deviation(self):
        steps = [{"state": "success"}, {"state": "deviation"}]
        assert _derive_overall_status(steps, []) == "deviation"

    def test_partial(self):
        steps = [{"state": "success"}, {"state": "partial"}]
        assert _derive_overall_status(steps, []) == "partial"

    def test_skipped(self):
        steps = [{"state": "success"}, {"state": "skipped"}]
        assert _derive_overall_status(steps, []) == "partial"


class TestBuildExecutionReport:
    def test_report_structure(self):
        package = {
            "package": {"id": "test", "version": "1.0.0"},
            "mtp_version": "0.2",
        }
        raw_results = {
            "steps": [
                {"step": 1, "state": "success", "validation_result": "pass",
                 "duration_seconds": 0.1, "retries_attempted": 0, "notes": ""},
            ],
            "platform": "test-platform",
            "edge_cases_encountered": [],
            "novel_situations": [],
            "dead_ends_prevented": [],
        }
        report = build_execution_report(package, raw_results, 1.0)
        er = report["execution_report"]
        assert er["mtp_package_id"] == "test"
        assert er["mtp_spec_version"] == "0.2"
        assert er["overall_status"] == "success"
        assert er["overall_confidence"] == "high"
        assert "drift_score" in er
        assert "report_hash" in er
        assert er["report_hash"].startswith("sha256:")

    def test_confidence_low_on_failure(self):
        package = {"package": {"id": "t", "version": "1.0"}}
        raw_results = {
            "steps": [{"step": 1, "state": "failure", "validation_result": "fail",
                        "duration_seconds": 0, "retries_attempted": 0, "notes": "",
                        "failure_reason": "err", "failure_blocking": True}],
            "platform": "test",
            "edge_cases_encountered": [],
            "novel_situations": [],
            "dead_ends_prevented": [],
        }
        report = build_execution_report(package, raw_results, 0.5)
        assert report["execution_report"]["overall_confidence"] == "low"
