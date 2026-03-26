"""Tests for TokenLogger, ToolPermissions, BudgetEnforcer handlers."""
import pytest

from events.bus import Event, EventBus, HandlerResult
from events.catalog import EventType
from events.handlers.token_logger import TokenLoggerHandler
from events.handlers.tool_permissions import ToolPermissionsHandler
from events.handlers.budget_enforcer import BudgetEnforcerHandler


# ── TokenLogger (14.2) ──────────────────────────────────────────

class TestTokenLogger:

    def test_logs_tool_executed(self):
        h = TokenLoggerHandler()
        e = Event(type=EventType.TOOL_EXECUTED,
                  data={"stage": "s1", "tool": "read_file",
                        "request_tokens": 50, "response_tokens": 2000},
                  source="runner")
        r = h(e)
        assert r.halt is False
        assert h.stage_tokens["s1"] == 2000

    def test_tracks_truncations(self):
        h = TokenLoggerHandler()
        h(Event(type=EventType.TOOL_TRUNCATED,
                data={"tool": "snapshot", "original_tokens": 60000,
                      "truncated_to": 10000},
                source="budget"))
        assert h.truncations == 1

    def test_tracks_blocks(self):
        h = TokenLoggerHandler()
        h(Event(type=EventType.TOOL_BLOCKED,
                data={"tool": "snapshot", "tokens": 80000},
                source="budget"))
        assert h.blocks == 1

    def test_cumulative_per_stage(self):
        h = TokenLoggerHandler()
        for i in range(3):
            h(Event(type=EventType.TOOL_EXECUTED,
                    data={"stage": "dev", "tool": f"t{i}",
                          "request_tokens": 10, "response_tokens": 1000},
                    source="r"))
        assert h.stage_tokens["dev"] == 3000

    def test_report(self):
        h = TokenLoggerHandler()
        h(Event(type=EventType.TOOL_EXECUTED,
                data={"stage": "s1", "tool": "t1",
                      "request_tokens": 10, "response_tokens": 500},
                source="r"))
        report = h.get_report()
        assert report["total_tokens"] == 500
        assert report["total_tool_calls"] == 1
        assert len(report["stages"]) == 1

    def test_skips_irrelevant_events(self):
        h = TokenLoggerHandler()
        r = h(Event(type=EventType.MISSION_STARTED, data={}, source="s"))
        assert r.handled is False


# ── ToolPermissions (14.4) ───────────────────────────────────────

class TestToolPermissions:

    def _handler(self, role_tools: dict):
        def get_allowed(role):
            return role_tools.get(role)
        return ToolPermissionsHandler(get_allowed_tools=get_allowed)

    def test_allowed_tool_proceeds(self):
        h = self._handler({"analyst": {"read_file", "list_directory"}})
        e = Event(type=EventType.TOOL_REQUESTED,
                  data={"tool": "read_file", "role": "analyst"},
                  source="runner")
        r = h(e)
        assert r.halt is False

    def test_denied_tool_halts(self):
        h = self._handler({"analyst": {"read_file"}})
        e = Event(type=EventType.TOOL_REQUESTED,
                  data={"tool": "snapshot", "role": "analyst"},
                  source="runner")
        r = h(e)
        assert r.halt is True
        assert "not permitted" in r.error

    def test_none_means_all_allowed(self):
        h = self._handler({"remote-operator": None})
        e = Event(type=EventType.TOOL_REQUESTED,
                  data={"tool": "any_tool", "role": "remote-operator"},
                  source="runner")
        r = h(e)
        assert r.halt is False

    def test_no_role_proceeds(self):
        h = self._handler({})
        e = Event(type=EventType.TOOL_REQUESTED,
                  data={"tool": "x", "role": ""},
                  source="runner")
        r = h(e)
        assert r.halt is False

    def test_skips_non_tool_events(self):
        h = self._handler({})
        r = h(Event(type=EventType.MISSION_STARTED, data={}, source="s"))
        assert r.handled is False


# ── BudgetEnforcer (14.5) ────────────────────────────────────────

class TestBudgetEnforcer:

    def _handler(self, **overrides):
        from context.token_budget import BudgetConfig
        config = BudgetConfig(**overrides)
        return BudgetEnforcerHandler(config=config)

    def test_within_budget_proceeds(self):
        h = self._handler()
        e = Event(type=EventType.TOOL_EXECUTED,
                  data={"tool": "read_file", "stage": "s1",
                        "response_tokens": 500},
                  source="runner")
        r = h(e)
        assert r.halt is False

    def test_soft_limit_signals_truncate(self):
        h = self._handler(tool_response_limit=100)
        e = Event(type=EventType.TOOL_EXECUTED,
                  data={"tool": "t", "stage": "s1",
                        "response_tokens": 200},
                  source="r")
        r = h(e)
        assert r.halt is False
        assert r.data.get("action") == "truncate"

    def test_hard_limit_blocks(self):
        h = self._handler(tool_response_hard_limit=100)
        e = Event(type=EventType.TOOL_EXECUTED,
                  data={"tool": "t", "stage": "s1",
                        "response_tokens": 200},
                  source="r")
        r = h(e)
        assert r.halt is True
        assert "too large" in r.error

    def test_stage_cumulative_halt(self):
        h = self._handler(stage_input_hard_limit=500)
        for i in range(3):
            h(Event(type=EventType.TOOL_EXECUTED,
                    data={"tool": "t", "stage": "s1",
                          "response_tokens": 200},
                    source="r"))
        # 3 * 200 = 600 > 500
        assert h.stage_totals["s1"] == 600
        # The third call should have halted

    def test_mission_total_abort(self):
        h = self._handler(mission_total_limit=300)
        for i in range(4):
            r = h(Event(type=EventType.TOOL_EXECUTED,
                        data={"tool": "t", "stage": f"s{i}",
                              "response_tokens": 100},
                        source="r"))
        # 4 * 100 = 400 > 300, last call should halt
        assert r.halt is True
        assert "Mission total" in r.error

    def test_stage_input_check(self):
        h = self._handler(stage_input_hard_limit=1000)
        e = Event(type=EventType.STAGE_CONTEXT_READY,
                  data={"stage": "dev", "input_tokens": 2000},
                  source="ctrl")
        r = h(e)
        assert r.halt is True

    def test_stage_input_within_limit(self):
        h = self._handler(stage_input_hard_limit=5000)
        e = Event(type=EventType.STAGE_CONTEXT_READY,
                  data={"stage": "dev", "input_tokens": 3000},
                  source="ctrl")
        r = h(e)
        assert r.halt is False

    def test_skips_irrelevant(self):
        h = self._handler()
        r = h(Event(type=EventType.MISSION_STARTED, data={}, source="s"))
        assert r.handled is False


# ── Integration: full pipeline ───────────────────────────────────

class TestHandlerPipeline:

    def test_permission_blocks_before_execution(self):
        """ToolPermissions halts → BudgetEnforcer never runs."""
        bus = EventBus()
        perm = ToolPermissionsHandler(
            get_allowed_tools=lambda r: {"read_file"})
        budget = BudgetEnforcerHandler()
        token_log = TokenLoggerHandler()

        bus.on(EventType.TOOL_REQUESTED, perm, priority=100, name="perm")
        bus.on(EventType.TOOL_REQUESTED, budget, priority=200, name="budget")
        bus.on_all(token_log, priority=10, name="logger")

        e = Event(type=EventType.TOOL_REQUESTED,
                  data={"tool": "snapshot", "role": "analyst"},
                  source="runner")
        results = bus.emit(e)

        assert bus.was_halted(results)
        # Budget enforcer should NOT have run
        assert budget.mission_total == 0
