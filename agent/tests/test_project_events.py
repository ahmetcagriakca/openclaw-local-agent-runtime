"""Tests for Project EventBus events — D-144 §9.

Task 73.13: 5 event types emitted with correct payload.
"""
import pytest

from events.bus import Event
from events.catalog import EventType
from events.handlers.project_handler import PROJECT_EVENT_TYPES, ProjectHandler


@pytest.fixture
def handler():
    return ProjectHandler()


class TestProjectEventTypes:
    """Verify 5 project event types exist in catalog."""

    def test_project_created_exists(self):
        assert EventType.PROJECT_CREATED == "project.created"

    def test_project_status_changed_exists(self):
        assert EventType.PROJECT_STATUS_CHANGED == "project.status_changed"

    def test_project_mission_linked_exists(self):
        assert EventType.PROJECT_MISSION_LINKED == "project.mission_linked"

    def test_project_mission_unlinked_exists(self):
        assert EventType.PROJECT_MISSION_UNLINKED == "project.mission_unlinked"

    def test_project_deleted_exists(self):
        assert EventType.PROJECT_DELETED == "project.deleted"

    def test_all_in_catalog(self):
        all_types = EventType.all_types()
        for et in PROJECT_EVENT_TYPES:
            assert et in all_types

    def test_project_namespace(self):
        project_types = EventType.namespace("project")
        assert len(project_types) == 9  # 5 D-144 + 3 D-145 + 1 rollup (Faz 2B)


class TestProjectHandler:
    """Verify handler processes all 5 event types."""

    def test_handles_project_created(self, handler):
        event = Event(
            type=EventType.PROJECT_CREATED,
            data={"project_id": "proj_abc", "name": "Test", "owner": "op"},
            source="test",
        )
        result = handler(event)
        assert result.handled is True
        assert result.halt is False

    def test_handles_status_changed(self, handler):
        event = Event(
            type=EventType.PROJECT_STATUS_CHANGED,
            data={
                "project_id": "proj_abc",
                "old_status": "draft",
                "new_status": "active",
                "actor": "operator",
            },
            source="test",
        )
        result = handler(event)
        assert result.handled is True

    def test_handles_mission_linked(self, handler):
        event = Event(
            type=EventType.PROJECT_MISSION_LINKED,
            data={"project_id": "proj_abc", "mission_id": "mis-1"},
            source="test",
        )
        result = handler(event)
        assert result.handled is True

    def test_handles_mission_unlinked(self, handler):
        event = Event(
            type=EventType.PROJECT_MISSION_UNLINKED,
            data={"project_id": "proj_abc", "mission_id": "mis-1"},
            source="test",
        )
        result = handler(event)
        assert result.handled is True

    def test_handles_project_deleted(self, handler):
        event = Event(
            type=EventType.PROJECT_DELETED,
            data={
                "project_id": "proj_abc",
                "deleted_at": "2026-04-06T10:00:00Z",
                "actor": "operator",
            },
            source="test",
        )
        result = handler(event)
        assert result.handled is True

    def test_skips_non_project_event(self, handler):
        event = Event(
            type=EventType.MISSION_STARTED,
            data={"mission_id": "mis-1"},
            source="test",
        )
        result = handler(event)
        assert result.handled is False

    def test_never_halts(self, handler):
        for event_type in PROJECT_EVENT_TYPES:
            event = Event(
                type=event_type,
                data={"project_id": "proj_test"},
                source="test",
            )
            result = handler(event)
            assert result.halt is False
