"""Tests for the MTP execution engine."""

import pytest

from mtp_run.adapters.mock import MockAdapter
from mtp_run.executor import execute_package


def _minimal_package(steps):
    return {
        "mtp_version": "0.2",
        "package": {"id": "test-pkg", "version": "1.0.0"},
        "intent": {"goal": "Test goal"},
        "methodology": {
            "approach": "Test approach",
            "steps": steps,
        },
        "edge_cases": [],
        "dead_ends": [],
        "output": {},
    }


class TestExecutePackage:
    def test_all_steps_succeed(self):
        pkg = _minimal_package([
            {"step": 1, "name": "Step 1", "action": "Do A", "execution_semantics": {}},
            {"step": 2, "name": "Step 2", "action": "Do B", "execution_semantics": {}},
        ])
        result = execute_package(pkg, "test data", MockAdapter(seed=42))
        assert len(result["steps"]) == 2
        assert all(s["state"] == "success" for s in result["steps"])

    def test_force_fail_halts_pipeline(self):
        pkg = _minimal_package([
            {"step": 1, "name": "Fail", "action": "FORCE_FAIL here",
             "execution_semantics": {"on_failure": "halt"}},
            {"step": 2, "name": "After", "action": "Should be skipped",
             "execution_semantics": {}},
        ])
        result = execute_package(pkg, "test data", MockAdapter(seed=42))
        assert result["steps"][0]["state"] == "failure"
        assert result["steps"][1]["state"] == "skipped"

    def test_force_fail_skip_with_flag(self):
        pkg = _minimal_package([
            {"step": 1, "name": "Fail", "action": "FORCE_FAIL here",
             "execution_semantics": {"on_failure": "skip_with_flag"}},
            {"step": 2, "name": "After", "action": "Should run",
             "execution_semantics": {}},
        ])
        result = execute_package(pkg, "test data", MockAdapter(seed=42))
        assert result["steps"][0]["state"] == "failure"
        assert result["steps"][1]["state"] == "success"

    def test_force_deviate_flag_and_proceed(self):
        pkg = _minimal_package([
            {"step": 1, "name": "Deviate", "action": "FORCE_DEVIATE here",
             "execution_semantics": {"on_deviation": "flag_and_proceed"}},
            {"step": 2, "name": "After", "action": "Should run",
             "execution_semantics": {}},
        ])
        result = execute_package(pkg, "test data", MockAdapter(seed=42))
        assert result["steps"][0]["state"] == "deviation"
        assert result["steps"][1]["state"] == "success"

    def test_force_deviate_halt(self):
        pkg = _minimal_package([
            {"step": 1, "name": "Deviate", "action": "FORCE_DEVIATE here",
             "execution_semantics": {"on_deviation": "halt"}},
            {"step": 2, "name": "After", "action": "Should skip",
             "execution_semantics": {}},
        ])
        result = execute_package(pkg, "test data", MockAdapter(seed=42))
        assert result["steps"][0]["state"] == "deviation"
        assert result["steps"][1]["state"] == "skipped"

    def test_force_escalate(self):
        pkg = _minimal_package([
            {"step": 1, "name": "Escalate", "action": "FORCE_ESCALATE here",
             "execution_semantics": {}},
            {"step": 2, "name": "After", "action": "Should skip",
             "execution_semantics": {}},
        ])
        result = execute_package(pkg, "test data", MockAdapter(seed=42))
        assert result["steps"][0]["state"] == "escalated"
        assert result["steps"][1]["state"] == "skipped"
        assert len(result["novel_situations"]) >= 1

    def test_dependency_skip(self):
        pkg = _minimal_package([
            {"step": 1, "name": "Fail", "action": "FORCE_FAIL here",
             "execution_semantics": {"on_failure": "halt"}},
            {"step": 2, "name": "Depends", "action": "Needs step 1",
             "depends_on": [1], "execution_semantics": {}},
        ])
        result = execute_package(pkg, "test data", MockAdapter(seed=42))
        assert result["steps"][1]["state"] == "skipped"

    def test_retry_on_failure(self):
        pkg = _minimal_package([
            {"step": 1, "name": "Retry", "action": "FORCE_FAIL here",
             "execution_semantics": {"on_failure": "retry", "max_retries": 2}},
        ])
        result = execute_package(pkg, "test data", MockAdapter(seed=42))
        assert result["steps"][0]["state"] == "failure"
        assert result["steps"][0]["retries_attempted"] == 2

    def test_progress_callbacks(self):
        starts = []
        ends = []

        def on_start(n, name):
            starts.append((n, name))

        def on_end(n, name, result):
            ends.append((n, name, result.state))

        pkg = _minimal_package([
            {"step": 1, "name": "Step 1", "action": "Do A", "execution_semantics": {}},
        ])
        execute_package(pkg, "data", MockAdapter(seed=42),
                        on_step_start=on_start, on_step_end=on_end)
        assert len(starts) == 1
        assert len(ends) == 1
        assert starts[0] == (1, "Step 1")
        assert ends[0][2] == "success"
