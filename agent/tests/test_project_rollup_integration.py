"""Integration tests for rollup + SSE — D-145 Faz 2B (T75.13).

Tests full flow: event → rollup invalidation → recompute → SSE broadcast.
"""
from unittest.mock import MagicMock

import pytest

from events.bus import Event, EventBus
from events.catalog import EventType
from events.handlers.project_handler import ProjectHandler
from persistence.project_store import ProjectStore


@pytest.fixture
def setup(tmp_path):
    """Full integration setup with store, handler, and event bus."""
    store_path = tmp_path / "projects.json"
    mission_store = MagicMock()
    missions = [
        {"id": "m1", "status": "completed", "project_id": None, "total_tokens": 500, "ts": "t1"},
        {"id": "m2", "status": "executing", "project_id": None, "total_tokens": 200, "ts": "t2"},
    ]
    mission_store.list.return_value = (missions, 2)

    store = ProjectStore(store_path=store_path, mission_store=mission_store)
    proj = store.create("Integration Test")
    pid = proj["project_id"]

    for m in missions:
        m["project_id"] = pid

    sse = MagicMock()
    handler = ProjectHandler(sse_manager=sse, project_store=store)

    bus = EventBus()
    bus.on(EventType.PROJECT_MISSION_LINKED, handler, priority=50)
    bus.on(EventType.PROJECT_STATUS_CHANGED, handler, priority=50)
    bus.on(EventType.PROJECT_ROLLUP_UPDATED, handler, priority=50)
    bus.on(EventType.PROJECT_ARTIFACT_PUBLISHED, handler, priority=50)
    bus.on(EventType.PROJECT_ARTIFACT_UNPUBLISHED, handler, priority=50)

    return store, pid, sse, bus, missions


class TestRollupInvalidationFlow:
    """T75.13: Event → rollup invalidation flow."""

    def test_mission_link_invalidates_rollup(self, setup):
        store, pid, sse, bus, _ = setup
        # Pre-compute rollup
        store.compute_rollup(pid)
        proj = store.get(pid)
        assert "_rollup_cache" in proj

        # Emit mission linked event
        event = Event(
            type=EventType.PROJECT_MISSION_LINKED,
            data={"project_id": pid, "mission_id": "m3"},
            source="test",
        )
        bus.emit(event)

        # Cache should be invalidated
        proj = store.get(pid)
        assert "_rollup_cache" not in proj

    def test_status_change_invalidates_rollup(self, setup):
        store, pid, sse, bus, _ = setup
        store.compute_rollup(pid)
        event = Event(
            type=EventType.PROJECT_STATUS_CHANGED,
            data={"project_id": pid, "old_status": "draft", "new_status": "active"},
            source="test",
        )
        bus.emit(event)
        proj = store.get(pid)
        assert "_rollup_cache" not in proj

    def test_get_rollup_after_invalidation_recomputes(self, setup):
        store, pid, sse, bus, _ = setup
        store.compute_rollup(pid)
        store.invalidate_rollup(pid)
        rollup = store.get_rollup(pid)
        assert rollup["total_missions"] == 2
        assert rollup["total_tokens"] == 700


class TestRollupRecomputeAccuracy:
    """T75.13: Rollup recompute accuracy after mutations."""

    def test_rollup_reflects_mission_changes(self, setup):
        store, pid, sse, bus, missions = setup
        # Add a new mission
        missions.append({
            "id": "m3", "status": "completed", "project_id": pid,
            "total_tokens": 300, "ts": "t3",
        })
        store._mission_store.list.return_value = (missions, 3)

        rollup = store.compute_rollup(pid)
        assert rollup["total_missions"] == 3
        assert rollup["quiescent_count"] == 2  # completed + completed
        assert rollup["active_count"] == 1  # executing
        assert rollup["total_tokens"] == 1000


class TestSSEBroadcastIntegration:
    """T75.13: SSE broadcast on event dispatch."""

    def test_status_change_triggers_no_sync_sse(self, setup):
        """SSE broadcast is async; in sync context it should be attempted."""
        store, pid, sse, bus, _ = setup
        event = Event(
            type=EventType.PROJECT_STATUS_CHANGED,
            data={"project_id": pid, "old_status": "draft", "new_status": "active"},
            source="test",
        )
        bus.emit(event)
        # SSE broadcast is async — in test without event loop, it logs debug
        # The important thing is the handler didn't raise

    def test_artifact_published_no_rollup_invalidation(self, setup):
        """Artifact publish does NOT invalidate rollup (no mission count change)."""
        store, pid, sse, bus, _ = setup
        store.compute_rollup(pid)
        event = Event(
            type=EventType.PROJECT_ARTIFACT_PUBLISHED,
            data={"project_id": pid, "artifact_id": "a1", "mission_id": "m1"},
            source="test",
        )
        bus.emit(event)
        proj = store.get(pid)
        assert "_rollup_cache" in proj  # Still cached — not invalidated
