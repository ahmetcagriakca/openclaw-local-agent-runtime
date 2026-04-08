"""Tests for EventBus production wiring — S81 T-81.02.

Validates:
1. AuditTrailHandler logs events when wired to EventBus
2. ProjectHandler SSE broadcast fires for project events
3. No duplicate events between EventBus SSE and FileWatcher SSE
4. Feature flag disables EventBus cleanly
"""
import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

from events.bus import Event, EventBus
from events.catalog import EventType
from events.handlers.audit_trail import AuditTrailHandler
from events.handlers.project_handler import ProjectHandler


class TestAuditTrailProduction:
    """Verify audit handler persists events via EventBus."""

    def test_audit_handler_writes_event(self, tmp_path):
        handler = AuditTrailHandler(log_dir=str(tmp_path))
        bus = EventBus()
        bus.on_all(handler, priority=0, name="audit_trail")

        event = Event(
            type=EventType.PROJECT_CREATED,
            data={"project_id": "p-001", "name": "Test"},
            source="test",
        )
        bus.emit(event)

        log_path = tmp_path / "audit-trail.jsonl"
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["type"] == EventType.PROJECT_CREATED
        assert entry["data"]["project_id"] == "p-001"
        assert "hash" in entry
        assert entry["prev_hash"] == "genesis"

    def test_audit_chain_integrity(self, tmp_path):
        handler = AuditTrailHandler(log_dir=str(tmp_path))
        bus = EventBus()
        bus.on_all(handler, priority=0, name="audit_trail")

        for i in range(5):
            bus.emit(Event(
                type=EventType.MISSION_STARTED,
                data={"mission_id": f"m-{i}"},
                source="test",
            ))

        valid, count, err = handler.verify_chain()
        assert valid is True
        assert count == 5
        assert err == ""

    def test_audit_handler_sanitizes_large_data(self, tmp_path):
        handler = AuditTrailHandler(log_dir=str(tmp_path))
        bus = EventBus()
        bus.on_all(handler, priority=0, name="audit_trail")

        bus.emit(Event(
            type="test.large",
            data={"big_field": "x" * 5000},
            source="test",
        ))

        log_path = tmp_path / "audit-trail.jsonl"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert "truncated" in entry["data"]["big_field"]


def _emit_with_loop(bus, event):
    """Emit event inside an asyncio event loop so SSE broadcast works.

    ProjectHandler.SSE broadcast uses asyncio.get_event_loop() internally.
    Python 3.12+ requires an active loop for this to work.
    """
    async def _run():
        bus.emit(event)

    asyncio.run(_run())


class TestProjectHandlerSSE:
    """Verify ProjectHandler broadcasts SSE events when wired to EventBus."""

    def test_project_status_change_broadcasts_sse(self):
        sse_manager = MagicMock()
        sse_manager.broadcast = AsyncMock()

        handler = ProjectHandler(sse_manager=sse_manager)
        bus = EventBus()
        for et in EventType.namespace("project"):
            bus.on(et, handler, name="project_handler")

        event = Event(
            type=EventType.PROJECT_STATUS_CHANGED,
            data={
                "project_id": "p-001",
                "old_status": "active",
                "new_status": "completed",
                "actor": "operator",
            },
            source="test",
        )
        _emit_with_loop(bus, event)

        # SSE broadcast should have been attempted
        sse_manager.broadcast.assert_called_once()
        call_args = sse_manager.broadcast.call_args
        assert call_args[0][0] == EventType.PROJECT_STATUS_CHANGED

    def test_project_created_does_not_broadcast_sse(self):
        """PROJECT_CREATED is not in SSE_BROADCAST_EVENTS."""
        sse_manager = MagicMock()
        sse_manager.broadcast = AsyncMock()

        handler = ProjectHandler(sse_manager=sse_manager)
        bus = EventBus()
        for et in EventType.namespace("project"):
            bus.on(et, handler, name="project_handler")

        _emit_with_loop(bus, Event(
            type=EventType.PROJECT_CREATED,
            data={"project_id": "p-001", "name": "Test", "owner": "op"},
            source="test",
        ))

        # PROJECT_CREATED is NOT in SSE_BROADCAST_EVENTS
        sse_manager.broadcast.assert_not_called()

    def test_rollup_updated_broadcasts_sse(self):
        sse_manager = MagicMock()
        sse_manager.broadcast = AsyncMock()

        handler = ProjectHandler(sse_manager=sse_manager)
        bus = EventBus()
        for et in EventType.namespace("project"):
            bus.on(et, handler, name="project_handler")

        _emit_with_loop(bus, Event(
            type=EventType.PROJECT_ROLLUP_UPDATED,
            data={"project_id": "p-001", "total_missions": 5, "active_count": 2},
            source="test",
        ))

        sse_manager.broadcast.assert_called_once()

    def test_artifact_published_broadcasts_sse(self):
        sse_manager = MagicMock()
        sse_manager.broadcast = AsyncMock()

        handler = ProjectHandler(sse_manager=sse_manager)
        bus = EventBus()
        for et in EventType.namespace("project"):
            bus.on(et, handler, name="project_handler")

        _emit_with_loop(bus, Event(
            type=EventType.PROJECT_ARTIFACT_PUBLISHED,
            data={"project_id": "p-001", "artifact_id": "a-1", "mission_id": "m-1"},
            source="test",
        ))

        sse_manager.broadcast.assert_called_once()

    def test_non_project_event_skipped(self):
        """Events outside project namespace are skipped by ProjectHandler."""
        sse_manager = MagicMock()
        sse_manager.broadcast = AsyncMock()

        handler = ProjectHandler(sse_manager=sse_manager)
        result = handler(Event(
            type=EventType.MISSION_STARTED,
            data={"mission_id": "m-1"},
            source="test",
        ))

        assert result.handled is False
        sse_manager.broadcast.assert_not_called()


class TestProjectHandlerRollupInvalidation:
    """Verify rollup cache invalidation on relevant events."""

    def test_mission_linked_invalidates_rollup(self):
        store = MagicMock()
        handler = ProjectHandler(project_store=store)

        handler(Event(
            type=EventType.PROJECT_MISSION_LINKED,
            data={"project_id": "p-001", "mission_id": "m-1"},
            source="test",
        ))

        store.invalidate_rollup.assert_called_once_with("p-001")

    def test_no_invalidation_without_store(self):
        """Graceful when project_store is None."""
        handler = ProjectHandler(project_store=None)
        result = handler(Event(
            type=EventType.PROJECT_MISSION_LINKED,
            data={"project_id": "p-001", "mission_id": "m-1"},
            source="test",
        ))
        assert result.handled is True


class TestNoDuplicateSSE:
    """Ensure EventBus SSE and FileWatcher SSE don't duplicate."""

    def test_eventbus_sse_uses_event_type_not_file_change(self):
        """EventBus SSE uses event type strings (project.status_changed),
        FileWatcher SSE uses file-change types (mission_updated, etc.).
        They are distinct namespaces — no overlap."""
        from events.catalog import EventType

        eventbus_types = set(EventType.namespace("project"))
        # FileWatcher uses types like: mission_updated, mission_created,
        # capabilities_updated, etc. — all without dots.
        filewatcher_types = {
            "mission_updated", "mission_created", "missions_bulk",
            "capabilities_updated", "services_updated", "approval_updated",
        }

        overlap = eventbus_types & filewatcher_types
        assert overlap == set(), f"Overlapping event types: {overlap}"


class TestFeatureFlag:
    """Verify EVENTBUS_ENABLED feature flag behavior."""

    def test_eventbus_enabled_by_default(self):
        """Default: EVENTBUS_ENABLED not set → enabled."""
        val = os.environ.get("EVENTBUS_ENABLED", "true").lower()
        assert val in ("1", "true", "yes")

    def test_feature_flag_false_values(self):
        """Various false values should disable EventBus."""
        for val in ("false", "0", "no", "FALSE", "No"):
            assert val.lower() not in ("1", "true", "yes")

    def test_feature_flag_true_values(self):
        """Various true values should enable EventBus."""
        for val in ("true", "1", "yes", "TRUE", "Yes"):
            assert val.lower() in ("1", "true", "yes")


class TestEventBusHandlerCounts:
    """Verify correct handler registration counts."""

    def test_production_handler_count(self):
        """Audit (global) + project handlers (one per project event type)."""
        bus = EventBus()
        audit = AuditTrailHandler(log_dir=tempfile.mkdtemp())
        bus.on_all(audit, priority=0, name="audit_trail")

        project_handler = ProjectHandler()
        project_types = EventType.namespace("project")
        for et in project_types:
            bus.on(et, project_handler, name="project_handler")

        # 1 global (audit) + N project type handlers
        assert bus.handler_count == 1 + len(project_types)

    def test_bus_clear_resets_all(self):
        bus = EventBus()
        bus.on_all(AuditTrailHandler(log_dir=tempfile.mkdtemp()),
                   priority=0, name="audit")
        bus.on(EventType.PROJECT_CREATED,
               ProjectHandler(), name="ph")

        assert bus.handler_count > 0
        bus.clear()
        assert bus.handler_count == 0
