"""Tests for provider selection telemetry (D-148)."""
import json
import os
import tempfile
from unittest.mock import patch

import pytest

from providers.provider_telemetry import emit_provider_selection
from providers.routing_policy import RoutingDecision


class TestProviderTelemetry:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_path = os.path.join(self.tmpdir, "policy-telemetry.jsonl")

    def _read_events(self):
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    @patch("context.policy_telemetry.TELEMETRY_LOG_PATH")
    def test_primary_selection_event(self, mock_path):
        mock_path.__str__ = lambda s: self.log_path
        # Patch at module level
        import context.policy_telemetry as pt
        orig = pt.TELEMETRY_LOG_PATH
        pt.TELEMETRY_LOG_PATH = self.log_path

        try:
            decision = RoutingDecision(
                selected_provider="azure-general",
                reason="primary provider (azure-first policy)",
            )
            emit_provider_selection(decision, task_type="review")

            events = self._read_events()
            assert len(events) == 1
            assert events[0]["event"] == "provider_selection"
            assert events[0]["selected_provider"] == "azure-general"
            assert events[0]["reason"] == "primary provider (azure-first policy)"
            assert events[0]["fallback_used"] is False
            assert events[0]["task_type"] == "review"
            assert "timestamp" in events[0]
        finally:
            pt.TELEMETRY_LOG_PATH = orig

    @patch("context.policy_telemetry.TELEMETRY_LOG_PATH")
    def test_fallback_event(self, mock_path):
        import context.policy_telemetry as pt
        orig = pt.TELEMETRY_LOG_PATH
        pt.TELEMETRY_LOG_PATH = self.log_path

        try:
            decision = RoutingDecision(
                selected_provider="gpt-general",
                reason="fallback: gpt-general",
                fallback_used=True,
                fallback_reason="azure kill switch active",
            )
            emit_provider_selection(decision, task_type="implementation", mission_id="m-001")

            events = self._read_events()
            assert len(events) == 1
            assert events[0]["event"] == "provider_fallback"
            assert events[0]["selected_provider"] == "gpt-general"
            assert events[0]["fallback_used"] is True
            assert events[0]["fallback_reason"] == "azure kill switch active"
            assert events[0]["mission_id"] == "m-001"
        finally:
            pt.TELEMETRY_LOG_PATH = orig

    @patch("context.policy_telemetry.TELEMETRY_LOG_PATH")
    def test_multiple_events(self, mock_path):
        import context.policy_telemetry as pt
        orig = pt.TELEMETRY_LOG_PATH
        pt.TELEMETRY_LOG_PATH = self.log_path

        try:
            for i in range(3):
                decision = RoutingDecision(
                    selected_provider=f"provider-{i}",
                    reason=f"test reason {i}",
                )
                emit_provider_selection(decision)

            events = self._read_events()
            assert len(events) == 3
            assert events[0]["selected_provider"] == "provider-0"
            assert events[2]["selected_provider"] == "provider-2"
        finally:
            pt.TELEMETRY_LOG_PATH = orig

    @patch("context.policy_telemetry.TELEMETRY_LOG_PATH")
    def test_no_optional_fields(self, mock_path):
        import context.policy_telemetry as pt
        orig = pt.TELEMETRY_LOG_PATH
        pt.TELEMETRY_LOG_PATH = self.log_path

        try:
            decision = RoutingDecision(
                selected_provider="azure-general",
                reason="primary",
            )
            emit_provider_selection(decision)

            events = self._read_events()
            assert len(events) == 1
            assert "task_type" not in events[0]
            assert "mission_id" not in events[0]
            assert "fallback_reason" not in events[0]
        finally:
            pt.TELEMETRY_LOG_PATH = orig

    def test_emit_is_best_effort(self):
        """Telemetry should not raise on write failure."""
        import context.policy_telemetry as pt
        orig = pt.TELEMETRY_LOG_PATH
        pt.TELEMETRY_LOG_PATH = "/nonexistent/path/telemetry.jsonl"

        try:
            decision = RoutingDecision(
                selected_provider="azure-general",
                reason="test",
            )
            # Should not raise
            emit_provider_selection(decision)
        finally:
            pt.TELEMETRY_LOG_PATH = orig
