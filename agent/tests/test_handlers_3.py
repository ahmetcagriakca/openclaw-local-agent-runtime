"""Tests for ApprovalGate, ToolExecutor, LLMExecutor, StageTransition."""
import pytest

from events.bus import Event, EventBus, HandlerResult
from events.catalog import EventType
from events.handlers.approval_gate import ApprovalGateHandler
from events.handlers.tool_executor import ToolExecutorHandler
from events.handlers.llm_executor import LLMExecutorHandler
from events.handlers.stage_transition import StageTransitionHandler, ContextAssemblerHandler


# ── ApprovalGate (14.6) ─────────────────────────────────────────

class TestApprovalGate:

    def test_requested_halts(self):
        h = ApprovalGateHandler()
        e = Event(type=EventType.APPROVAL_REQUESTED,
                  data={"approval_id": "a1", "tool": "rm_file",
                        "role": "developer", "risk": "high"},
                  source="risk")
        r = h(e)
        assert r.halt is True
        assert h.is_pending("a1")

    def test_granted_proceeds(self):
        h = ApprovalGateHandler()
        h(Event(type=EventType.APPROVAL_REQUESTED,
                data={"approval_id": "a1"}, source="s"))
        r = h(Event(type=EventType.APPROVAL_GRANTED,
                     data={"approval_id": "a1"}, source="op"))
        assert r.halt is False
        assert not h.is_pending("a1")
        assert h.get_decision("a1") == "granted"

    def test_denied_halts(self):
        h = ApprovalGateHandler()
        h(Event(type=EventType.APPROVAL_REQUESTED,
                data={"approval_id": "a1"}, source="s"))
        r = h(Event(type=EventType.APPROVAL_DENIED,
                     data={"approval_id": "a1"}, source="op"))
        assert r.halt is True
        assert h.get_decision("a1") == "denied"

    def test_skips_irrelevant(self):
        h = ApprovalGateHandler()
        r = h(Event(type=EventType.TOOL_EXECUTED, data={}, source="s"))
        assert r.handled is False


# ── ToolExecutor (14.7) ─────────────────────────────────────────

class TestToolExecutor:

    def test_stub_execution(self):
        h = ToolExecutorHandler()
        e = Event(type=EventType.TOOL_CLEARED,
                  data={"tool": "read_file", "params": {"path": "/tmp"},
                        "stage": "analyst"},
                  source="perm")
        r = h(e)
        assert r.halt is False
        assert "stub" in r.data["output"]
        assert len(h.executions) == 1

    def test_real_execution(self):
        def mock_exec(tool, params):
            return {"success": True, "output": f"ran {tool}"}
        h = ToolExecutorHandler(execute_fn=mock_exec)
        e = Event(type=EventType.TOOL_CLEARED,
                  data={"tool": "list_dir", "params": {}, "stage": "s1"},
                  source="perm")
        r = h(e)
        assert r.data["success"] is True
        assert "ran list_dir" in r.data["output"]

    def test_execution_error_handled(self):
        def fail_exec(tool, params):
            raise RuntimeError("MCP down")
        h = ToolExecutorHandler(execute_fn=fail_exec)
        e = Event(type=EventType.TOOL_CLEARED,
                  data={"tool": "t", "params": {}, "stage": "s"},
                  source="p")
        r = h(e)
        assert r.data["success"] is False

    def test_skips_non_cleared(self):
        h = ToolExecutorHandler()
        r = h(Event(type=EventType.TOOL_REQUESTED, data={}, source="s"))
        assert r.handled is False


# ── LLMExecutor (14.8) ──────────────────────────────────────────

class TestLLMExecutor:

    def test_stub_call(self):
        h = LLMExecutorHandler()
        e = Event(type=EventType.LLM_REQUESTED,
                  data={"agent_id": "gpt-4o", "stage": "analyst",
                        "input_tokens": 3000},
                  source="ctrl")
        r = h(e)
        assert r.halt is False
        assert "stub" in r.data["response"]
        assert len(h.calls) == 1

    def test_real_call(self):
        def mock_llm(agent_id, messages, tools):
            return {"response": "analysis done", "output_tokens": 500}
        h = LLMExecutorHandler(call_fn=mock_llm)
        e = Event(type=EventType.LLM_REQUESTED,
                  data={"agent_id": "claude", "stage": "s1",
                        "messages": [], "tools": []},
                  source="ctrl")
        r = h(e)
        assert r.data["response"] == "analysis done"
        assert r.data["output_tokens"] == 500

    def test_call_error(self):
        def fail_llm(agent_id, messages, tools):
            raise RuntimeError("rate limit")
        h = LLMExecutorHandler(call_fn=fail_llm)
        r = h(Event(type=EventType.LLM_REQUESTED,
                     data={"agent_id": "x", "stage": "s"}, source="c"))
        assert r.data["success"] is False

    def test_skips_non_llm(self):
        h = LLMExecutorHandler()
        r = h(Event(type=EventType.TOOL_EXECUTED, data={}, source="s"))
        assert r.handled is False


# ── StageTransition (14.10) ─────────────────────────────────────

class TestStageTransition:

    def test_within_budget_proceeds(self):
        h = StageTransitionHandler(context_budget=50000)
        e = Event(type=EventType.STAGE_ENTERING,
                  data={"stage": "dev", "specialist": "developer",
                        "input_tokens": 5000},
                  source="ctrl")
        r = h(e)
        assert r.halt is False

    def test_over_budget_halts(self):
        h = StageTransitionHandler(context_budget=10000)
        e = Event(type=EventType.STAGE_ENTERING,
                  data={"stage": "dev", "specialist": "developer",
                        "input_tokens": 50000},
                  source="ctrl")
        r = h(e)
        assert r.halt is True
        assert "exceeds budget" in r.error

    def test_skips_non_stage(self):
        h = StageTransitionHandler()
        r = h(Event(type=EventType.TOOL_EXECUTED, data={}, source="s"))
        assert r.handled is False


class TestContextAssemblerHandler:

    def test_no_assembler_returns_empty(self):
        h = ContextAssemblerHandler()
        e = Event(type=EventType.STAGE_ENTERING,
                  data={"stage": "s1", "role": "analyst",
                        "artifact_ids": ["a1"]},
                  source="ctrl")
        r = h(e)
        assert r.data.get("context") == ""

    def test_no_artifacts_returns_empty(self):
        h = ContextAssemblerHandler()
        e = Event(type=EventType.STAGE_ENTERING,
                  data={"stage": "s1", "role": "analyst",
                        "artifact_ids": []},
                  source="ctrl")
        r = h(e)
        assert r.data.get("context") == ""

    def test_skips_non_stage(self):
        h = ContextAssemblerHandler()
        r = h(Event(type=EventType.TOOL_EXECUTED, data={}, source="s"))
        assert r.handled is False


# ── Full pipeline integration ────────────────────────────────────

class TestFullPipeline:

    def test_13_handlers_registered(self):
        """All 13 handlers can be registered on a single bus."""
        from events.handlers.audit_trail import AuditTrailHandler
        from events.handlers.token_logger import TokenLoggerHandler
        from events.handlers.bypass_detector import BypassDetectorHandler
        from events.handlers.tool_permissions import ToolPermissionsHandler
        from events.handlers.budget_enforcer import BudgetEnforcerHandler
        from events.handlers.report_collector import ReportCollectorHandler
        from events.handlers.anomaly_detector import AnomalyDetectorHandler
        from events.handlers.metrics_exporter import MetricsExporterHandler
        import tempfile, shutil

        tmpdir = tempfile.mkdtemp()
        try:
            bus = EventBus()

            # Global handlers (see everything)
            bus.on_all(AuditTrailHandler(log_dir=tmpdir), priority=0, name="audit")
            bus.on_all(TokenLoggerHandler(), priority=10, name="token_logger")
            bus.on_all(BypassDetectorHandler(), priority=20, name="bypass")
            bus.on_all(MetricsExporterHandler(), priority=30, name="metrics")
            bus.on_all(AnomalyDetectorHandler(), priority=40, name="anomaly")
            bus.on_all(ReportCollectorHandler(), priority=50, name="report")

            # Event-specific handlers
            bus.on(EventType.TOOL_REQUESTED, ToolPermissionsHandler(
                get_allowed_tools=lambda r: {"read_file", "list_directory"}),
                priority=100, name="permissions")
            bus.on(EventType.TOOL_REQUESTED, BudgetEnforcerHandler(),
                priority=200, name="budget")
            bus.on(EventType.APPROVAL_REQUESTED, ApprovalGateHandler(),
                priority=100, name="approval")
            bus.on(EventType.TOOL_CLEARED, ToolExecutorHandler(),
                priority=100, name="tool_exec")
            bus.on(EventType.LLM_REQUESTED, LLMExecutorHandler(),
                priority=100, name="llm_exec")
            bus.on(EventType.STAGE_ENTERING, StageTransitionHandler(),
                priority=100, name="stage_transition")
            bus.on(EventType.STAGE_ENTERING, ContextAssemblerHandler(),
                priority=200, name="context_assembler")

            assert bus.handler_count == 13

            # Smoke test: emit allowed tool request
            results = bus.emit(Event(
                type=EventType.TOOL_REQUESTED,
                data={"tool": "read_file", "role": "analyst"},
                source="test"))
            assert not bus.was_halted(results)

            # Smoke test: emit denied tool request
            results = bus.emit(Event(
                type=EventType.TOOL_REQUESTED,
                data={"tool": "snapshot", "role": "analyst"},
                source="test"))
            assert bus.was_halted(results)

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
