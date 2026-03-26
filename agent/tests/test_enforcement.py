"""D-102 enforcement tests — Task 14.13.

10 scenarios from D-102 addendum validating the full governance pipeline.
"""
import tempfile
import shutil

import pytest

from events.bus import Event, EventBus, HandlerResult
from events.catalog import EventType
from events.handlers.audit_trail import AuditTrailHandler
from events.handlers.token_logger import TokenLoggerHandler
from events.handlers.bypass_detector import BypassDetectorHandler
from events.handlers.tool_permissions import ToolPermissionsHandler
from events.handlers.budget_enforcer import BudgetEnforcerHandler
from events.handlers.anomaly_detector import AnomalyDetectorHandler
from events.handlers.metrics_exporter import MetricsExporterHandler
from events.handlers.report_collector import ReportCollectorHandler
from events.handlers.approval_gate import ApprovalGateHandler
from events.handlers.tool_executor import ToolExecutorHandler
from events.handlers.stage_transition import StageTransitionHandler

from context.token_budget import BudgetConfig


@pytest.fixture
def full_bus():
    """Fully wired bus with all 13 handlers."""
    tmpdir = tempfile.mkdtemp()
    bus = EventBus()

    audit = AuditTrailHandler(log_dir=tmpdir)
    token_logger = TokenLoggerHandler()
    bypass = BypassDetectorHandler()
    metrics = MetricsExporterHandler()
    anomaly = AnomalyDetectorHandler(rework_threshold=2, deny_threshold=3)
    report = ReportCollectorHandler()

    bus.on_all(audit, priority=0, name="audit")
    bus.on_all(token_logger, priority=10, name="token_logger")
    bus.on_all(bypass, priority=20, name="bypass")
    bus.on_all(metrics, priority=30, name="metrics")
    bus.on_all(anomaly, priority=40, name="anomaly")
    bus.on_all(report, priority=50, name="report")

    role_tools = {
        "analyst": {"read_file", "list_directory", "ui_overview"},
        "developer": None,  # all tools
        "product-owner": set(),  # no tools
    }
    bus.on(EventType.TOOL_REQUESTED,
           ToolPermissionsHandler(get_allowed_tools=lambda r: role_tools.get(r)),
           priority=100, name="permissions")

    config = BudgetConfig(
        tool_response_limit=10_000,
        tool_response_hard_limit=50_000,
        stage_input_hard_limit=80_000,
        mission_total_limit=300_000)
    budget = BudgetEnforcerHandler(config=config)
    bus.on(EventType.TOOL_EXECUTED, budget, priority=200, name="budget")
    bus.on(EventType.STAGE_CONTEXT_READY, budget, priority=200, name="budget_stage")

    bus.on(EventType.APPROVAL_REQUESTED, ApprovalGateHandler(),
           priority=100, name="approval")

    bus.on(EventType.TOOL_CLEARED,
           ToolExecutorHandler(), priority=100, name="tool_exec")

    bus.on(EventType.STAGE_ENTERING,
           StageTransitionHandler(context_budget=40000),
           priority=100, name="stage_transition")

    yield {
        "bus": bus, "audit": audit, "token_logger": token_logger,
        "bypass": bypass, "metrics": metrics, "anomaly": anomaly,
        "report": report, "budget": budget, "tmpdir": tmpdir,
    }
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestEnforcement:

    def test_01_analyst_snapshot_blocked(self, full_bus):
        """Analyst cannot use snapshot tool."""
        bus = full_bus["bus"]
        results = bus.emit(Event(
            type=EventType.TOOL_REQUESTED,
            data={"tool": "snapshot", "role": "analyst"},
            source="runner"))
        assert bus.was_halted(results)

    def test_02_analyst_read_file_allowed(self, full_bus):
        """Analyst can use read_file."""
        bus = full_bus["bus"]
        results = bus.emit(Event(
            type=EventType.TOOL_REQUESTED,
            data={"tool": "read_file", "role": "analyst"},
            source="runner"))
        assert not bus.was_halted(results)

    def test_03_developer_all_tools_allowed(self, full_bus):
        """Developer can use any tool (None = all)."""
        bus = full_bus["bus"]
        for tool in ["snapshot", "write_file", "terminal", "read_file"]:
            results = bus.emit(Event(
                type=EventType.TOOL_REQUESTED,
                data={"tool": tool, "role": "developer"},
                source="runner"))
            assert not bus.was_halted(results), f"{tool} should be allowed for developer"

    def test_04_po_no_tools(self, full_bus):
        """Product owner has no tool access."""
        bus = full_bus["bus"]
        results = bus.emit(Event(
            type=EventType.TOOL_REQUESTED,
            data={"tool": "read_file", "role": "product-owner"},
            source="runner"))
        assert bus.was_halted(results)

    def test_05_budget_truncate_signal(self, full_bus):
        """Tool response >10K signals truncation."""
        bus = full_bus["bus"]
        results = bus.emit(Event(
            type=EventType.TOOL_EXECUTED,
            data={"tool": "read_file", "stage": "s1",
                  "response_tokens": 15000},
            source="runner"))
        # Budget handler should signal truncate (not halt)
        truncate_results = [r for r in results if r.data.get("action") == "truncate"]
        assert len(truncate_results) >= 1

    def test_06_budget_hard_block(self, full_bus):
        """Tool response >50K blocks."""
        bus = full_bus["bus"]
        results = bus.emit(Event(
            type=EventType.TOOL_EXECUTED,
            data={"tool": "snapshot", "stage": "s1",
                  "response_tokens": 60000},
            source="runner"))
        assert bus.was_halted(results)

    def test_07_stage_context_over_budget(self, full_bus):
        """Stage with >40K input tokens is blocked."""
        bus = full_bus["bus"]
        results = bus.emit(Event(
            type=EventType.STAGE_ENTERING,
            data={"stage": "dev", "specialist": "developer",
                  "input_tokens": 50000},
            source="ctrl"))
        assert bus.was_halted(results)

    def test_08_bypass_detected(self, full_bus):
        """Tool executed without clearing triggers bypass flag."""
        bus = full_bus["bus"]
        bypass = full_bus["bypass"]

        bus.emit(Event(type=EventType.TOOL_EXECUTED,
                       data={"tool": "secret_tool", "stage": "s1",
                             "response_tokens": 100},
                       source="runner", correlation_id="bypass-test"))

        assert bypass.bypass_count == 1

    def test_09_anomaly_on_excessive_denies(self, full_bus):
        """3+ tool blocks trigger anomaly."""
        bus = full_bus["bus"]
        anomaly = full_bus["anomaly"]

        for i in range(3):
            bus.emit(Event(type=EventType.TOOL_BLOCKED,
                           data={"tool": f"t{i}"}, source="s"))

        assert len(anomaly.anomalies) >= 1
        assert anomaly.anomalies[0]["type"] == "excessive_denies"

    def test_10_audit_chain_intact_after_full_flow(self, full_bus):
        """Audit trail chain hash valid after complex event sequence."""
        bus = full_bus["bus"]
        audit = full_bus["audit"]

        # Simulate a mini mission
        cid = "enforcement-test"
        bus.emit(Event(type=EventType.MISSION_STARTED,
                       data={"goal": "test"}, source="ctrl",
                       correlation_id=cid))
        bus.emit(Event(type=EventType.STAGE_ENTERING,
                       data={"stage": "analyst", "specialist": "analyst",
                             "input_tokens": 1000},
                       source="ctrl", correlation_id=cid))
        bus.emit(Event(type=EventType.TOOL_REQUESTED,
                       data={"tool": "read_file", "role": "analyst"},
                       source="runner", correlation_id=cid))
        bus.emit(Event(type=EventType.TOOL_EXECUTED,
                       data={"tool": "read_file", "stage": "analyst",
                             "response_tokens": 500},
                       source="runner", correlation_id=cid))
        bus.emit(Event(type=EventType.STAGE_COMPLETED,
                       data={"stage": "analyst"}, source="ctrl",
                       correlation_id=cid))
        bus.emit(Event(type=EventType.MISSION_COMPLETED,
                       data={"mission_id": "m1"}, source="ctrl",
                       correlation_id=cid))

        valid, count, error = audit.verify_chain()
        assert valid is True, f"Chain broken: {error}"
        assert count >= 6
