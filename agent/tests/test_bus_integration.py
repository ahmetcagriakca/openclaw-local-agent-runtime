"""Tests for EventBus integration with AgentRunner — Task 14.11."""
import shutil
import tempfile

from events.bus import Event, EventBus
from events.catalog import EventType
from events.handlers.anomaly_detector import AnomalyDetectorHandler
from events.handlers.audit_trail import AuditTrailHandler
from events.handlers.budget_enforcer import BudgetEnforcerHandler
from events.handlers.bypass_detector import BypassDetectorHandler
from events.handlers.metrics_exporter import MetricsExporterHandler
from events.handlers.report_collector import ReportCollectorHandler
from events.handlers.token_logger import TokenLoggerHandler
from events.handlers.tool_permissions import ToolPermissionsHandler


def _create_test_bus(audit_dir, role_tools=None):
    """Create a fully wired EventBus for testing."""
    bus = EventBus()

    # Global handlers
    bus.on_all(AuditTrailHandler(log_dir=audit_dir), priority=0, name="audit")
    token_logger = TokenLoggerHandler()
    bus.on_all(token_logger, priority=10, name="token_logger")
    bus.on_all(BypassDetectorHandler(), priority=20, name="bypass")
    metrics = MetricsExporterHandler()
    bus.on_all(metrics, priority=30, name="metrics")
    bus.on_all(AnomalyDetectorHandler(), priority=40, name="anomaly")
    bus.on_all(ReportCollectorHandler(), priority=50, name="report")

    # Type-specific
    if role_tools is not None:
        bus.on(EventType.TOOL_REQUESTED,
               ToolPermissionsHandler(get_allowed_tools=lambda r: role_tools.get(r)),
               priority=100, name="permissions")

    bus.on(EventType.TOOL_EXECUTED,
           BudgetEnforcerHandler(), priority=200, name="budget")

    return bus, token_logger, metrics


class TestBusWiredEvents:
    """Test that agent runner emits correct events when bus is provided."""

    def test_stage_entering_emitted(self):
        """Bus receives stage.entering when agent starts."""
        tmpdir = tempfile.mkdtemp()
        try:
            bus, _, metrics = _create_test_bus(tmpdir)

            # Track stage.entering events
            entering_events = []
            bus.on(EventType.STAGE_ENTERING,
                   lambda e: (entering_events.append(e), HandlerResult.proceed())[1])

            from events.bus import HandlerResult
            bus.emit(Event(
                type=EventType.STAGE_ENTERING,
                data={"stage": "test-session", "specialist": "analyst",
                      "agent_id": "gpt-4o", "input_tokens": 500},
                source="agent_runner"))

            assert len(entering_events) == 1
            assert entering_events[0].data["specialist"] == "analyst"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_tool_requested_permission_deny(self):
        """Bus blocks tool.requested for unauthorized tools."""
        tmpdir = tempfile.mkdtemp()
        try:
            bus, _, metrics = _create_test_bus(
                tmpdir, role_tools={"analyst": {"read_file"}})

            results = bus.emit(Event(
                type=EventType.TOOL_REQUESTED,
                data={"tool": "snapshot", "role": "analyst"},
                source="agent_runner"))

            assert bus.was_halted(results)
            m = metrics.get_metrics()
            assert m["events_total"] >= 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_tool_executed_tracked(self):
        """Bus records tool.executed events in token logger."""
        tmpdir = tempfile.mkdtemp()
        try:
            bus, token_logger, _ = _create_test_bus(tmpdir)

            bus.emit(Event(
                type=EventType.TOOL_EXECUTED,
                data={"tool": "read_file", "stage": "s1",
                      "request_tokens": 50, "response_tokens": 1500},
                source="agent_runner"))

            assert token_logger.stage_tokens.get("s1") == 1500
            report = token_logger.get_report()
            assert report["total_tool_calls"] == 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_stage_completed_in_report(self):
        """ReportCollector captures stage.completed data."""
        tmpdir = tempfile.mkdtemp()
        try:
            bus, _, _ = _create_test_bus(tmpdir)

            # Find report handler
            report_handler = None
            for _, name, handler in bus._global_handlers:
                if name == "report":
                    report_handler = handler
                    break

            bus.emit(Event(
                type=EventType.STAGE_COMPLETED,
                data={"stage": "analyst", "specialist": "analyst",
                      "artifact_tokens": 800, "tool_calls": 2,
                      "duration_ms": 3000, "policy_denies": 1},
                source="agent_runner"))

            assert len(report_handler.stages) == 1
            assert report_handler.stages[0]["specialist"] == "analyst"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_audit_trail_integrity(self):
        """Audit trail chain hash intact after multiple events."""
        tmpdir = tempfile.mkdtemp()
        try:
            bus, _, _ = _create_test_bus(tmpdir)

            # Simulate a mini mission flow
            bus.emit(Event(type=EventType.STAGE_ENTERING,
                          data={"stage": "s1"}, source="ctrl"))
            bus.emit(Event(type=EventType.TOOL_EXECUTED,
                          data={"tool": "t1", "stage": "s1",
                                "response_tokens": 100},
                          source="runner"))
            bus.emit(Event(type=EventType.STAGE_COMPLETED,
                          data={"stage": "s1"}, source="ctrl"))

            # Verify chain
            audit = None
            for _, name, handler in bus._global_handlers:
                if name == "audit":
                    audit = handler
                    break

            valid, count, error = audit.verify_chain()
            assert valid is True
            assert count == 3
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_full_pipeline_flow(self):
        """Simulate a complete tool request → clear → execute → complete flow."""
        tmpdir = tempfile.mkdtemp()
        try:
            bus, token_logger, metrics = _create_test_bus(
                tmpdir, role_tools={"developer": None})  # all tools allowed

            cid = "test-flow-001"

            # 1. Stage entering
            bus.emit(Event(type=EventType.STAGE_ENTERING,
                          data={"stage": "dev", "specialist": "developer",
                                "input_tokens": 3000},
                          source="ctrl", correlation_id=cid))

            # 2. Tool requested (should pass — developer has all tools)
            results = bus.emit(Event(
                type=EventType.TOOL_REQUESTED,
                data={"tool": "read_file", "role": "developer"},
                source="runner", correlation_id=cid))
            assert not bus.was_halted(results)

            # 3. Tool executed
            bus.emit(Event(type=EventType.TOOL_EXECUTED,
                          data={"tool": "read_file", "stage": "dev",
                                "request_tokens": 30, "response_tokens": 500},
                          source="runner", correlation_id=cid))

            # 4. Stage completed
            bus.emit(Event(type=EventType.STAGE_COMPLETED,
                          data={"stage": "dev", "specialist": "developer",
                                "artifact_tokens": 200, "tool_calls": 1},
                          source="ctrl", correlation_id=cid))

            # Verify metrics
            m = metrics.get_metrics()
            assert m["tools_executed"] >= 1
            assert m["stages_completed"] >= 1

            # Verify token tracking
            assert token_logger.stage_tokens.get("dev") == 500

            # Verify history
            h = bus.history(correlation_id=cid)
            assert len(h) == 4

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
