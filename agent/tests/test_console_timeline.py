"""Tests for ConsoleTimeline handler — Task 14.12."""
import io

from events.bus import Event, EventBus, HandlerResult
from events.catalog import EventType
from events.handlers.console_timeline import ConsoleTimelineHandler


class TestConsoleTimeline:

    def test_prints_events(self):
        buf = io.StringIO()
        h = ConsoleTimelineHandler(output=buf, color=False)
        h(Event(type=EventType.MISSION_STARTED,
                data={"goal": "test goal"}, source="ctrl"))
        h(Event(type=EventType.STAGE_ENTERING,
                data={"stage": "s1", "specialist": "analyst"}, source="ctrl"))
        assert len(h.lines) == 2
        assert "mission.started" in h.lines[0]
        assert "analyst" in h.lines[1]

    def test_never_halts(self):
        h = ConsoleTimelineHandler(output=io.StringIO(), color=False)
        r = h(Event(type=EventType.TOOL_BLOCKED,
                    data={"tool": "snapshot"}, source="s"))
        assert r.halt is False

    def test_tool_detail(self):
        h = ConsoleTimelineHandler(output=io.StringIO(), color=False)
        h(Event(type=EventType.TOOL_EXECUTED,
                data={"tool": "read_file", "response_tokens": 1500},
                source="s"))
        assert "read_file" in h.lines[0]
        assert "1500tok" in h.lines[0]

    def test_truncation_detail(self):
        h = ConsoleTimelineHandler(output=io.StringIO(), color=False)
        h(Event(type=EventType.TOOL_TRUNCATED,
                data={"tool": "snapshot", "original_tokens": 60000,
                      "truncated_to": 10000},
                source="s"))
        assert "60000" in h.lines[0]
        assert "10000" in h.lines[0]

    def test_elapsed_time(self):
        h = ConsoleTimelineHandler(output=io.StringIO(), color=False)
        h(Event(type=EventType.MISSION_STARTED, data={}, source="s"))
        # First event should show ~0.0s
        assert "0.0s" in h.lines[0]

    def test_works_with_bus(self):
        buf = io.StringIO()
        bus = EventBus()
        h = ConsoleTimelineHandler(output=buf, color=False)
        bus.on_all(h, priority=5, name="timeline")

        bus.emit(Event(type=EventType.STAGE_ENTERING,
                       data={"stage": "dev", "specialist": "developer"},
                       source="ctrl"))
        bus.emit(Event(type=EventType.TOOL_EXECUTED,
                       data={"tool": "write_file", "response_tokens": 200},
                       source="runner"))
        bus.emit(Event(type=EventType.STAGE_COMPLETED,
                       data={"stage": "dev", "specialist": "developer"},
                       source="ctrl"))

        assert len(h.lines) == 3
