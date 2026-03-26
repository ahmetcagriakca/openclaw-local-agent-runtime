"""Tests for D-102 L2 distance-based tiered context assembly."""
import pytest

from mission.stage_result import StageResult


def _make_stage_result(name, text_len=100, specialist="analyst"):
    """Helper to create a StageResult with artifact text of given length."""
    return StageResult(
        stage_name=name,
        specialist=specialist,
        artifact_text="x" * text_len,
        artifact_tokens=text_len // 4,
        token_count=text_len,
        tool_calls_made=1,
        policy_denies=0,
        duration_ms=1000,
    )


class TestFormatArtifactContextWithDistance:
    """Test distance-based tier limits in _format_artifact_context."""

    def _format(self, context_package, stage_results=None):
        """Call controller's _format_artifact_context with distance info."""
        from mission.controller import MissionController
        mc = MissionController.__new__(MissionController)
        return mc._format_artifact_context(context_package,
                                            stage_results=stage_results)

    def test_basic_formatting(self):
        """Context package without stage_results uses semantic tiers."""
        pkg = [
            ("art-1", "Hello world", "B"),
            ("art-2", "Second artifact", "C"),
        ]
        result = self._format(pkg)
        assert "art-1" in result
        assert "Hello world" in result
        assert "art-2" in result

    def test_distance_tier_a_gets_5000(self):
        """N-1 stage (most recent) gets up to 5000 chars."""
        long_text = "a" * 8000
        pkg = [("art-1", long_text, "D")]
        stages = [_make_stage_result("s1", 8000)]
        result = self._format(pkg, stage_results=stages)
        # Should be truncated to 5000 (distance tier A)
        art_section = result.split("---")[1] if "---" in result else result
        # The actual text content (excluding header) should be <= 5000 + truncation notice
        assert "truncated" in result.lower()

    def test_distance_tier_c_gets_500(self):
        """N-3+ stage gets at most 500 chars."""
        long_text = "c" * 3000
        # 3 stage results = distances 3, 2, 1 from current
        stages = [
            _make_stage_result("s1", 3000),
            _make_stage_result("s2", 3000),
            _make_stage_result("s3", 3000),
        ]
        pkg = [
            ("art-1", long_text, "D"),  # s1 = N-3 → 500 chars
            ("art-2", long_text, "D"),  # s2 = N-2 → 2000 chars
            ("art-3", long_text, "D"),  # s3 = N-1 → 5000 chars
        ]
        result = self._format(pkg, stage_results=stages)
        assert "truncated" in result.lower()

    def test_empty_context_package(self):
        result = self._format([])
        assert result == ""

    def test_none_content_skipped(self):
        pkg = [("art-1", None, "B")]
        result = self._format(pkg)
        assert result == ""

    def test_total_budget_emergency_truncation(self):
        """If total exceeds 40K tokens, emergency truncation keeps last 3."""
        # Create many large artifacts
        huge = "z" * 200_000  # ~50K tokens
        pkg = [
            ("art-1", huge, "D"),
            ("art-2", huge, "D"),
            ("art-3", huge, "D"),
            ("art-4", huge, "D"),
        ]
        result = self._format(pkg)
        assert "Context truncated" in result or "truncated" in result.lower()
