"""Tests for D-102 EventBus core — Task 14.0."""
import pytest

from events.bus import Event, EventBus, HandlerResult
from events.catalog import EventType
from events.correlation import get_correlation_id, new_correlation_id, set_correlation_id


class TestEvent:

    def test_frozen(self):
        e = Event(type="test.event", data={"k": "v"}, source="test")
        with pytest.raises(AttributeError):
            e.type = "mutated"

    def test_auto_correlation_id(self):
        e = Event(type="t", data={}, source="s")
        assert len(e.correlation_id) == 12

    def test_auto_timestamp(self):
        e = Event(type="t", data={}, source="s")
        assert e.ts is not None

    def test_child_shares_correlation(self):
        parent = Event(type="a", data={}, source="s")
        child = parent.child("b", {"x": 1}, "s2")
        assert child.correlation_id == parent.correlation_id
        assert child.parent_id == parent.correlation_id
        assert child.type == "b"
        assert child.data == {"x": 1}


class TestHandlerResult:

    def test_proceed(self):
        r = HandlerResult.proceed(key="val")
        assert r.handled is True
        assert r.halt is False
        assert r.data == {"key": "val"}

    def test_block(self):
        r = HandlerResult.block("denied")
        assert r.halt is True
        assert r.error == "denied"

    def test_skip(self):
        r = HandlerResult.skip()
        assert r.handled is False
        assert r.halt is False


class TestEventBus:

    def test_emit_no_handlers(self):
        bus = EventBus()
        e = Event(type="test", data={}, source="s")
        results = bus.emit(e)
        assert results == []

    def test_handler_receives_event(self):
        bus = EventBus()
        received = []
        bus.on("test.ping", lambda e: (received.append(e), HandlerResult.proceed())[1])
        e = Event(type="test.ping", data={"msg": "hi"}, source="s")
        bus.emit(e)
        assert len(received) == 1
        assert received[0].data["msg"] == "hi"

    def test_handler_priority_order(self):
        bus = EventBus()
        order = []
        bus.on("t", lambda e: (order.append("B"), HandlerResult.proceed())[1],
               priority=200, name="B")
        bus.on("t", lambda e: (order.append("A"), HandlerResult.proceed())[1],
               priority=100, name="A")
        bus.emit(Event(type="t", data={}, source="s"))
        assert order == ["A", "B"]

    def test_halt_stops_propagation(self):
        bus = EventBus()
        order = []
        bus.on("t", lambda e: (order.append("A"), HandlerResult.block("stop"))[1],
               priority=100, name="A")
        bus.on("t", lambda e: (order.append("B"), HandlerResult.proceed())[1],
               priority=200, name="B")
        results = bus.emit(Event(type="t", data={}, source="s"))
        assert order == ["A"]  # B never ran
        assert bus.was_halted(results) is True

    def test_global_handler_runs_for_all(self):
        bus = EventBus()
        seen = []
        bus.on_all(lambda e: (seen.append(e.type), HandlerResult.proceed())[1],
                   name="logger")
        bus.emit(Event(type="a", data={}, source="s"))
        bus.emit(Event(type="b", data={}, source="s"))
        assert seen == ["a", "b"]

    def test_global_runs_before_specific(self):
        bus = EventBus()
        order = []
        bus.on("t", lambda e: (order.append("specific"), HandlerResult.proceed())[1])
        bus.on_all(lambda e: (order.append("global"), HandlerResult.proceed())[1])
        bus.emit(Event(type="t", data={}, source="s"))
        assert order == ["global", "specific"]

    def test_handler_error_doesnt_crash_bus(self):
        bus = EventBus()
        def bad_handler(e):
            raise RuntimeError("boom")
        bus.on("t", bad_handler, name="bad")
        results = bus.emit(Event(type="t", data={}, source="s"))
        assert len(results) == 1
        assert "error" in results[0].error

    def test_history(self):
        bus = EventBus()
        bus.on("t", lambda e: HandlerResult.proceed())
        bus.emit(Event(type="t", data={"i": 1}, source="s"))
        bus.emit(Event(type="t", data={"i": 2}, source="s"))
        h = bus.history()
        assert len(h) == 2

    def test_history_filter_by_type(self):
        bus = EventBus()
        bus.on("a", lambda e: HandlerResult.proceed())
        bus.on("b", lambda e: HandlerResult.proceed())
        bus.emit(Event(type="a", data={}, source="s"))
        bus.emit(Event(type="b", data={}, source="s"))
        assert len(bus.history(event_type="a")) == 1

    def test_history_filter_by_correlation(self):
        bus = EventBus()
        bus.on("t", lambda e: HandlerResult.proceed())
        e1 = Event(type="t", data={}, source="s", correlation_id="abc")
        e2 = Event(type="t", data={}, source="s", correlation_id="xyz")
        bus.emit(e1)
        bus.emit(e2)
        assert len(bus.history(correlation_id="abc")) == 1

    def test_handler_count(self):
        bus = EventBus()
        bus.on("a", lambda e: HandlerResult.proceed())
        bus.on("b", lambda e: HandlerResult.proceed())
        bus.on_all(lambda e: HandlerResult.proceed())
        assert bus.handler_count == 3

    def test_registered_types(self):
        bus = EventBus()
        bus.on("z.event", lambda e: HandlerResult.proceed())
        bus.on("a.event", lambda e: HandlerResult.proceed())
        assert bus.registered_types() == ["a.event", "z.event"]

    def test_clear(self):
        bus = EventBus()
        bus.on("t", lambda e: HandlerResult.proceed())
        bus.emit(Event(type="t", data={}, source="s"))
        bus.clear()
        assert bus.handler_count == 0
        assert len(bus.history()) == 0

    def test_was_halted_false(self):
        results = [HandlerResult.proceed(), HandlerResult.proceed()]
        assert EventBus().was_halted(results) is False

    def test_was_halted_true(self):
        results = [HandlerResult.proceed(), HandlerResult.block("x")]
        assert EventBus().was_halted(results) is True


class TestEventCatalog:

    def test_has_33_types(self):
        all_types = EventType.all_types()
        assert len(all_types) == 36  # 28 original + 5 project (D-144) + 3 workspace/artifact (D-145)

    def test_namespace_mission(self):
        ns = EventType.namespace("mission")
        assert "mission.started" in ns
        assert "mission.completed" in ns
        assert len(ns) == 4

    def test_namespace_tool(self):
        ns = EventType.namespace("tool")
        assert len(ns) == 5

    def test_namespace_gate(self):
        ns = EventType.namespace("gate")
        assert len(ns) == 4

    def test_all_types_are_strings(self):
        for t in EventType.all_types():
            assert isinstance(t, str)
            assert "." in t


class TestCorrelation:

    def test_new_id_generated(self):
        cid = new_correlation_id()
        assert len(cid) == 12
        assert get_correlation_id() == cid

    def test_set_id(self):
        set_correlation_id("custom123456")
        assert get_correlation_id() == "custom123456"

    def test_new_overwrites_old(self):
        cid1 = new_correlation_id()
        cid2 = new_correlation_id()
        assert cid1 != cid2
        assert get_correlation_id() == cid2
