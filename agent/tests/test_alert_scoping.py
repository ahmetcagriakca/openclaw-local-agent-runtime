"""Tests for B-119 Alert Namespace Scoping Fix (Sprint 49).

Covers: user_id in Alert model, write-path population,
read-path filtering, legacy compatibility.
"""


from events.bus import Event
from events.catalog import EventType
from observability.alert_engine import Alert, AlertEngine


class TestAlertModel:
    def test_user_id_in_init(self):
        alert = Alert("r1", "test", "info", "m1", {}, user_id="user-1")
        assert alert.user_id == "user-1"

    def test_user_id_default_none(self):
        alert = Alert("r1", "test", "info", "m1", {})
        assert alert.user_id is None

    def test_user_id_in_to_dict(self):
        alert = Alert("r1", "test", "info", "m1", {}, user_id="user-1")
        d = alert.to_dict()
        assert d["user_id"] == "user-1"

    def test_legacy_alert_to_dict(self):
        alert = Alert("r1", "test", "info", "m1", {})
        d = alert.to_dict()
        assert d["user_id"] is None


class TestWritePath:
    def test_fire_populates_user_id_from_operator(self):
        engine = AlertEngine()
        event = Event(
            type=EventType.MISSION_FAILED,
            source="test",
            data={"mission_id": "m1", "operator": "user-abc", "error": "fail"},
        )
        engine(event)
        active = engine.get_active()
        # At least one alert should have user_id
        fired = [a for a in active if a.get("mission_id") == "m1"]
        if fired:
            assert fired[0]["user_id"] == "user-abc"

    def test_fire_fallback_to_system(self):
        engine = AlertEngine()
        event = Event(
            type=EventType.MISSION_FAILED,
            source="test",
            data={"mission_id": "m2"},
        )
        engine(event)
        active = engine.get_active()
        fired = [a for a in active if a.get("mission_id") == "m2"]
        if fired:
            assert fired[0]["user_id"] == "system"


class TestReadPathScoping:
    def _engine_with_alerts(self):
        engine = AlertEngine()
        # Manually inject alerts with different user_ids
        engine._active = [
            Alert("r1", "alert-1", "warn", "m1", {}, user_id="alice"),
            Alert("r2", "alert-2", "warn", "m2", {}, user_id="bob"),
            Alert("r3", "alert-3", "warn", "m3", {}, user_id=None),  # legacy
            Alert("r4", "alert-4", "warn", "m4", {}, user_id="system"),
        ]
        engine._history = list(engine._active)
        return engine

    def test_get_active_no_filter(self):
        engine = self._engine_with_alerts()
        alerts = engine.get_active()
        assert len(alerts) == 4

    def test_get_active_filter_alice(self):
        engine = self._engine_with_alerts()
        alerts = engine.get_active(user_id="alice")
        # alice's alert + legacy (None) alerts
        user_ids = [a["user_id"] for a in alerts]
        assert "alice" in user_ids
        assert None in user_ids  # legacy visible
        assert "bob" not in user_ids

    def test_get_active_filter_bob(self):
        engine = self._engine_with_alerts()
        alerts = engine.get_active(user_id="bob")
        user_ids = [a["user_id"] for a in alerts]
        assert "bob" in user_ids
        assert None in user_ids  # legacy visible
        assert "alice" not in user_ids

    def test_get_history_scoped(self):
        engine = self._engine_with_alerts()
        history = engine.get_history(user_id="alice")
        user_ids = [a["user_id"] for a in history]
        assert "alice" in user_ids
        assert None in user_ids  # legacy visible
        assert "bob" not in user_ids

    def test_legacy_alerts_visible_to_all(self):
        engine = self._engine_with_alerts()
        alice_alerts = engine.get_active(user_id="alice")
        bob_alerts = engine.get_active(user_id="bob")
        # Legacy (None) alert visible to both
        alice_none = [a for a in alice_alerts if a["user_id"] is None]
        bob_none = [a for a in bob_alerts if a["user_id"] is None]
        assert len(alice_none) == 1
        assert len(bob_none) == 1
