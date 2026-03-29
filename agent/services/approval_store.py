"""Approval store — strict ID-based approval lifecycle with idempotency."""
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from context.policy_telemetry import emit_policy_event
from utils.atomic_write import atomic_write_json


@dataclass
class ApprovalRecord:
    approvalId: str
    missionId: str
    stageId: str
    requestedByRole: str
    toolCallId: str
    tool: str
    paramsHash: str
    risk: str
    reason: str
    requestedAt: str
    expiresAt: str
    status: str = "pending"
    decision: str = None
    decidedAt: str = None
    decidedBy: str = None


class ApprovalStore:
    """Strict ID-based approval lifecycle. No ambiguous yes/no."""

    def __init__(self, store_path=None):
        if store_path is None:
            store_path = os.path.join(
                os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))),
                "logs", "approvals")
        self.store_path = store_path
        self.pending = {}
        self.history = []
        os.makedirs(store_path, exist_ok=True)

    def request_approval(self, mission_id, stage_id, role,
                         tool_call_id, tool, params, risk,
                         reason, timeout_seconds=60) -> ApprovalRecord:
        now = datetime.now(timezone.utc)
        params_hash = hashlib.sha256(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest()

        # Idempotency — same params already pending?
        for existing in self.pending.values():
            if existing.paramsHash == f"sha256:{params_hash}" and \
               existing.status == "pending":
                return existing

        record = ApprovalRecord(
            approvalId=f"apr-{now.strftime('%Y%m%d%H%M%S%f')}-{tool_call_id[:8]}",
            missionId=mission_id,
            stageId=stage_id,
            requestedByRole=role,
            toolCallId=tool_call_id,
            tool=tool,
            paramsHash=f"sha256:{params_hash}",
            risk=risk,
            reason=reason,
            requestedAt=now.isoformat(),
            expiresAt=(now + timedelta(seconds=timeout_seconds)).isoformat()
        )

        self.pending[record.approvalId] = record
        self._persist(record)

        emit_policy_event("approval_requested", {
            "approval_id": record.approvalId,
            "mission_id": mission_id,
            "tool": tool, "risk": risk, "role": role})

        return record

    def approve(self, approval_id: str, decided_by: str = "operator") -> bool:
        record = self.pending.get(approval_id)
        if not record or record.status != "pending":
            return False
        if self._is_expired(record):
            self._expire(record)
            return False

        record.status = "approved"
        record.decision = "approved"
        record.decidedAt = datetime.now(timezone.utc).isoformat()
        record.decidedBy = decided_by
        self._move_to_history(record)

        emit_policy_event("approval_decided", {
            "approval_id": approval_id,
            "decision": "approved", "decided_by": decided_by})
        return True

    def deny(self, approval_id: str, decided_by: str = "operator") -> bool:
        record = self.pending.get(approval_id)
        if not record or record.status != "pending":
            return False

        record.status = "denied"
        record.decision = "denied"
        record.decidedAt = datetime.now(timezone.utc).isoformat()
        record.decidedBy = decided_by
        self._move_to_history(record)

        emit_policy_event("approval_decided", {
            "approval_id": approval_id,
            "decision": "denied", "decided_by": decided_by})
        return True

    def check_expired(self):
        expired = []
        for aid, record in list(self.pending.items()):
            if self._is_expired(record):
                self._expire(record)
                expired.append(aid)
        return expired

    def get_pending(self) -> list:
        self.check_expired()
        return [asdict(r) for r in self.pending.values()
                if r.status == "pending"]

    def check_idempotency(self, params_hash: str) -> str | None:
        for record in self.history:
            if record.paramsHash == f"sha256:{params_hash}" and \
               record.status == "approved":
                return record.approvalId
        return None

    def _is_expired(self, record):
        expires = datetime.fromisoformat(record.expiresAt)
        return datetime.now(timezone.utc) > expires

    def _expire(self, record):
        record.status = "expired"
        record.decidedAt = datetime.now(timezone.utc).isoformat()
        self._move_to_history(record)
        emit_policy_event("approval_decided", {
            "approval_id": record.approvalId, "decision": "expired"})

    def _move_to_history(self, record):
        if record.approvalId in self.pending:
            del self.pending[record.approvalId]
        self.history.append(record)

    def _persist(self, record):
        path = os.path.join(self.store_path, f"{record.approvalId}.json")
        try:
            atomic_write_json(path, asdict(record))
        except Exception:
            pass
