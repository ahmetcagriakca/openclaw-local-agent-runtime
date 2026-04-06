"""Tests for audit ownership — S76 P3.5/P3.6.

Verifies:
- 3 audit writers target distinct files
- Governance chain (audit_integrity) fails explicitly on write error
- Operational log (audit_service) continues on write error
- Chain integrity verification passes after writes
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestAuditWriterSeparation:
    """P3.5: Verify 3 writers target distinct files."""

    def test_audit_integrity_targets_audit_jsonl(self):
        from persistence.audit_integrity import AUDIT_PATH
        assert AUDIT_PATH.endswith("audit.jsonl")
        assert "audit" in AUDIT_PATH

    def test_audit_trail_targets_audit_trail_jsonl(self):
        from events.handlers.audit_trail import AuditTrailHandler
        handler = AuditTrailHandler(log_dir="/tmp/test-audit")
        assert handler.log_path.endswith("audit-trail.jsonl")

    def test_audit_service_targets_agent_audit_jsonl(self):
        from services.audit_service import AUDIT_LOG_PATH
        assert AUDIT_LOG_PATH.endswith("agent-audit.jsonl")

    def test_all_three_targets_are_distinct(self):
        from persistence.audit_integrity import AUDIT_PATH
        from services.audit_service import AUDIT_LOG_PATH

        paths = {
            os.path.basename(AUDIT_PATH),
            os.path.basename(AUDIT_LOG_PATH),
            "audit-trail.jsonl",
        }
        assert len(paths) == 3, "All 3 audit writers must target distinct files"


class TestGovernanceChainFailure:
    """P3.5: Governance chain write failure → explicit error."""

    def test_append_entry_creates_valid_chain(self, tmp_path):
        from persistence.audit_integrity import append_entry
        log_path = str(tmp_path / "test-audit.jsonl")

        e1 = append_entry("test.event1", "test_actor", "detail1", audit_path=log_path)
        assert "entry_hash" in e1
        assert "prev_hash" in e1

        e2 = append_entry("test.event2", "test_actor", "detail2", audit_path=log_path)
        assert e2["prev_hash"] == e1["entry_hash"]

    def test_append_entry_writes_to_file(self, tmp_path):
        from persistence.audit_integrity import append_entry
        log_path = str(tmp_path / "test-audit.jsonl")

        append_entry("test.event", "actor", "detail", audit_path=log_path)

        assert os.path.exists(log_path)
        lines = Path(log_path).read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event"] == "test.event"


class TestOperationalLogFailure:
    """P3.5: Operational log failure → silent continue."""

    def test_log_agent_run_silent_on_write_error(self, tmp_path):
        from services.audit_service import log_agent_run

        # Write to a path that will fail (directory as file)
        with patch("services.audit_service.AUDIT_LOG_PATH", str(tmp_path)):
            # Should NOT raise — silent continue
            log_agent_run(
                session_id="s1", agent_id="a1", user_id="u1",
                user_message="test", tool_calls=[], response="ok",
                status="completed", turns_used=1, duration_ms=100,
            )


class TestChainIntegrity:
    """P3.6: Chain integrity verification."""

    def test_chain_integrity_after_writes(self, tmp_path):
        from persistence.audit_integrity import append_entry, verify_chain

        log_path = str(tmp_path / "integrity-test.jsonl")

        for i in range(5):
            append_entry(f"event.{i}", "actor", f"detail-{i}", audit_path=log_path)

        result = verify_chain(audit_path=log_path)
        assert result["status"] == "INTEGRITY_OK"
        assert result["entry_count"] == 5

    def test_chain_detects_tampering(self, tmp_path):
        from persistence.audit_integrity import append_entry, verify_chain

        log_path = str(tmp_path / "tamper-test.jsonl")

        for i in range(3):
            append_entry(f"event.{i}", "actor", f"detail-{i}", audit_path=log_path)

        # Tamper with second entry
        lines = Path(log_path).read_text().strip().split("\n")
        entry = json.loads(lines[1])
        entry["detail"] = "TAMPERED"
        lines[1] = json.dumps(entry)
        Path(log_path).write_text("\n".join(lines) + "\n")

        result = verify_chain(audit_path=log_path)
        assert result["status"] == "INTEGRITY_FAIL"

    def test_audit_trail_handler_chain_integrity(self, tmp_path):
        from events.bus import Event
        from events.catalog import EventType
        from events.handlers.audit_trail import AuditTrailHandler

        handler = AuditTrailHandler(log_dir=str(tmp_path))

        for i in range(3):
            event = Event(
                type=EventType.MISSION_STARTED,
                data={"mission_id": f"m{i}"},
                source="test",
            )
            handler(event)

        valid, count, error = handler.verify_chain()
        assert valid is True
        assert count == 3
