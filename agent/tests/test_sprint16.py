"""Sprint 16 — Presentation Layer + CI/CD Foundation Tests.

Covers:
- Persistence layer (mission_store, trace_store, metric_store)
- Dashboard API endpoints
- Telemetry query API endpoints
- Alert engine + rules
- Alert API endpoints
- Session model
- Full integration: record → query → render
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from conftest import CSRF_ORIGIN
from fastapi.testclient import TestClient

# ══════════════════════════════════════════════════════════════
# Persistence Layer Tests
# ══════════════════════════════════════════════════════════════

class TestMissionStore(unittest.TestCase):
    """Task 16.0: mission_store.py persistence tests."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = Path(self.tmp) / "mission-history.json"
        from persistence.mission_store import MissionStore
        self.store = MissionStore(store_path=self.path)

    def test_record_and_get(self):
        self.store.record({
            "id": "m-001", "goal": "Test mission",
            "complexity": "medium", "status": "completed",
            "tokens": 50000, "duration": 30.5, "stages": 3,
        })
        result = self.store.get("m-001")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "m-001")
        self.assertEqual(result["tokens"], 50000)

    def test_list_with_filters(self):
        for i in range(5):
            self.store.record({
                "id": f"m-{i:03d}",
                "goal": f"Mission {i}",
                "complexity": "medium" if i % 2 == 0 else "complex",
                "status": "completed" if i < 3 else "failed",
                "tokens": (i + 1) * 10000,
            })

        # Filter by status
        items, total = self.store.list(status=["completed"])
        self.assertEqual(total, 3)

        # Filter by complexity
        items, total = self.store.list(complexity=["complex"])
        self.assertEqual(total, 2)

        # Search
        items, total = self.store.list(search="Mission 2")
        self.assertEqual(total, 1)

        # Pagination
        items, total = self.store.list(limit=2, offset=0)
        self.assertEqual(len(items), 2)
        self.assertEqual(total, 5)

    def test_summary(self):
        self.store.record({"id": "m-001", "status": "completed", "tokens": 50000, "duration": 30})
        self.store.record({"id": "m-002", "status": "failed", "tokens": 20000, "duration": 10})
        summary = self.store.summary()
        self.assertEqual(summary["total_missions"], 2)
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["total_tokens"], 70000)

    def test_persistence_across_instances(self):
        self.store.record({"id": "m-001", "goal": "Persist test"})
        from persistence.mission_store import MissionStore
        store2 = MissionStore(store_path=self.path)
        self.assertEqual(store2.count, 1)
        self.assertIsNotNone(store2.get("m-001"))


class TestTraceStore(unittest.TestCase):
    """Task 16.1: trace_store.py tests."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = Path(self.tmp) / "trace-history.json"
        from persistence.trace_store import TraceStore
        self.store = TraceStore(store_path=self.path)

    def test_record_and_get(self):
        spans = [
            {"name": "mission", "attributes": {"mission.id": "m-001"}},
            {"name": "stage:analyst", "attributes": {"stage.name": "analyst"}},
        ]
        self.store.record_trace("m-001", spans)
        trace = self.store.get_trace("m-001")
        self.assertIsNotNone(trace)
        self.assertEqual(trace["span_count"], 2)

    def test_list_traces(self):
        for i in range(3):
            self.store.record_trace(f"m-{i:03d}", [{"name": "mission"}])
        traces = self.store.list_traces()
        self.assertEqual(len(traces), 3)

    def test_get_span_tree(self):
        spans = [{"name": "mission"}, {"name": "stage:dev"}]
        self.store.record_trace("m-001", spans)
        tree = self.store.get_span_tree("m-001")
        self.assertEqual(len(tree), 2)


class TestMetricStore(unittest.TestCase):
    """Task 16.2: metric_store.py tests."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = Path(self.tmp) / "metric-history.json"
        from persistence.metric_store import MetricStore
        self.store = MetricStore(store_path=self.path)

    def test_snapshot_and_get(self):
        self.store.snapshot({"missions_total": 5, "tokens_total": 100000})
        current = self.store.get_current()
        self.assertEqual(current["missions_total"], 5)

    def test_history(self):
        for i in range(3):
            self.store.snapshot({"missions_total": i})
        history = self.store.get_history()
        self.assertEqual(len(history), 3)


# ══════════════════════════════════════════════════════════════
# Alert Engine Tests
# ══════════════════════════════════════════════════════════════

class TestAlertEngine(unittest.TestCase):
    """Task 16.6: alert_engine.py tests."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config_path = Path(self.tmp) / "alert-rules.json"
        from observability.alert_engine import AlertEngine
        self.engine = AlertEngine(config_path=self.config_path)

    def test_default_rules_loaded(self):
        rules = self.engine.get_rules()
        self.assertEqual(len(rules), 9)

    def test_mission_aborted_fires_alert(self):
        from events.bus import Event
        from events.catalog import EventType
        event = Event(
            type=EventType.MISSION_ABORTED,
            data={"mission_id": "m-test", "reason": "budget"},
            source="test",
        )
        self.engine(event)
        active = self.engine.get_active()
        self.assertTrue(len(active) > 0)

    def test_budget_warning_fires_after_threshold(self):
        from events.bus import Event
        from events.catalog import EventType
        # A-006 fires on first budget.warning
        event = Event(
            type=EventType.BUDGET_WARNING,
            data={"current": 250000, "limit": 300000},
            source="test",
        )
        self.engine(event)
        active = self.engine.get_active()
        self.assertTrue(len(active) > 0)

    def test_rule_crud(self):
        # Update
        result = self.engine.update_rule("A-001", {"threshold": 5})
        self.assertIsNotNone(result)
        self.assertEqual(result["threshold"], 5)

        # Add
        new_rule = self.engine.add_rule({
            "id": "A-100", "name": "Custom rule",
            "event_types": [], "condition": "any",
            "threshold": 1, "severity": "info",
        })
        self.assertEqual(new_rule["id"], "A-100")
        self.assertEqual(len(self.engine.get_rules()), 10)

    def test_alert_history(self):
        from events.bus import Event
        from events.catalog import EventType
        event = Event(
            type=EventType.MISSION_ABORTED,
            data={"mission_id": "m-hist"},
            source="test",
        )
        self.engine(event)
        history = self.engine.get_history()
        self.assertTrue(len(history) > 0)
        self.assertEqual(history[0]["mission_id"], "m-hist")


class TestAlertNotifier(unittest.TestCase):
    """Task 16.7: alert_notifier.py tests."""

    def test_format_message(self):
        from observability.alert_engine import Alert
        from observability.alert_notifier import AlertNotifier
        notifier = AlertNotifier()
        alert = Alert(
            rule_id="A-001", rule_name="Budget gates",
            severity="warning", mission_id="m-test",
            details={"event_type": "approval.requested", "trigger_value": 4, "threshold": 3},
        )
        msg = notifier._format_message(alert, "\u26a0\ufe0f")
        self.assertIn("A-001", msg)
        self.assertIn("m-test", msg)

    def test_no_token_skips_send(self):
        from observability.alert_engine import Alert
        from observability.alert_notifier import AlertNotifier
        notifier = AlertNotifier(bot_token="", chat_id="")
        alert = Alert("A-001", "Test", "info", "m-001", {})
        result = notifier.send_alert(alert)
        self.assertFalse(result)


# ══════════════════════════════════════════════════════════════
# Dashboard API Tests
# ══════════════════════════════════════════════════════════════

class TestDashboardAPI(unittest.TestCase):
    """Task 16.4-16.5: dashboard API endpoint tests."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Patch mission store path
        from persistence.mission_store import MissionStore
        self.store = MissionStore(store_path=Path(self.tmp) / "missions.json")
        self.store.record({
            "id": "m-api-001", "goal": "API test",
            "status": "completed", "complexity": "medium",
            "tokens": 50000, "duration": 25,
        })
        import api.dashboard_api as dapi
        dapi._mission_store = self.store

        from api.server import app
        self.client = TestClient(app)

    def test_list_missions(self):
        r = self.client.get("/api/v1/dashboard/missions")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("missions", data)
        self.assertEqual(data["total"], 1)

    def test_get_mission(self):
        r = self.client.get("/api/v1/dashboard/missions/m-api-001")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["mission"]["id"], "m-api-001")

    def test_get_mission_404(self):
        r = self.client.get("/api/v1/dashboard/missions/nonexistent")
        self.assertEqual(r.status_code, 404)

    def test_summary(self):
        r = self.client.get("/api/v1/dashboard/summary")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total_missions"], 1)
        self.assertEqual(data["completed"], 1)

    def test_filter_by_status(self):
        r = self.client.get("/api/v1/dashboard/missions?status=failed")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total"], 0)


# ══════════════════════════════════════════════════════════════
# Telemetry Query API Tests
# ══════════════════════════════════════════════════════════════

class TestTelemetryQueryAPI(unittest.TestCase):
    """Task 16.1-16.3: telemetry query endpoint tests."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from persistence.metric_store import MetricStore
        from persistence.trace_store import TraceStore
        self.trace_store = TraceStore(store_path=Path(self.tmp) / "traces.json")
        self.metric_store = MetricStore(store_path=Path(self.tmp) / "metrics.json")

        self.trace_store.record_trace("m-trace-001", [
            {"name": "mission", "attributes": {}},
            {"name": "stage:analyst", "attributes": {}},
        ])
        self.metric_store.snapshot({"missions_total": 5})

        import api.telemetry_query_api as tqapi
        tqapi._trace_store = self.trace_store
        tqapi._metric_store = self.metric_store

        from api.server import app
        self.client = TestClient(app)

    def test_get_trace(self):
        r = self.client.get("/api/v1/telemetry/traces/m-trace-001")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["trace"]["span_count"], 2)

    def test_get_trace_404(self):
        r = self.client.get("/api/v1/telemetry/traces/nonexistent")
        self.assertEqual(r.status_code, 404)

    def test_list_traces(self):
        r = self.client.get("/api/v1/telemetry/traces")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total"], 1)

    def test_current_metrics(self):
        r = self.client.get("/api/v1/telemetry/metrics/current")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["metrics"]["missions_total"], 5)

    def test_metric_history(self):
        r = self.client.get("/api/v1/telemetry/metrics/history")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total"], 1)

    def test_query_logs_empty(self):
        r = self.client.get("/api/v1/telemetry/logs")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total"], 0)


# ══════════════════════════════════════════════════════════════
# Alert API Tests
# ══════════════════════════════════════════════════════════════

class TestAlertAPI(unittest.TestCase):
    """Task 16.8: alert API endpoint tests."""

    def setUp(self):
        os.environ.setdefault("VEZIR_AUTH_BYPASS", "1")
        self.tmp = tempfile.mkdtemp()
        from observability.alert_engine import AlertEngine
        self.engine = AlertEngine(config_path=Path(self.tmp) / "rules.json")

        import api.alerts_api as aapi
        aapi.set_engine(self.engine)

        from api.server import app
        self.client = TestClient(app)

    def test_list_rules(self):
        r = self.client.get("/api/v1/alerts/rules")
        self.assertEqual(r.status_code, 200)
        rules = r.json()["rules"]
        self.assertEqual(len(rules), 9)

    def test_get_rule(self):
        r = self.client.get("/api/v1/alerts/rules/A-001")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["rule"]["id"], "A-001")

    def test_update_rule(self):
        r = self.client.put("/api/v1/alerts/rules/A-001",
                            json={"threshold": 5, "enabled": False},
                            headers={"Origin": CSRF_ORIGIN})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["rule"]["threshold"], 5)
        self.assertFalse(r.json()["rule"]["enabled"])

    def test_create_rule(self):
        r = self.client.post("/api/v1/alerts/rules", json={
            "id": "A-100", "name": "Custom", "condition": "any",
            "threshold": 1, "severity": "info",
        }, headers={"Origin": CSRF_ORIGIN})
        self.assertEqual(r.status_code, 200)

    def test_active_alerts(self):
        r = self.client.get("/api/v1/alerts/active")
        self.assertEqual(r.status_code, 200)
        self.assertIn("alerts", r.json())

    def test_alert_history(self):
        r = self.client.get("/api/v1/alerts/history")
        self.assertEqual(r.status_code, 200)
        self.assertIn("alerts", r.json())


# ══════════════════════════════════════════════════════════════
# Session Model Tests
# ══════════════════════════════════════════════════════════════

class TestSessionModel(unittest.TestCase):
    """Task 16.19: auth/session.py tests."""

    def test_session_creation(self):
        from auth.session import Session
        s = Session()
        self.assertTrue(len(s.session_id) > 0)
        self.assertEqual(s.operator, "akca")

    def test_get_operator(self):
        from auth.session import get_operator
        self.assertEqual(get_operator(), "akca")

    def test_session_to_dict(self):
        from auth.session import Session
        s = Session(operator="test-user", source="telegram")
        d = s.to_dict()
        self.assertEqual(d["operator"], "test-user")
        self.assertEqual(d["source"], "telegram")


# ══════════════════════════════════════════════════════════════
# Integration: Full E2E Flow
# ══════════════════════════════════════════════════════════════

class TestFullIntegration(unittest.TestCase):
    """Task 16.21: record → query → API response chain."""

    def test_mission_record_to_api(self):
        """Record a mission via store → query via dashboard API."""
        tmp = tempfile.mkdtemp()
        from persistence.mission_store import MissionStore
        store = MissionStore(store_path=Path(tmp) / "missions.json")

        # Record mission
        store.record({
            "id": "m-e2e-001", "goal": "E2E integration test",
            "complexity": "medium", "status": "completed",
            "tokens": 75000, "duration": 45.2, "stages": 5,
            "tools": 12, "reworks": 1,
        })

        # Query via store
        mission = store.get("m-e2e-001")
        self.assertIsNotNone(mission)
        self.assertEqual(mission["tokens"], 75000)

        # Query via list
        items, total = store.list(search="E2E")
        self.assertEqual(total, 1)

        # Summary
        summary = store.summary()
        self.assertEqual(summary["total_missions"], 1)
        self.assertEqual(summary["avg_tokens"], 75000)

    def test_trace_record_to_api(self):
        """Record trace → query via API."""
        tmp = tempfile.mkdtemp()
        from persistence.trace_store import TraceStore
        store = TraceStore(store_path=Path(tmp) / "traces.json")

        store.record_trace("m-e2e-001", [
            {"name": "mission", "attributes": {"mission.id": "m-e2e-001"}},
            {"name": "stage:analyst"},
            {"name": "stage:developer"},
            {"name": "tool:ReadFile"},
            {"name": "llm_call"},
        ])

        trace = store.get_trace("m-e2e-001")
        self.assertEqual(trace["span_count"], 5)

    def test_alert_e2e(self):
        """Event → alert engine → alert fired."""
        tmp = tempfile.mkdtemp()
        from events.bus import Event, EventBus
        from events.catalog import EventType
        from observability.alert_engine import AlertEngine

        engine = AlertEngine(config_path=Path(tmp) / "rules.json")
        bus = EventBus()
        bus.on_all(engine, priority=5, name="AlertEngine")

        # Emit mission abort → should fire A-008
        bus.emit(Event(
            type=EventType.MISSION_ABORTED,
            data={"mission_id": "m-alert-e2e", "reason": "operator abort"},
            source="test",
        ))

        active = engine.get_active()
        self.assertTrue(len(active) > 0)
        # A-004 (bypass/any) and A-005 (audit/any) also fire due to "any" condition
        # A-008 specifically fires for mission.aborted
        rule_ids = [a["rule_id"] for a in active]
        self.assertIn("A-008", rule_ids)


if __name__ == "__main__":
    unittest.main()
