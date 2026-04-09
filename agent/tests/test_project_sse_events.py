"""Tests for project SSE events — D-145 Faz 2B (T75.11).

Tests SSE broadcast wiring for project events and rollup invalidation.
"""
from unittest.mock import MagicMock

from events.bus import Event
from events.catalog import EventType
from events.handlers.project_handler import (
    PROJECT_EVENT_TYPES,
    ROLLUP_INVALIDATION_EVENTS,
    SSE_BROADCAST_EVENTS,
    ProjectHandler,
)


class TestSSEBroadcastEvents:
    """T75.11: Verify SSE broadcast event set."""

    def test_sse_broadcast_events_defined(self):
        assert EventType.PROJECT_STATUS_CHANGED in SSE_BROADCAST_EVENTS
        assert EventType.PROJECT_ROLLUP_UPDATED in SSE_BROADCAST_EVENTS
        assert EventType.PROJECT_ARTIFACT_PUBLISHED in SSE_BROADCAST_EVENTS
        assert EventType.PROJECT_ARTIFACT_UNPUBLISHED in SSE_BROADCAST_EVENTS

    def test_sse_broadcast_events_count(self):
        assert len(SSE_BROADCAST_EVENTS) == 7  # 4 original + 3 GitHub (D-151)

    def test_sse_broadcast_events_are_subset_of_project_events(self):
        assert SSE_BROADCAST_EVENTS.issubset(PROJECT_EVENT_TYPES)


class TestRollupInvalidationEvents:
    """T75.11: Verify rollup invalidation event set."""

    def test_rollup_invalidation_events_defined(self):
        assert EventType.PROJECT_MISSION_LINKED in ROLLUP_INVALIDATION_EVENTS
        assert EventType.PROJECT_MISSION_UNLINKED in ROLLUP_INVALIDATION_EVENTS
        assert EventType.PROJECT_STATUS_CHANGED in ROLLUP_INVALIDATION_EVENTS

    def test_rollup_invalidation_events_count(self):
        assert len(ROLLUP_INVALIDATION_EVENTS) == 3


class TestProjectHandlerSSEBroadcast:
    """T75.11: Handler SSE broadcast tests."""

    def test_handler_accepts_sse_manager(self):
        sse = MagicMock()
        handler = ProjectHandler(sse_manager=sse)
        assert handler._sse_manager is sse

    def test_handler_accepts_project_store(self):
        store = MagicMock()
        handler = ProjectHandler(project_store=store)
        assert handler._project_store is store

    def test_handler_without_sse_still_works(self):
        handler = ProjectHandler()
        event = Event(
            type=EventType.PROJECT_STATUS_CHANGED,
            data={"project_id": "p1", "old_status": "draft", "new_status": "active"},
            source="test",
        )
        result = handler(event)
        assert result.handled is True

    def test_handler_rollup_invalidation_calls_store(self):
        store = MagicMock()
        handler = ProjectHandler(project_store=store)
        event = Event(
            type=EventType.PROJECT_MISSION_LINKED,
            data={"project_id": "p1", "mission_id": "m1"},
            source="test",
        )
        handler(event)
        store.invalidate_rollup.assert_called_once_with("p1")

    def test_handler_non_invalidation_event_skips_store(self):
        store = MagicMock()
        handler = ProjectHandler(project_store=store)
        event = Event(
            type=EventType.PROJECT_CREATED,
            data={"project_id": "p1", "name": "Test"},
            source="test",
        )
        handler(event)
        store.invalidate_rollup.assert_not_called()


class TestProjectHandlerRollupEvent:
    """T75.11: Rollup updated event handling."""

    def test_handles_rollup_updated(self):
        handler = ProjectHandler()
        event = Event(
            type=EventType.PROJECT_ROLLUP_UPDATED,
            data={
                "project_id": "p1",
                "total_missions": 5,
                "active_count": 2,
            },
            source="test",
        )
        result = handler(event)
        assert result.handled is True
        assert result.halt is False

    def test_rollup_updated_in_project_events(self):
        assert EventType.PROJECT_ROLLUP_UPDATED in PROJECT_EVENT_TYPES

    def test_project_event_types_count(self):
        assert len(PROJECT_EVENT_TYPES) == 12  # 9 original + 3 GitHub (D-151)
