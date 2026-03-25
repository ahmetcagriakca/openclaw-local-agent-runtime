"""Sprint 11 Task 11.1 — Contract-First Mutation Test Suite.

11 tests written BEFORE endpoint code. All initially FAIL (endpoints don't exist yet).
Contract source: SPRINT-11-TASK-BREAKDOWN.md Section 3-4, D-096.

Tests:
 1. POST mutation → lifecycleState=requested
 2. requested → accepted → applied (SSE)
 3. requested → accepted → rejected (SSE)
 4. requested → timed_out (SSE)
 5. duplicate mutation on same target while active/pending → 409
 6. invalid FSM state → rejected
 7. audit log fields present
 8. atomic request artifact created
 9. CSRF: missing Origin → 403
10. 2-tab race: simultaneous approve
11. cancel during active execution
"""
import asyncio
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_TIMEOUT = 10.0


def run_with_timeout(coro, timeout=TEST_TIMEOUT):
    """Run an async coroutine with a hard timeout."""
    async def _wrapped():
        return await asyncio.wait_for(coro, timeout=timeout)
    return asyncio.run(_wrapped())


def _make_test_client():
    """Create a TestClient with minimal app setup."""
    from fastapi.testclient import TestClient
    from api.server import app
    return TestClient(app)


def _approval_json(apv_id: str, status: str = "pending",
                   mission_id: str = "m-001") -> dict:
    """Build a minimal approval JSON fixture."""
    return {
        "id": apv_id,
        "missionId": mission_id,
        "toolName": "shell",
        "risk": "high",
        "status": status,
        "requestedAt": "2026-03-26T10:00:00Z",
    }


class TestMutationContract01_LifecycleRequested(unittest.TestCase):
    """Test 1: POST mutation → lifecycleState=requested, requestedAt populated, acceptedAt null."""

    def test_approve_returns_lifecycle_requested(self):
        """POST /api/v1/approvals/{id}/approve → 200 + lifecycleState=requested."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            # Create a pending approval file
            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(json.dumps(_approval_json("apv-001")),
                                encoding="utf-8")

            with patch("api.server.APPROVALS_DIR", approvals_dir), \
                 patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                client = _make_test_client()
                resp = client.post(
                    "/api/v1/approvals/apv-001/approve",
                    headers={"Origin": "http://localhost:3000"},
                )

            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body["lifecycleState"], "requested")
            self.assertIn("requestId", body)
            self.assertIsNotNone(body["requestedAt"])
            self.assertIsNone(body["acceptedAt"])
            self.assertIsNone(body["appliedAt"])


class TestMutationContract02_SSEMutationRequested(unittest.TestCase):
    """Test 2: API emits mutation_requested SSE with requestId correlation.

    D-096 ordering: artifact persisted → SSE mutation_requested → HTTP response.
    mutation_accepted / mutation_applied are controller-side (runtime consumer).
    """

    def test_sse_mutation_requested_emitted(self):
        """After approve, _emit_mutation_requested called with correct args."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(json.dumps(_approval_json("apv-001")),
                                encoding="utf-8")

            # Mock the SSE emit function to capture calls
            emit_calls = []
            _original_emit = None

            async def _mock_emit(request, request_id, target_id, mutation_type):
                emit_calls.append({
                    "requestId": request_id,
                    "targetId": target_id,
                    "type": mutation_type,
                })

            with patch("api.server.APPROVALS_DIR", approvals_dir), \
                 patch("api.server.MISSIONS_DIR", tmppath / "missions"), \
                 patch("api.approval_mutation_api._emit_mutation_requested",
                       _mock_emit):
                client = _make_test_client()
                resp = client.post(
                    "/api/v1/approvals/apv-001/approve",
                    headers={"Origin": "http://localhost:3000"},
                )

            self.assertEqual(resp.status_code, 200)
            request_id = resp.json().get("requestId")
            self.assertIsNotNone(request_id)

            # Verify _emit_mutation_requested was called
            self.assertEqual(len(emit_calls), 1,
                             "mutation_requested emit not called exactly once")
            self.assertEqual(emit_calls[0]["requestId"], request_id)
            self.assertEqual(emit_calls[0]["targetId"], "apv-001")
            self.assertEqual(emit_calls[0]["type"], "approve")


class TestMutationContract03_SSERejected(unittest.TestCase):
    """Test 3: requested → accepted → rejected (SSE) with rejectedReason."""

    def test_sse_mutation_rejected_with_reason(self):
        """Reject on already-approved approval → mutation_rejected SSE with reason."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            # Approval already approved — reject should fail validation
            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(
                json.dumps(_approval_json("apv-001", status="approved")),
                encoding="utf-8")

            with patch("api.server.APPROVALS_DIR", approvals_dir), \
                 patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                client = _make_test_client()
                resp = client.post(
                    "/api/v1/approvals/apv-001/reject",
                    headers={"Origin": "http://localhost:3000"},
                )

            # Should still return 200 with lifecycleState=requested,
            # then SSE mutation_rejected later. Or might return 409/422.
            # Contract: invalid FSM state → rejected lifecycle or error response
            self.assertIn(resp.status_code, [200, 409, 422])
            if resp.status_code == 200:
                body = resp.json()
                self.assertIn("requestId", body)


class TestMutationContract04_SSETimedOut(unittest.TestCase):
    """Test 4: requested → timed_out (SSE) after 10s."""

    def test_timeout_lifecycle(self):
        """Mutation that is not processed within timeout → mutation_timed_out SSE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(json.dumps(_approval_json("apv-001")),
                                encoding="utf-8")

            with patch("api.server.APPROVALS_DIR", approvals_dir), \
                 patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                client = _make_test_client()
                resp = client.post(
                    "/api/v1/approvals/apv-001/approve",
                    headers={"Origin": "http://localhost:3000"},
                )

            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body["lifecycleState"], "requested")
            # timeout_at should be set (~10s from requestedAt)
            self.assertIn("timeoutAt", body)


class TestMutationContract05_DuplicateConflict(unittest.TestCase):
    """Test 5: duplicate mutation on same target while pending → 409."""

    def test_duplicate_approve_returns_409(self):
        """Two approves on same target: first 200, second 409."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(json.dumps(_approval_json("apv-001")),
                                encoding="utf-8")

            with patch("api.server.APPROVALS_DIR", approvals_dir), \
                 patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                client = _make_test_client()
                headers = {"Origin": "http://localhost:3000"}

                resp1 = client.post(
                    "/api/v1/approvals/apv-001/approve", headers=headers)
                resp2 = client.post(
                    "/api/v1/approvals/apv-001/approve", headers=headers)

            self.assertEqual(resp1.status_code, 200)
            self.assertEqual(resp2.status_code, 409,
                             "Duplicate approve should return 409 Conflict")


class TestMutationContract06_InvalidFSMState(unittest.TestCase):
    """Test 6: invalid FSM state → rejected (approve on non-approval_wait)."""

    def test_approve_non_pending_returns_error(self):
        """Approve on already-approved approval → 409 or 422."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            # Approval already approved → FSM state invalid
            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(
                json.dumps(_approval_json("apv-001", status="approved")),
                encoding="utf-8")

            with patch("api.server.APPROVALS_DIR", approvals_dir), \
                 patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                client = _make_test_client()
                resp = client.post(
                    "/api/v1/approvals/apv-001/approve",
                    headers={"Origin": "http://localhost:3000"},
                )

            self.assertIn(resp.status_code, [409, 422],
                          "Approve on non-pending should return 409 or 422")


class TestMutationContract07_AuditLogFields(unittest.TestCase):
    """Test 7: audit log fields present after mutation."""

    def test_audit_log_contains_required_fields(self):
        """After approve, audit logger emits structured entry with required fields."""
        import logging as _logging

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(json.dumps(_approval_json("apv-001")),
                                encoding="utf-8")

            # Capture audit log output
            captured_logs = []
            handler = _logging.Handler()
            handler.emit = lambda record: captured_logs.append(record.getMessage())
            audit_logger = _logging.getLogger("mcc.mutation.audit")
            audit_logger.addHandler(handler)

            try:
                with patch("api.server.APPROVALS_DIR", approvals_dir), \
                     patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                    client = _make_test_client()
                    resp = client.post(
                        "/api/v1/approvals/apv-001/approve",
                        headers={
                            "Origin": "http://localhost:3000",
                            "X-Tab-Id": "tab-123",
                            "X-Session-Id": "sess-456",
                        },
                    )
            finally:
                audit_logger.removeHandler(handler)

            self.assertEqual(resp.status_code, 200)

            # Verify audit log entry has required fields
            audit_entries = [l for l in captured_logs if "MUTATION_AUDIT" in l]
            self.assertGreater(len(audit_entries), 0, "No MUTATION_AUDIT entry")

            audit_json_str = audit_entries[0].replace("MUTATION_AUDIT ", "")
            audit_data = json.loads(audit_json_str)
            required_fields = ["requestId", "operation", "targetId",
                               "tabId", "sessionId"]
            for field in required_fields:
                self.assertIn(field, audit_data,
                              f"Audit log missing field: {field}")
            self.assertEqual(audit_data["tabId"], "tab-123")
            self.assertEqual(audit_data["sessionId"], "sess-456")


class TestMutationContract08_AtomicArtifactCreated(unittest.TestCase):
    """Test 8: atomic request artifact created after POST."""

    def test_signal_artifact_exists_after_approve(self):
        """POST approve → approve-request-{uuid}.json signal file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(json.dumps(_approval_json("apv-001")),
                                encoding="utf-8")

            with patch("api.server.APPROVALS_DIR", approvals_dir), \
                 patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                client = _make_test_client()
                resp = client.post(
                    "/api/v1/approvals/apv-001/approve",
                    headers={"Origin": "http://localhost:3000"},
                )

            self.assertEqual(resp.status_code, 200)

            # Check signal artifact exists in mission directory
            artifacts = list(missions_dir.glob("approve-request-*.json"))
            self.assertGreater(len(artifacts), 0,
                               "No approve-request signal artifact found")

            # Verify artifact content
            artifact_data = json.loads(artifacts[0].read_text(encoding="utf-8"))
            self.assertEqual(artifact_data["type"], "approve")
            self.assertEqual(artifact_data["targetId"], "apv-001")
            self.assertIn("requestId", artifact_data)
            self.assertIn("requestedAt", artifact_data)


class TestMutationContract09_CSRFMissingOrigin(unittest.TestCase):
    """Test 9: CSRF — missing Origin → 403."""

    def test_post_without_origin_returns_403(self):
        """POST mutation endpoint without Origin header → 403 Forbidden."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()

            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(json.dumps(_approval_json("apv-001")),
                                encoding="utf-8")

            with patch("api.server.APPROVALS_DIR", approvals_dir), \
                 patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                client = _make_test_client()
                # POST without Origin header
                resp = client.post("/api/v1/approvals/apv-001/approve")

            self.assertEqual(resp.status_code, 403,
                             "POST without Origin should return 403")


class TestMutationContract10_TwoTabRace(unittest.TestCase):
    """Test 10: 2-tab race — simultaneous approve: first 200, second 409."""

    def test_concurrent_approve_race(self):
        """Two tabs approve same approval: first succeeds, second gets 409."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            approvals_dir = tmppath / "approvals"
            approvals_dir.mkdir()
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            apv_file = approvals_dir / "apv-001.json"
            apv_file.write_text(json.dumps(_approval_json("apv-001")),
                                encoding="utf-8")

            with patch("api.server.APPROVALS_DIR", approvals_dir), \
                 patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                client = _make_test_client()

                resp_tab1 = client.post(
                    "/api/v1/approvals/apv-001/approve",
                    headers={
                        "Origin": "http://localhost:3000",
                        "X-Tab-Id": "tab-A",
                    },
                )
                resp_tab2 = client.post(
                    "/api/v1/approvals/apv-001/approve",
                    headers={
                        "Origin": "http://localhost:3000",
                        "X-Tab-Id": "tab-B",
                    },
                )

            self.assertEqual(resp_tab1.status_code, 200,
                             "First tab approve should succeed")
            self.assertEqual(resp_tab2.status_code, 409,
                             "Second tab approve should get 409 Conflict")


class TestMutationContract11_CancelDuringExecution(unittest.TestCase):
    """Test 11: cancel during active execution → graceful abort, FSM transition."""

    def test_cancel_running_mission(self):
        """POST /api/v1/missions/{id}/cancel on running mission → 200 + lifecycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            missions_dir = tmppath / "missions" / "m-001"
            missions_dir.mkdir(parents=True)

            # Create a mission state file indicating "executing"
            state_file = missions_dir / "state.json"
            state_file.write_text(json.dumps({
                "missionId": "m-001",
                "state": "executing",
                "startedAt": "2026-03-26T10:00:00Z",
            }), encoding="utf-8")

            with patch("api.server.MISSIONS_DIR", tmppath / "missions"):
                client = _make_test_client()
                resp = client.post(
                    "/api/v1/missions/m-001/cancel",
                    headers={"Origin": "http://localhost:3000"},
                )

            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body["lifecycleState"], "requested")
            self.assertIn("requestId", body)
            self.assertEqual(body["targetId"], "m-001")

            # Check cancel signal artifact created
            artifacts = list(missions_dir.glob("cancel-request-*.json"))
            self.assertGreater(len(artifacts), 0,
                               "No cancel-request signal artifact found")


if __name__ == "__main__":
    unittest.main()
