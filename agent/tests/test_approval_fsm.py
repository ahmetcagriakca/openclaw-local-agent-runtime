"""Approval FSM tests — D-138 timeout=deny + escalation lifecycle.

Tests:
- State transitions: approve, deny, expire, escalate
- Timeout=deny doctrine
- Terminal state immutability (no reuse)
- Escalation lifecycle
- Idempotency
- Bypass prevention
- Audit event emission
"""
import json
import os
from unittest.mock import patch

import pytest

from services.approval_store import (
    DECIDABLE_STATES,
    TERMINAL_STATES,
    VALID_STATES,
    ApprovalStore,
)


@pytest.fixture
def store(tmp_path):
    return ApprovalStore(store_path=str(tmp_path))


@pytest.fixture
def pending_record(store):
    return store.request_approval(
        mission_id="m-001", stage_id="s-001", role="analyst",
        tool_call_id="tc-12345678", tool="run_shell",
        params={"cmd": "ls"}, risk="high",
        reason="High risk tool", timeout_seconds=300)


class TestStateConstants:
    """Verify D-138 state definitions."""

    def test_valid_states(self):
        assert VALID_STATES == {"pending", "approved", "denied", "expired", "escalated"}

    def test_terminal_states(self):
        assert TERMINAL_STATES == {"approved", "denied", "expired"}

    def test_decidable_states(self):
        assert DECIDABLE_STATES == {"pending", "escalated"}

    def test_terminal_not_decidable(self):
        assert TERMINAL_STATES.isdisjoint(DECIDABLE_STATES)


class TestApprove:
    """Test approval flow."""

    @patch("services.approval_store.emit_policy_event")
    def test_approve_pending(self, mock_emit, store, pending_record):
        assert store.approve(pending_record.approvalId)
        record = store.get_record(pending_record.approvalId)
        assert record["status"] == "approved"
        assert record["decision"] == "approved"
        assert record["decidedBy"] == "operator"
        assert record["decidedAt"] is not None

    @patch("services.approval_store.emit_policy_event")
    def test_approve_emits_event(self, mock_emit, store, pending_record):
        store.approve(pending_record.approvalId)
        calls = [c for c in mock_emit.call_args_list
                 if c[0][0] == "approval_decided" and c[0][1].get("decision") == "approved"]
        assert len(calls) == 1

    @patch("services.approval_store.emit_policy_event")
    def test_approve_persists_to_disk(self, mock_emit, store, pending_record):
        store.approve(pending_record.approvalId)
        path = os.path.join(store.store_path, f"{pending_record.approvalId}.json")
        data = json.loads(open(path).read())
        assert data["status"] == "approved"

    @patch("services.approval_store.emit_policy_event")
    def test_approve_nonexistent_returns_false(self, mock_emit, store):
        assert not store.approve("apr-nonexistent")

    @patch("services.approval_store.emit_policy_event")
    def test_approve_removes_from_pending(self, mock_emit, store, pending_record):
        store.approve(pending_record.approvalId)
        assert pending_record.approvalId not in store.pending
        assert len(store.history) == 1


class TestDeny:
    """Test denial flow."""

    @patch("services.approval_store.emit_policy_event")
    def test_deny_pending(self, mock_emit, store, pending_record):
        assert store.deny(pending_record.approvalId)
        record = store.get_record(pending_record.approvalId)
        assert record["status"] == "denied"
        assert record["decision"] == "denied"

    @patch("services.approval_store.emit_policy_event")
    def test_deny_emits_event(self, mock_emit, store, pending_record):
        store.deny(pending_record.approvalId)
        calls = [c for c in mock_emit.call_args_list
                 if c[0][0] == "approval_decided" and c[0][1].get("decision") == "denied"]
        assert len(calls) == 1

    @patch("services.approval_store.emit_policy_event")
    def test_deny_persists_to_disk(self, mock_emit, store, pending_record):
        store.deny(pending_record.approvalId)
        path = os.path.join(store.store_path, f"{pending_record.approvalId}.json")
        data = json.loads(open(path).read())
        assert data["status"] == "denied"


class TestTimeoutDeny:
    """D-138 doctrine: timeout = deny."""

    @patch("services.approval_store.emit_policy_event")
    def test_expired_approval_cannot_be_approved(self, mock_emit, store):
        """Timeout=deny: expired record rejects approve attempt."""
        record = store.request_approval(
            mission_id="m-002", stage_id="s-002", role="analyst",
            tool_call_id="tc-expired1", tool="run_shell",
            params={"cmd": "rm"}, risk="critical",
            reason="Test expiry", timeout_seconds=0)
        # Timeout=0 means already expired
        assert not store.approve(record.approvalId)
        resolved = store.get_record(record.approvalId)
        assert resolved["status"] == "expired"
        assert resolved["decidedBy"] == "system:timeout"

    @patch("services.approval_store.emit_policy_event")
    def test_check_expired_marks_stale(self, mock_emit, store):
        record = store.request_approval(
            mission_id="m-003", stage_id="s-003", role="analyst",
            tool_call_id="tc-stale001", tool="run_shell",
            params={"cmd": "test"}, risk="high",
            reason="Test", timeout_seconds=0)
        expired = store.check_expired()
        assert record.approvalId in expired

    @patch("services.approval_store.emit_policy_event")
    def test_expired_emits_event(self, mock_emit, store):
        store.request_approval(
            mission_id="m-004", stage_id="s-004", role="analyst",
            tool_call_id="tc-emit001", tool="x",
            params={}, risk="high", reason="Test", timeout_seconds=0)
        store.check_expired()
        calls = [c for c in mock_emit.call_args_list
                 if c[0][0] == "approval_decided" and c[0][1].get("decision") == "expired"]
        assert len(calls) >= 1

    @patch("services.approval_store.emit_policy_event")
    def test_expired_persists_to_disk(self, mock_emit, store):
        record = store.request_approval(
            mission_id="m-005", stage_id="s-005", role="analyst",
            tool_call_id="tc-perst01", tool="x",
            params={"a": 1}, risk="high", reason="Test", timeout_seconds=0)
        store.check_expired()
        path = os.path.join(store.store_path, f"{record.approvalId}.json")
        data = json.loads(open(path).read())
        assert data["status"] == "expired"
        assert data["decidedBy"] == "system:timeout"


class TestTerminalImmutability:
    """Terminal states cannot be modified (no reuse)."""

    @patch("services.approval_store.emit_policy_event")
    def test_cannot_approve_denied(self, mock_emit, store, pending_record):
        store.deny(pending_record.approvalId)
        assert not store.approve(pending_record.approvalId)

    @patch("services.approval_store.emit_policy_event")
    def test_cannot_deny_approved(self, mock_emit, store, pending_record):
        store.approve(pending_record.approvalId)
        assert not store.deny(pending_record.approvalId)

    @patch("services.approval_store.emit_policy_event")
    def test_cannot_approve_expired(self, mock_emit, store):
        record = store.request_approval(
            mission_id="m-006", stage_id="s-006", role="analyst",
            tool_call_id="tc-noreu01", tool="x",
            params={"b": 2}, risk="high", reason="Test", timeout_seconds=0)
        store.check_expired()
        # Record is now in history, not pending — approve should fail
        assert not store.approve(record.approvalId)

    @patch("services.approval_store.emit_policy_event")
    def test_cannot_escalate_denied(self, mock_emit, store, pending_record):
        store.deny(pending_record.approvalId)
        assert not store.escalate(pending_record.approvalId)

    @patch("services.approval_store.emit_policy_event")
    def test_cannot_escalate_approved(self, mock_emit, store, pending_record):
        store.approve(pending_record.approvalId)
        assert not store.escalate(pending_record.approvalId)


class TestEscalation:
    """D-138 escalation lifecycle."""

    @patch("services.approval_store.emit_policy_event")
    def test_escalate_pending(self, mock_emit, store, pending_record):
        assert store.escalate(pending_record.approvalId, reason="risk_critical")
        record = store.get_record(pending_record.approvalId)
        assert record["status"] == "escalated"
        assert record["escalationReason"] == "risk_critical"
        assert record["escalatedAt"] is not None

    @patch("services.approval_store.emit_policy_event")
    def test_approve_escalated(self, mock_emit, store, pending_record):
        store.escalate(pending_record.approvalId)
        assert store.approve(pending_record.approvalId, decided_by="admin")
        record = store.get_record(pending_record.approvalId)
        assert record["status"] == "approved"
        assert record["decidedBy"] == "admin"

    @patch("services.approval_store.emit_policy_event")
    def test_deny_escalated(self, mock_emit, store, pending_record):
        store.escalate(pending_record.approvalId)
        assert store.deny(pending_record.approvalId, decided_by="admin")
        record = store.get_record(pending_record.approvalId)
        assert record["status"] == "denied"

    @patch("services.approval_store.emit_policy_event")
    def test_escalated_expires(self, mock_emit, store):
        record = store.request_approval(
            mission_id="m-esc", stage_id="s-esc", role="analyst",
            tool_call_id="tc-escexp1", tool="x",
            params={"esc": 1}, risk="critical", reason="Test", timeout_seconds=0)
        # Escalate before expiry check — but timeout=0 means expired
        # escalate should fail because already expired
        assert not store.escalate(record.approvalId)

    @patch("services.approval_store.emit_policy_event")
    def test_escalation_emits_event(self, mock_emit, store, pending_record):
        store.escalate(pending_record.approvalId, reason="test_reason")
        calls = [c for c in mock_emit.call_args_list
                 if c[0][0] == "approval_decided" and c[0][1].get("decision") == "escalated"]
        assert len(calls) == 1

    @patch("services.approval_store.emit_policy_event")
    def test_cannot_double_escalate(self, mock_emit, store, pending_record):
        store.escalate(pending_record.approvalId)
        # Already escalated, not pending — should fail
        assert not store.escalate(pending_record.approvalId)


class TestIdempotency:
    """Duplicate request handling."""

    @patch("services.approval_store.emit_policy_event")
    def test_duplicate_params_returns_existing(self, mock_emit, store):
        r1 = store.request_approval(
            mission_id="m-dup", stage_id="s-dup", role="analyst",
            tool_call_id="tc-dup00001", tool="x",
            params={"dup": True}, risk="high", reason="Test", timeout_seconds=300)
        r2 = store.request_approval(
            mission_id="m-dup", stage_id="s-dup", role="analyst",
            tool_call_id="tc-dup00002", tool="x",
            params={"dup": True}, risk="high", reason="Test", timeout_seconds=300)
        assert r1.approvalId == r2.approvalId


class TestGetRecord:
    """Record retrieval from pending and history."""

    @patch("services.approval_store.emit_policy_event")
    def test_get_pending_record(self, mock_emit, store, pending_record):
        record = store.get_record(pending_record.approvalId)
        assert record is not None
        assert record["status"] == "pending"

    @patch("services.approval_store.emit_policy_event")
    def test_get_history_record(self, mock_emit, store, pending_record):
        store.approve(pending_record.approvalId)
        record = store.get_record(pending_record.approvalId)
        assert record is not None
        assert record["status"] == "approved"

    @patch("services.approval_store.emit_policy_event")
    def test_get_nonexistent_returns_none(self, mock_emit, store):
        assert store.get_record("apr-nonexistent") is None
