"""Tests for BypassDetector, ReportCollector, AnomalyDetector, MetricsExporter."""

from events.bus import Event
from events.catalog import EventType
from events.handlers.anomaly_detector import AnomalyDetectorHandler
from events.handlers.bypass_detector import BypassDetectorHandler
from events.handlers.metrics_exporter import MetricsExporterHandler
from events.handlers.report_collector import ReportCollectorHandler

# ── BypassDetector (14.3) ────────────────────────────────────────

class TestBypassDetector:

    def test_cleared_then_executed_ok(self):
        h = BypassDetectorHandler()
        cid = "abc123"
        h(Event(type=EventType.TOOL_CLEARED,
                data={"tool": "read_file"}, source="perm",
                correlation_id=cid))
        r = h(Event(type=EventType.TOOL_EXECUTED,
                     data={"tool": "read_file"}, source="runner",
                     correlation_id=cid))
        assert h.bypass_count == 0
        assert r.data.get("bypass_detected") is None

    def test_executed_without_cleared_is_bypass(self):
        h = BypassDetectorHandler()
        r = h(Event(type=EventType.TOOL_EXECUTED,
                     data={"tool": "snapshot"}, source="runner",
                     correlation_id="xyz"))
        assert h.bypass_count == 1
        assert r.data.get("bypass_detected") is True

    def test_different_tool_is_bypass(self):
        h = BypassDetectorHandler()
        h(Event(type=EventType.TOOL_CLEARED,
                data={"tool": "read_file"}, source="perm",
                correlation_id="abc"))
        h(Event(type=EventType.TOOL_EXECUTED,
                     data={"tool": "write_file"}, source="runner",
                     correlation_id="abc"))
        assert h.bypass_count == 1

    def test_skips_irrelevant(self):
        h = BypassDetectorHandler()
        r = h(Event(type=EventType.MISSION_STARTED, data={}, source="s"))
        assert r.handled is False

    def test_bypass_log_recorded(self):
        h = BypassDetectorHandler()
        h(Event(type=EventType.TOOL_EXECUTED,
                data={"tool": "t1"}, source="s", correlation_id="c1"))
        assert len(h.bypass_log) == 1
        assert h.bypass_log[0]["tool"] == "t1"


# ── ReportCollector (14.9) ───────────────────────────────────────

class TestReportCollector:

    def test_collects_stage_data(self):
        h = ReportCollectorHandler()
        h(Event(type=EventType.STAGE_COMPLETED,
                data={"stage": "s1", "specialist": "analyst",
                      "artifact_tokens": 500, "tool_calls": 3},
                source="ctrl"))
        assert len(h.stages) == 1
        assert h.stages[0]["specialist"] == "analyst"

    def test_mission_report(self):
        h = ReportCollectorHandler()
        h(Event(type=EventType.STAGE_COMPLETED,
                data={"stage": "s1", "specialist": "analyst"},
                source="ctrl"))
        h(Event(type=EventType.MISSION_COMPLETED,
                data={"mission_id": "m1", "goal": "test"},
                source="ctrl"))
        report = h.get_report()
        assert report["mission_id"] == "m1"
        assert report["total_stages"] == 1

    def test_empty_report(self):
        h = ReportCollectorHandler()
        report = h.get_report()
        assert report.get("stages") == [] or report == {"stages": []}


# ── AnomalyDetector (14.9) ──────────────────────────────────────

class TestAnomalyDetector:

    def test_rework_threshold(self):
        h = AnomalyDetectorHandler(rework_threshold=2)
        h(Event(type=EventType.STAGE_REWORK, data={}, source="s"))
        assert len(h.anomalies) == 0
        h(Event(type=EventType.STAGE_REWORK, data={}, source="s"))
        assert len(h.anomalies) == 1
        assert h.anomalies[0]["type"] == "high_rework"

    def test_deny_threshold(self):
        h = AnomalyDetectorHandler(deny_threshold=2)
        h(Event(type=EventType.TOOL_BLOCKED, data={}, source="s"))
        h(Event(type=EventType.TOOL_BLOCKED, data={}, source="s"))
        assert len(h.anomalies) == 1
        assert h.anomalies[0]["type"] == "excessive_denies"

    def test_budget_exceeded_flagged(self):
        h = AnomalyDetectorHandler()
        h(Event(type=EventType.BUDGET_EXCEEDED,
                data={"total": 600000}, source="s"))
        assert len(h.anomalies) == 1

    def test_never_halts(self):
        h = AnomalyDetectorHandler(rework_threshold=1)
        r = h(Event(type=EventType.STAGE_REWORK, data={}, source="s"))
        assert r.halt is False


# ── MetricsExporter (14.9) ──────────────────────────────────────

class TestMetricsExporter:

    def test_counts_events(self):
        h = MetricsExporterHandler()
        h(Event(type=EventType.TOOL_EXECUTED, data={}, source="s"))
        h(Event(type=EventType.TOOL_EXECUTED, data={}, source="s"))
        h(Event(type=EventType.TOOL_BLOCKED, data={}, source="s"))
        m = h.get_metrics()
        assert m["events_total"] == 3
        assert m["tools_executed"] == 2
        assert m["tools_blocked"] == 1

    def test_all_counter_keys_present(self):
        h = MetricsExporterHandler()
        m = h.get_metrics()
        assert "events_total" in m
        assert "tools_executed" in m
        assert "missions_completed" in m
        assert "approvals_requested" in m

    def test_mission_lifecycle(self):
        h = MetricsExporterHandler()
        h(Event(type=EventType.MISSION_COMPLETED, data={}, source="s"))
        h(Event(type=EventType.MISSION_FAILED, data={}, source="s"))
        m = h.get_metrics()
        assert m["missions_completed"] == 1
        assert m["missions_failed"] == 1
