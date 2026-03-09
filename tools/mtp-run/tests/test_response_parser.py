"""Tests for LLM response parsing."""

from mtp_run.response_parser import parse_step_response


class TestParseStepResponse:
    def test_yaml_block_parsed(self):
        raw = """Here is the result:
```yaml
state: success
validation_result: pass
output: |
  Some output here
notes: "All good"
```
"""
        result = parse_step_response(raw)
        assert result.state == "success"
        assert result.validation_result == "pass"
        assert "Some output" in result.output

    def test_plain_yaml_parsed(self):
        raw = """state: deviation
validation_result: pass
output: adjusted result
deviation_description: used alternative
deviation_reason: original not applicable
"""
        result = parse_step_response(raw)
        assert result.state == "deviation"
        assert result.deviation_description == "used alternative"

    def test_heuristic_fallback_failure(self):
        raw = "I cannot complete this task because of an error in the data."
        result = parse_step_response(raw)
        assert result.state == "failure"
        assert "heuristic" in result.notes.lower()

    def test_heuristic_fallback_success(self):
        raw = "The analysis is complete. All metrics look good."
        result = parse_step_response(raw)
        assert result.state == "success"

    def test_heuristic_fallback_escalated(self):
        raw = "This situation requires escalation to a human reviewer."
        result = parse_step_response(raw)
        assert result.state == "escalated"

    def test_invalid_state_normalized_to_failure(self):
        raw = """state: invalid_state
validation_result: pass
output: some output
"""
        result = parse_step_response(raw)
        assert result.state == "failure"

    def test_invalid_validation_normalized(self):
        raw = """state: success
validation_result: maybe
output: some output
"""
        result = parse_step_response(raw)
        assert result.validation_result == "not_applicable"

    def test_edge_cases_parsed(self):
        raw = """state: success
validation_result: pass
output: done
edge_cases:
  - scenario: missing values
    matched_edge_case: ec_1
    handling_applied: filled with defaults
"""
        result = parse_step_response(raw)
        assert len(result.edge_cases_encountered) == 1
        assert result.edge_cases_encountered[0]["scenario"] == "missing values"

    def test_novel_situations_parsed(self):
        raw = """state: escalated
validation_result: not_applicable
output: ""
novel_situations:
  - description: unexpected format
    action_taken: escalated
"""
        result = parse_step_response(raw)
        assert len(result.novel_situations) == 1

    def test_dead_ends_parsed(self):
        raw = """state: success
validation_result: pass
output: done
dead_ends_considered:
  - dead_end_ref: de_1
    notes: avoided regex approach
"""
        result = parse_step_response(raw)
        assert len(result.dead_ends_considered) == 1
