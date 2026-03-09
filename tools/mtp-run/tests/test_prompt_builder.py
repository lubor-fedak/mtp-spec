"""Tests for prompt builder."""

from mtp_run.prompt_builder import build_system_context, build_step_prompt, build_data_section


class TestBuildSystemContext:
    def test_includes_intent(self):
        pkg = {
            "intent": {"goal": "Analyze churn"},
            "methodology": {"approach": "Score each customer"},
            "edge_cases": [],
            "dead_ends": [],
        }
        ctx = build_system_context(pkg)
        assert "Analyze churn" in ctx
        assert "Score each customer" in ctx

    def test_includes_dead_ends(self):
        pkg = {
            "intent": {"goal": "Test"},
            "methodology": {"approach": "Do it"},
            "edge_cases": [],
            "dead_ends": [
                {"approach": "regex parsing", "reason": "too fragile", "lesson": "use structured"},
            ],
        }
        ctx = build_system_context(pkg)
        assert "regex parsing" in ctx
        assert "DEAD ENDS" in ctx

    def test_includes_response_format(self):
        pkg = {
            "intent": {"goal": "Test"},
            "methodology": {"approach": "Do it"},
            "edge_cases": [],
            "dead_ends": [],
        }
        ctx = build_system_context(pkg)
        assert "RESPONSE FORMAT" in ctx
        assert "success" in ctx
        assert "deviation" in ctx
        assert "escalated" in ctx

    def test_includes_non_goals(self):
        pkg = {
            "intent": {"goal": "Test", "non_goals": ["Do not predict"]},
            "methodology": {"approach": "Do it"},
            "edge_cases": [],
            "dead_ends": [],
        }
        ctx = build_system_context(pkg)
        assert "Do not predict" in ctx


class TestBuildStepPrompt:
    def test_includes_action(self):
        step = {"step": 1, "name": "Parse", "action": "Parse the CSV"}
        prompt = build_step_prompt(step, [], {})
        assert "Parse the CSV" in prompt
        assert "STEP 1" in prompt

    def test_includes_validation(self):
        step = {"step": 1, "name": "Parse", "action": "Do it", "validation": "All rows parsed"}
        prompt = build_step_prompt(step, [], {})
        assert "All rows parsed" in prompt
        assert "VALIDATION" in prompt

    def test_includes_edge_cases(self):
        step = {"step": 1, "name": "Parse", "action": "Do it"}
        edge_cases = [{"scenario": "empty file", "severity": "high", "handling": "return empty"}]
        prompt = build_step_prompt(step, edge_cases, {})
        assert "empty file" in prompt

    def test_includes_prior_outputs(self):
        step = {"step": 2, "name": "Analyze", "action": "Do it", "depends_on": [1]}
        outputs = {1: "previous output data"}
        prompt = build_step_prompt(step, [], outputs)
        assert "previous output data" in prompt

    def test_truncates_long_outputs(self):
        step = {"step": 2, "name": "Analyze", "action": "Do it", "depends_on": [1]}
        outputs = {1: "x" * 3000}
        prompt = build_step_prompt(step, [], outputs)
        assert "[truncated]" in prompt


class TestBuildDataSection:
    def test_basic_data(self):
        section = build_data_section("col1,col2\na,b")
        assert "DATA" in section
        assert "col1,col2" in section

    def test_with_assumptions(self):
        section = build_data_section("data here", {"assumptions": ["UTF-8 encoded"]})
        assert "UTF-8 encoded" in section
