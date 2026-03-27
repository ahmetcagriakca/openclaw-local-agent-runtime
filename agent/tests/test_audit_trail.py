"""Tests for AuditTrail handler — Task 14.1."""
import json
import os
import tempfile

import pytest

from events.bus import Event, EventBus
from events.catalog import EventType
from events.handlers.audit_trail import AuditTrailHandler


@pytest.fixture
def audit_dir():
    d = tempfile.mkdtemp()
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def handler(audit_dir):
    return AuditTrailHandler(log_dir=audit_dir)


@pytest.fixture
def bus_with_audit(handler):
    bus = EventBus()
    bus.on_all(handler, priority=0, name="audit")
    return bus


class TestAuditTrailHandler:

    def test_creates_log_file(self, handler, audit_dir):
        e = Event(type=EventType.MISSION_STARTED, data={"goal": "test"}, source="ctrl")
        handler(e)
        assert os.path.isfile(os.path.join(audit_dir, "audit-trail.jsonl"))

    def test_never_halts(self, handler):
        e = Event(type="test", data={}, source="s")
        result = handler(e)
        assert result.halt is False

    def test_entries_have_chain_hash(self, handler, audit_dir):
        handler(Event(type="a", data={}, source="s"))
        handler(Event(type="b", data={}, source="s"))

        with open(os.path.join(audit_dir, "audit-trail.jsonl")) as f:
            lines = [json.loads(ln) for ln in f if ln.strip()]

        assert lines[0]["prev_hash"] == "genesis"
        assert lines[1]["prev_hash"] == lines[0]["hash"]
        assert lines[0]["hash"] != lines[1]["hash"]

    def test_chain_verification_passes(self, handler):
        for i in range(5):
            handler(Event(type=f"e{i}", data={"i": i}, source="s"))
        valid, count, error = handler.verify_chain()
        assert valid is True
        assert count == 5
        assert error == ""

    def test_chain_detects_tampering(self, handler, audit_dir):
        handler(Event(type="a", data={}, source="s"))
        handler(Event(type="b", data={}, source="s"))

        # Tamper with the first entry
        log_path = os.path.join(audit_dir, "audit-trail.jsonl")
        with open(log_path, "r") as f:
            lines = f.readlines()
        entry = json.loads(lines[0])
        entry["data"]["injected"] = True
        lines[0] = json.dumps(entry) + "\n"
        with open(log_path, "w") as f:
            f.writelines(lines)

        valid, count, error = handler.verify_chain()
        assert valid is False
        assert "hash mismatch" in error

    def test_sanitizes_large_data(self, handler, audit_dir):
        big = "x" * 5000
        handler(Event(type="t", data={"big": big}, source="s"))

        with open(os.path.join(audit_dir, "audit-trail.jsonl")) as f:
            entry = json.loads(f.readline())

        assert len(entry["data"]["big"]) < 300
        assert "truncated" in entry["data"]["big"]

    def test_sequential_numbering(self, handler, audit_dir):
        for i in range(3):
            handler(Event(type="t", data={}, source="s"))

        with open(os.path.join(audit_dir, "audit-trail.jsonl")) as f:
            entries = [json.loads(ln) for ln in f if ln.strip()]

        assert [e["seq"] for e in entries] == [0, 1, 2]

    def test_correlation_id_recorded(self, handler, audit_dir):
        e = Event(type="t", data={}, source="s", correlation_id="abc123")
        handler(e)

        with open(os.path.join(audit_dir, "audit-trail.jsonl")) as f:
            entry = json.loads(f.readline())
        assert entry["correlation_id"] == "abc123"

    def test_resumes_chain_on_restart(self, audit_dir):
        h1 = AuditTrailHandler(log_dir=audit_dir)
        h1(Event(type="a", data={}, source="s"))
        h1(Event(type="b", data={}, source="s"))
        last_hash = h1._prev_hash

        # Simulate restart
        h2 = AuditTrailHandler(log_dir=audit_dir)
        assert h2._prev_hash == last_hash
        assert h2._count == 2

        h2(Event(type="c", data={}, source="s"))
        valid, count, _ = h2.verify_chain()
        assert valid is True
        assert count == 3

    def test_works_with_eventbus(self, bus_with_audit, handler, audit_dir):
        bus_with_audit.emit(Event(type=EventType.TOOL_REQUESTED,
                                   data={"tool": "read_file"}, source="runner"))
        bus_with_audit.emit(Event(type=EventType.TOOL_BLOCKED,
                                   data={"tool": "snapshot", "role": "analyst"},
                                   source="permission"))

        valid, count, _ = handler.verify_chain()
        assert valid is True
        assert count == 2
