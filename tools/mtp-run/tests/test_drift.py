"""Tests for drift scoring engine (spec §8.3)."""

import pytest

from mtp_run.drift import compute_report_drift, compare_reports, DEFAULT_WEIGHTS


def _make_report(steps, edge_cases=None, novel_situations=None, quality_checks=None):
    return {
        "execution_report": {
            "target_platform": "test",
            "overall_status": "success",
            "steps": steps,
            "edge_cases_encountered": edge_cases or [],
            "novel_situations": novel_situations or [],
            "dead_ends_prevented": [],
            "quality_checks": quality_checks or [],
        }
    }


class TestComputeReportDrift:
    def test_all_success_returns_perfect_score(self):
        report = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
            {"step": 2, "state": "success", "validation_result": "pass"},
            {"step": 3, "state": "success", "validation_result": "pass"},
        ])
        result = compute_report_drift(report)
        assert result["composite"] == 1.0
        assert result["components"]["step_fidelity"] == 1.0
        assert result["components"]["deviation_rate"] == 1.0

    def test_one_failure_reduces_fidelity(self):
        report = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
            {"step": 2, "state": "failure", "validation_result": "fail"},
        ])
        result = compute_report_drift(report)
        assert result["components"]["step_fidelity"] == 0.5
        assert result["composite"] < 1.0

    def test_deviation_affects_deviation_rate(self):
        report = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
            {"step": 2, "state": "deviation", "validation_result": "pass"},
        ])
        result = compute_report_drift(report)
        assert result["components"]["deviation_rate"] == 0.5
        assert result["components"]["step_fidelity"] == 0.5

    def test_validation_pass_rate(self):
        report = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
            {"step": 2, "state": "success", "validation_result": "fail"},
            {"step": 3, "state": "success", "validation_result": "pass"},
        ])
        result = compute_report_drift(report)
        assert result["components"]["validation_pass_rate"] == pytest.approx(2 / 3, abs=0.001)

    def test_novel_situation_rate(self):
        report = _make_report(
            steps=[
                {"step": 1, "state": "success", "validation_result": "pass"},
                {"step": 2, "state": "escalated", "validation_result": "not_applicable"},
            ],
            novel_situations=[{"description": "novel thing", "step": 2}],
        )
        result = compute_report_drift(report)
        assert result["components"]["novel_situation_rate"] == 0.5

    def test_edge_case_coverage(self):
        report = _make_report(
            steps=[{"step": 1, "state": "success", "validation_result": "pass"}],
            edge_cases=[
                {"scenario": "edge1", "matched_edge_case": "ec_1", "handling_applied": "handled"},
                {"scenario": "edge2", "matched_edge_case": "novel", "handling_applied": ""},
            ],
        )
        result = compute_report_drift(report)
        assert result["components"]["edge_case_coverage"] == 0.5

    def test_quality_checks_output_quality(self):
        report = _make_report(
            steps=[{"step": 1, "state": "success", "validation_result": "pass"}],
            quality_checks=[
                {"check": "qc1", "result": "pass", "is_blocking": False},
                {"check": "qc2", "result": "fail", "is_blocking": False},
            ],
        )
        result = compute_report_drift(report)
        assert result["components"]["output_quality"] == 0.5

    def test_missing_components_excluded_weights_redistributed(self):
        report = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
        ])
        result = compute_report_drift(report)
        # edge_case_coverage and output_quality should be None (no data)
        assert result["components"]["edge_case_coverage"] is None
        assert result["components"]["output_quality"] is None
        # weights should be redistributed among active components
        active_weights = result["weights_used"]
        assert sum(active_weights.values()) == pytest.approx(1.0, abs=0.01)

    def test_default_weights_sum_to_one(self):
        assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)

    def test_dead_end_avoidance_default_is_one(self):
        report = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
        ])
        result = compute_report_drift(report)
        assert result["components"]["dead_end_avoidance"] == 1.0

    def test_dead_end_avoidance_zero_when_repeated(self):
        report = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
        ])
        report["execution_report"]["drift_score"] = {
            "components": {"dead_end_avoidance": 0.0}
        }
        result = compute_report_drift(report)
        assert result["components"]["dead_end_avoidance"] == 0.0


class TestCompareReports:
    def test_identical_reports_perfect_agreement(self):
        report = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
            {"step": 2, "state": "success", "validation_result": "pass"},
        ])
        result = compare_reports(report, report)
        assert result["state_agreement"] == 1.0
        assert result["matching_steps"] == 2
        assert result["total_steps"] == 2
        assert result["differences"] == []
        assert result["comparison_drift"]["composite"] == 1.0

    def test_different_states_detected(self):
        r1 = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
            {"step": 2, "state": "success", "validation_result": "pass"},
        ])
        r2 = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
            {"step": 2, "state": "deviation", "validation_result": "pass"},
        ])
        result = compare_reports(r1, r2)
        assert result["state_agreement"] == 0.5
        assert result["matching_steps"] == 1
        assert len(result["differences"]) == 1
        assert result["differences"][0]["step"] == 2

    def test_cross_report_drift_lower_on_divergence(self):
        r1 = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
            {"step": 2, "state": "success", "validation_result": "pass"},
        ])
        r2 = _make_report([
            {"step": 1, "state": "success", "validation_result": "pass"},
            {"step": 2, "state": "failure", "validation_result": "fail"},
        ])
        result = compare_reports(r1, r2)
        assert result["comparison_drift"]["composite"] < 1.0
