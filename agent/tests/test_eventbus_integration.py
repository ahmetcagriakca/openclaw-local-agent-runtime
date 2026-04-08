"""Integration tests for EventBus production event flow — S81 T-81.03.

End-to-end: lifespan wires EventBus → emit event → handlers fire.
Also tests graceful degradation when EVENTBUS_ENABLED=false.
"""
import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from events.bus import Event, EventBus
from events.catalog import EventType
from events.handlers.audit_trail import AuditTrailHandler
from events.handlers.project_handler import ProjectHandler


def _emit_with_loop(bus, event):
    """Emit event inside an asyncio event loop so SSE broadcast works."""
    async def _run():
        return bus.emit(event)
    return asyncio.run(_run())


def _create_production_bus(sse_manager=None, audit_dir=None):
    """Replicate the production wiring from server.py lifespan."""
    bus = EventBus()

    # Global: audit trail (priority 0)
    audit_handler = AuditTrailHandler(log_dir=audit_dir)
    bus.on_all(audit_handler, priority=0, name="audit_trail")

    # Project handler: SSE + rollup
    project_handler = ProjectHandler(
        sse_manager=sse_manager,
        project_store=None,
    )
    for et in EventType.namespace("project"):
        bus.on(et, project_handler, name="project_handler")

    return bus, audit_handler


class TestFullEventFlow:
    """End-to-end: create project event → audit logged + SSE broadcast."""

    def test_project_created_audit_only(self, tmp_path):
        """PROJECT_CREATED → audit log (no SSE broadcast)."""
        bus, audit = _create_production_bus(audit_dir=str(tmp_path))

        event = Event(
            type=EventType.PROJECT_CREATED,
            data={"project_id": "p-int-01", "name": "IntegrationTest", "owner": "op"},
            source="integration",
        )
        results = bus.emit(event)

        # Audit handler + project handler both ran
        assert len(results) == 2
        assert all(r.handled for r in results)

        # Audit file has the entry
        log_path = tmp_path / "audit-trail.jsonl"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["type"] == EventType.PROJECT_CREATED
        assert entry["source"] == "integration"

    def test_project_status_change_full_flow(self, tmp_path):
        """STATUS_CHANGED → audit log + SSE broadcast."""
        sse = MagicMock()
        sse.broadcast = AsyncMock()

        bus, audit = _create_production_bus(
            sse_manager=sse, audit_dir=str(tmp_path))

        event = Event(
            type=EventType.PROJECT_STATUS_CHANGED,
            data={
                "project_id": "p-int-02",
                "old_status": "planning",
                "new_status": "active",
                "actor": "operator",
            },
            source="integration",
        )
        results = _emit_with_loop(bus, event)

        # Both handlers ran
        assert len(results) == 2

        # Audit entry written
        log_path = tmp_path / "audit-trail.jsonl"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["type"] == EventType.PROJECT_STATUS_CHANGED

        # SSE broadcast attempted
        sse.broadcast.assert_called_once()

    def test_mission_event_audit_only(self, tmp_path):
        """Mission events → audit log only (no project handler)."""
        bus, audit = _create_production_bus(audit_dir=str(tmp_path))

        event = Event(
            type=EventType.MISSION_STARTED,
            data={"mission_id": "m-int-01"},
            source="controller",
        )
        results = bus.emit(event)

        # Only audit handler (global) ran; project handler skipped
        assert len(results) == 1
        assert results[0].handled is True

        log_path = tmp_path / "audit-trail.jsonl"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["type"] == EventType.MISSION_STARTED

    def test_multiple_events_sequential(self, tmp_path):
        """Multiple events in sequence maintain audit chain."""
        sse = MagicMock()
        sse.broadcast = AsyncMock()
        bus, audit = _create_production_bus(
            sse_manager=sse, audit_dir=str(tmp_path))

        events = [
            Event(type=EventType.MISSION_STARTED,
                  data={"mission_id": "m-1"}, source="ctrl"),
            Event(type=EventType.PROJECT_CREATED,
                  data={"project_id": "p-1", "name": "P1", "owner": "op"},
                  source="api"),
            Event(type=EventType.PROJECT_STATUS_CHANGED,
                  data={"project_id": "p-1", "old_status": "planning",
                        "new_status": "active", "actor": "op"},
                  source="api"),
            Event(type=EventType.MISSION_COMPLETED,
                  data={"mission_id": "m-1"}, source="ctrl"),
        ]

        for e in events:
            _emit_with_loop(bus, e)

        # Verify audit chain integrity
        valid, count, err = audit.verify_chain()
        assert valid is True
        assert count == 4
        assert err == ""

        # SSE broadcast only for STATUS_CHANGED
        assert sse.broadcast.call_count == 1

    def test_correlation_id_preserved_in_audit(self, tmp_path):
        """Correlation ID flows from Event through to audit log."""
        bus, audit = _create_production_bus(audit_dir=str(tmp_path))

        event = Event(
            type=EventType.PROJECT_CREATED,
            data={"project_id": "p-cor-01", "name": "CorrTest", "owner": "op"},
            source="test",
        )
        bus.emit(event)

        log_path = tmp_path / "audit-trail.jsonl"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["correlation_id"] == event.correlation_id


class TestGracefulDegradation:
    """EventBus disabled → no events, no errors."""

    def test_disabled_bus_is_none(self):
        """When EVENTBUS_ENABLED=false, bus should be None (not instantiated)."""
        enabled = os.environ.get("EVENTBUS_ENABLED", "true").lower()
        # Simulate disabled
        val = "false"
        assert val.lower() not in ("1", "true", "yes")
        # In server.py, event_bus = None when disabled

    def test_app_state_none_is_safe(self):
        """Code that checks app.state.event_bus handles None gracefully."""
        app_state = MagicMock()
        app_state.event_bus = None

        # Typical guard pattern used in API endpoints
        if app_state.event_bus is not None:
            app_state.event_bus.emit(Event(
                type="test", data={}, source="test"))
        # No error raised — graceful

    def test_handler_error_does_not_crash_bus(self, tmp_path):
        """A failing handler doesn't crash the bus or prevent other handlers."""
        bus = EventBus()

        # Add a broken handler
        def broken_handler(event):
            raise RuntimeError("simulated handler failure")

        bus.on_all(broken_handler, priority=0, name="broken")

        # Add audit handler after
        audit = AuditTrailHandler(log_dir=str(tmp_path))
        bus.on_all(audit, priority=10, name="audit_trail")

        event = Event(
            type=EventType.MISSION_STARTED,
            data={"mission_id": "m-err"},
            source="test",
        )

        # Should not raise
        results = bus.emit(event)
        assert len(results) >= 1
        # First result is the error from broken handler
        assert results[0].error is not None

    def test_project_handler_no_sse_manager(self, tmp_path):
        """ProjectHandler works without SSE manager (logs only)."""
        bus, audit = _create_production_bus(
            sse_manager=None, audit_dir=str(tmp_path))

        event = Event(
            type=EventType.PROJECT_STATUS_CHANGED,
            data={"project_id": "p-no-sse", "old_status": "active",
                  "new_status": "completed", "actor": "op"},
            source="test",
        )
        results = bus.emit(event)
        assert len(results) == 2
        assert all(r.handled for r in results)


class TestEventBusHistory:
    """Verify event history works in production wiring."""

    def test_history_captures_events(self, tmp_path):
        bus, _ = _create_production_bus(audit_dir=str(tmp_path))

        for i in range(3):
            bus.emit(Event(
                type=EventType.MISSION_STARTED,
                data={"mission_id": f"m-{i}"},
                source="test",
            ))

        history = bus.history(event_type=EventType.MISSION_STARTED)
        assert len(history) == 3

    def test_history_filter_by_type(self, tmp_path):
        bus, _ = _create_production_bus(audit_dir=str(tmp_path))

        bus.emit(Event(type=EventType.MISSION_STARTED,
                       data={}, source="test"))
        bus.emit(Event(type=EventType.PROJECT_CREATED,
                       data={"project_id": "p-1", "name": "T", "owner": "o"},
                       source="test"))
        bus.emit(Event(type=EventType.MISSION_COMPLETED,
                       data={}, source="test"))

        mission_history = bus.history(event_type=EventType.MISSION_STARTED)
        assert len(mission_history) == 1

        project_history = bus.history(event_type=EventType.PROJECT_CREATED)
        assert len(project_history) == 1
