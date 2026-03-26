"""Tests for D-102 L1 stage boundary isolation."""
import pytest

from mission.stage_result import StageResult, extract_stage_result


class TestStageResult:
    """StageResult dataclass tests."""

    def test_frozen_immutable(self):
        sr = StageResult(
            stage_name="s1", specialist="analyst",
            artifact_text="hello", artifact_tokens=2,
            token_count=100, tool_calls_made=3,
            policy_denies=1, duration_ms=500,
        )
        with pytest.raises(AttributeError):
            sr.artifact_text = "mutated"

    def test_fields_preserved(self):
        sr = StageResult(
            stage_name="s2", specialist="developer",
            artifact_text="code output", artifact_tokens=3,
            token_count=5000, tool_calls_made=10,
            policy_denies=2, duration_ms=12000,
        )
        assert sr.stage_name == "s2"
        assert sr.specialist == "developer"
        assert sr.artifact_text == "code output"
        assert sr.token_count == 5000
        assert sr.tool_calls_made == 10
        assert sr.policy_denies == 2


class TestExtractStageResult:
    """extract_stage_result() isolation tests."""

    def _make_stage(self, **overrides):
        base = {
            "id": "stage-1",
            "specialist": "analyst",
            "status": "completed",
            "result": "Analysis complete. Found 3 files.",
            "tool_call_count": 2,
            "policy_deny_count": 0,
            "duration_ms": 3500,
            "token_report": {
                "total_tokens": 8000,
                "total_tool_calls": 2,
                "truncations": 0,
                "blocks": 0,
            },
            # These should NOT appear in StageResult:
            "tool_calls_detail": [
                {"name": "read_file", "params": {"path": "/etc/hosts"},
                 "result": "127.0.0.1 localhost\n" * 500,
                 "policyDenied": False},
                {"name": "list_directory", "params": {"path": "/home"},
                 "result": "user1\nuser2\n" * 200,
                 "policyDenied": False},
            ],
            "system_prompt": "You are an analyst..." * 50,
            "user_prompt": "Analyze the repository structure..." * 20,
        }
        base.update(overrides)
        return base

    def test_extracts_artifact_text_only(self):
        stage = self._make_stage()
        sr = extract_stage_result(stage)
        assert sr.artifact_text == "Analysis complete. Found 3 files."
        assert sr.artifact_tokens > 0

    def test_tool_history_not_in_result(self):
        stage = self._make_stage()
        sr = extract_stage_result(stage)
        # StageResult has no tool_calls_detail attribute
        assert not hasattr(sr, "tool_calls_detail")
        assert not hasattr(sr, "system_prompt")
        assert not hasattr(sr, "user_prompt")
        # artifact_text should not contain tool response content
        assert "127.0.0.1" not in sr.artifact_text
        assert "user1" not in sr.artifact_text

    def test_metrics_extracted(self):
        stage = self._make_stage()
        sr = extract_stage_result(stage)
        assert sr.stage_name == "stage-1"
        assert sr.specialist == "analyst"
        assert sr.token_count == 8000
        assert sr.tool_calls_made == 2
        assert sr.policy_denies == 0
        assert sr.duration_ms == 3500

    def test_dict_result_converted_to_string(self):
        stage = self._make_stage(result={"key": "value", "nested": [1, 2]})
        sr = extract_stage_result(stage)
        assert isinstance(sr.artifact_text, str)
        assert "key" in sr.artifact_text
        assert "value" in sr.artifact_text

    def test_missing_fields_handled(self):
        minimal_stage = {"id": "s-min", "specialist": "pm"}
        sr = extract_stage_result(minimal_stage)
        assert sr.stage_name == "s-min"
        assert sr.artifact_text == ""
        assert sr.token_count == 0
        assert sr.tool_calls_made == 0

    def test_none_result_handled(self):
        stage = self._make_stage(result=None)
        sr = extract_stage_result(stage)
        assert sr.artifact_text == ""

    def test_large_tool_response_not_leaked(self):
        """Simulate a stage where tool calls returned massive data.
        StageResult should contain only the final artifact text."""
        huge_tool_response = "x" * 200_000  # 200K chars = ~50K tokens
        stage = self._make_stage(
            result="Summary: 3 endpoints found.",
            tool_calls_detail=[
                {"name": "snapshot", "result": huge_tool_response},
            ],
        )
        sr = extract_stage_result(stage)
        assert len(sr.artifact_text) < 100
        assert sr.artifact_text == "Summary: 3 endpoints found."
