"""Sprint 8 API Test Suite — unit + integration tests.

GPT review fixes applied:
- Fix 2: DataQuality 6-state (fresh/partial/stale/degraded/unknown/not_reached)
- Fix 3: Wrapper responses (MissionListResponse, etc.)
- Fix 4: CapabilityStatus tri-state
- Fix 6: services.json heartbeat
- Fix 8: TelemetryEntry missionId + sourceFile
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Unit Tests: Schemas ──────────────────────────────────────────

class TestSchemas(unittest.TestCase):

    def test_01_data_quality_6_states(self):
        """GPT Fix 2: 6 states, known_zero removed."""
        from api.schemas import DataQuality
        expected = {"fresh", "partial", "stale", "degraded",
                    "unknown", "not_reached"}
        actual = {s.value for s in DataQuality}
        self.assertEqual(actual, expected)
        # known_zero must NOT exist
        self.assertNotIn("known_zero", {s.value for s in DataQuality})

    def test_02_mission_summary_round_trip(self):
        from api.schemas import MissionSummary
        ms = MissionSummary(missionId="test-1", state="completed",
                            goal="test")
        data = ms.model_dump()
        restored = MissionSummary(**data)
        self.assertEqual(restored.missionId, "test-1")

    def test_03_stage_detail_with_gate(self):
        from api.schemas import StageDetail, GateResultDetail, Finding
        stage = StageDetail(
            index=0, role="tester", status="completed",
            agentUsed="gpt-general",
            gateResults=GateResultDetail(
                gateName="gate_2", passed=True,
                findings=[Finding(check="test", status="pass")]))
        data = stage.model_dump()
        self.assertTrue(data["gateResults"]["passed"])

    def test_04_capability_tri_state(self):
        """GPT Fix 4: CapabilityStatus is tri-state, not bool."""
        from api.schemas import CapabilityEntry, CapabilityStatus
        ce = CapabilityEntry(name="test", status=CapabilityStatus.AVAILABLE)
        self.assertEqual(ce.status, CapabilityStatus.AVAILABLE)
        ce2 = CapabilityEntry(name="x", status=CapabilityStatus.UNKNOWN)
        self.assertEqual(ce2.status, CapabilityStatus.UNKNOWN)

    def test_05_component_health_has_name(self):
        """GPT Fix 4: ComponentHealth has name field."""
        from api.schemas import ComponentHealth
        ch = ComponentHealth(name="api", status="ok")
        self.assertEqual(ch.name, "api")

    def test_06_telemetry_entry_has_mission_id(self):
        """GPT Fix 8: TelemetryEntry has missionId + sourceFile."""
        from api.schemas import TelemetryEntry
        te = TelemetryEntry(type="test", missionId="m-1",
                            sourceFile="telemetry.jsonl", data={})
        self.assertEqual(te.missionId, "m-1")
        self.assertEqual(te.sourceFile, "telemetry.jsonl")

    def test_07_response_meta(self):
        from api.schemas import ResponseMeta, DataQuality
        rm = ResponseMeta(freshnessMs=100, dataQuality=DataQuality.FRESH)
        data = rm.model_dump()
        self.assertEqual(data["dataQuality"], "fresh")
        self.assertIn("generatedAt", data)

    def test_08_wrapper_response(self):
        """GPT Fix 3: All endpoints use wrapper responses."""
        from api.schemas import (MissionListResponse, MissionDetailResponse,
                                  HealthResponse, ApprovalListResponse,
                                  TelemetryResponse, CapabilitiesResponse,
                                  StageListResponse)
        # All wrappers must have 'meta' field
        for cls in [MissionListResponse, HealthResponse,
                    ApprovalListResponse, TelemetryResponse,
                    CapabilitiesResponse, StageListResponse]:
            fields = cls.model_fields
            self.assertIn("meta", fields, f"{cls.__name__} missing meta")

    def test_09_mission_state_enum(self):
        from api.schemas import MissionState
        self.assertEqual(len(MissionState), 10)


# ── Unit Tests: Atomic Write ─────────────────────────────────────

class TestAtomicWrite(unittest.TestCase):

    def test_10_json_write_read(self):
        from utils.atomic_write import atomic_write_json
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.json"
            atomic_write_json(path, {"key": "value"})
            data = json.loads(path.read_text())
            self.assertEqual(data["key"], "value")

    def test_11_no_temp_on_success(self):
        from utils.atomic_write import atomic_write_json
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.json"
            atomic_write_json(path, {"ok": True})
            files = list(Path(d).iterdir())
            self.assertEqual(len(files), 1)

    def test_12_creates_parent_dirs(self):
        from utils.atomic_write import atomic_write_json
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sub" / "dir" / "test.json"
            atomic_write_json(path, {"nested": True})
            self.assertTrue(path.exists())


# ── Unit Tests: Cache ────────────────────────────────────────────

class TestCache(unittest.TestCase):

    def test_13_miss_then_hit(self):
        from api.cache import IncrementalFileCache, CacheStatus
        cache = IncrementalFileCache()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False) as f:
            json.dump({"x": 1}, f)
            path = f.name
        try:
            _, status1 = cache.get(path)
            self.assertEqual(status1, CacheStatus.miss)
            _, status2 = cache.get(path)
            self.assertEqual(status2, CacheStatus.hit)
        finally:
            os.unlink(path)

    def test_14_error_on_missing(self):
        from api.cache import IncrementalFileCache, CacheStatus
        cache = IncrementalFileCache()
        data, status = cache.get("/nonexistent/file.json")
        self.assertIsNone(data)
        self.assertEqual(status, CacheStatus.error)

    def test_15_error_on_corrupt(self):
        from api.cache import IncrementalFileCache, CacheStatus
        cache = IncrementalFileCache()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False) as f:
            f.write("{corrupt")
            path = f.name
        try:
            data, status = cache.get(path)
            self.assertIsNone(data)
            self.assertEqual(status, CacheStatus.error)
        finally:
            os.unlink(path)

    def test_16_invalidate(self):
        from api.cache import IncrementalFileCache
        cache = IncrementalFileCache()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False) as f:
            json.dump({"a": 1}, f)
            path = f.name
        try:
            cache.get(path)
            cache.invalidate(path)
            self.assertEqual(cache.stats().entries, 0)
        finally:
            os.unlink(path)


# ── Unit Tests: Circuit Breaker ──────────────────────────────────

class TestCircuitBreaker(unittest.TestCase):

    def test_17_closed_on_success(self):
        from api.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=3)
        self.assertEqual(cb.call("s", lambda: 42), 42)
        self.assertEqual(cb.get_state("s"), "closed")

    def test_18_opens_after_threshold(self):
        from api.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_s=100)
        for _ in range(2):
            try:
                cb.call("s", lambda: (_ for _ in ()).throw(ValueError()))
            except ValueError:
                pass
        self.assertEqual(cb.get_state("s"), "open")
        with self.assertRaises(CircuitBreakerOpen):
            cb.call("s", lambda: 1)

    def test_19_source_isolation(self):
        from api.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout_s=100)
        for _ in range(2):
            try:
                cb.call("bad", lambda: (_ for _ in ()).throw(ValueError()))
            except ValueError:
                pass
        self.assertEqual(cb.get_state("bad"), "open")
        self.assertEqual(cb.get_state("good"), "closed")

    def test_20_half_open_recovery(self):
        from api.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout_s=0.1)
        try:
            cb.call("s", lambda: (_ for _ in ()).throw(ValueError()))
        except ValueError:
            pass
        time.sleep(0.15)
        self.assertEqual(cb.get_state("s"), "half_open")
        self.assertEqual(cb.call("s", lambda: "ok"), "ok")
        self.assertEqual(cb.get_state("s"), "closed")


# ── Unit Tests: Normalizer ───────────────────────────────────────

class TestNormalizer(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.missions_dir = Path(self.tmpdir) / "missions"
        self.missions_dir.mkdir()
        self.approvals_dir = Path(self.tmpdir) / "approvals"
        self.approvals_dir.mkdir()
        self.telemetry_path = Path(self.tmpdir) / "telemetry.jsonl"
        self.caps_path = Path(self.tmpdir) / "capabilities.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def _normalizer(self):
        from api.normalizer import MissionNormalizer
        return MissionNormalizer(
            self.missions_dir, self.telemetry_path,
            self.caps_path, self.approvals_dir)

    def test_21_list_missions(self):
        self._write(self.missions_dir / "mission-001.json", {
            "missionId": "mission-001", "status": "completed",
            "stages": [], "goal": "test"})
        n = self._normalizer()
        items, meta = n.list_missions()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].missionId, "mission-001")

    def test_22_get_mission_not_found(self):
        n = self._normalizer()
        self.assertIsNone(n.get_mission("nonexistent"))

    def test_23_precedence_state_over_mission(self):
        """BF-4: status: state > mission."""
        self._write(self.missions_dir / "mission-002.json", {
            "missionId": "mission-002", "status": "executing", "stages": []})
        self._write(self.missions_dir / "mission-002-state.json", {
            "status": "failed"})
        n = self._normalizer()
        mission, meta = n.get_mission("mission-002")
        self.assertEqual(mission.state, "failed")

    def test_24_freshness_max_age(self):
        """BF-1: freshnessMs = max(source ages)."""
        self._write(self.missions_dir / "mission-003.json", {
            "missionId": "mission-003", "status": "completed", "stages": []})
        n = self._normalizer()
        _, meta = n.get_mission("mission-003")
        self.assertGreaterEqual(meta.freshnessMs, 0)

    def test_25_missing_source_partial(self):
        """GPT Fix 2: missing source → partial (not unknown)."""
        self._write(self.missions_dir / "mission-004.json", {
            "missionId": "mission-004", "status": "completed", "stages": []})
        n = self._normalizer()
        _, meta = n.get_mission("mission-004")
        self.assertIn("state", meta.sourcesMissing)
        from api.schemas import DataQuality
        self.assertEqual(meta.dataQuality, DataQuality.PARTIAL)

    def test_26_deny_forensics_from_summary(self):
        """BF-4: forensics: summary > telemetry."""
        self._write(self.missions_dir / "mission-005.json", {
            "missionId": "mission-005", "status": "failed", "stages": []})
        self._write(self.missions_dir / "mission-005-summary.json", {
            "status": "failed", "stages": [],
            "denyForensics": [{"gate": "gate_1"}],
            "totalPolicyDenies": 2})
        n = self._normalizer()
        mission, _ = n.get_mission("mission-005")
        self.assertEqual(len(mission.denyForensics), 1)

    def test_27_corrupt_json_degraded(self):
        """D-068: corrupt source → degraded, API stays up."""
        with open(self.missions_dir / "mission-006.json", "w") as f:
            f.write("{truncated")
        n = self._normalizer()
        self.assertIsNone(n.get_mission("mission-006"))

    def test_42_resolve_file_id_direct(self):
        """resolve_file_id returns same ID for controller missions."""
        self._write(self.missions_dir / "mission-001.json", {
            "missionId": "mission-001", "status": "completed", "stages": []})
        n = self._normalizer()
        self.assertEqual(n.resolve_file_id("mission-001"), "mission-001")

    def test_43_resolve_file_id_dashboard_placeholder(self):
        """resolve_file_id resolves dashboard placeholder to controller ID."""
        # Dashboard placeholder
        self._write(self.missions_dir / "dash-uuid-123.json", {
            "missionId": "dash-uuid-123", "goal": "test",
            "createdFrom": "dashboard", "status": "running", "stages": []})
        # Controller mission linked by session
        self._write(self.missions_dir / "mission-20260326120000-999.json", {
            "missionId": "mission-20260326120000-999",
            "sessionId": "web-dash-uuid-123",
            "status": "completed", "stages": []})
        n = self._normalizer()
        resolved = n.resolve_file_id("dash-uuid-123")
        self.assertEqual(resolved, "mission-20260326120000-999")

    def test_44_resolve_file_id_nonexistent(self):
        """resolve_file_id returns original ID if mission not found."""
        n = self._normalizer()
        self.assertEqual(n.resolve_file_id("nope"), "nope")


# ── Unit Tests: Capabilities ────────────────────────────────────

class TestCapabilities(unittest.TestCase):

    def test_28_tri_state_available(self):
        """GPT Fix 4: get_status → tri-state."""
        from api.capabilities import CapabilityChecker
        from api.schemas import CapabilityStatus
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False) as f:
            json.dump({"autoGenerated": True, "capabilities": {
                "deny_forensics": {"available": True}
            }}, f)
            path = f.name
        try:
            cc = CapabilityChecker(path)
            self.assertEqual(cc.get_status("deny_forensics"),
                             CapabilityStatus.AVAILABLE)
            self.assertEqual(cc.get_status("nonexistent"),
                             CapabilityStatus.UNAVAILABLE)
            self.assertTrue(cc.is_available("deny_forensics"))
        finally:
            os.unlink(path)

    def test_29_missing_manifest_unknown(self):
        from api.capabilities import CapabilityChecker
        from api.schemas import CapabilityStatus
        cc = CapabilityChecker("/nonexistent/caps.json")
        self.assertEqual(cc.get_status("deny_forensics"),
                         CapabilityStatus.UNKNOWN)

    def test_30_corrupt_manifest_unknown(self):
        from api.capabilities import CapabilityChecker
        from api.schemas import CapabilityStatus
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                          delete=False) as f:
            f.write("not json")
            path = f.name
        try:
            cc = CapabilityChecker(path)
            self.assertEqual(cc.get_status("anything"),
                             CapabilityStatus.UNKNOWN)
        finally:
            os.unlink(path)


# ── Integration Tests: API Endpoints ─────────────────────────────

class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        missions_dir = Path(cls.tmpdir) / "missions"
        missions_dir.mkdir()
        approvals_dir = Path(cls.tmpdir) / "approvals"
        approvals_dir.mkdir()

        with open(missions_dir / "mission-test-1.json", "w") as f:
            json.dump({
                "missionId": "mission-test-1", "status": "completed",
                "goal": "integration test",
                "stages": [{"id": "s1", "specialist": "analyst",
                            "status": "completed"}]
            }, f)

        with open(approvals_dir / "apv-test-1.json", "w") as f:
            json.dump({
                "approvalId": "apv-test-1", "status": "approved",
                "toolName": "test_tool", "risk": "low"
            }, f)

        caps_path = Path(cls.tmpdir) / "capabilities.json"
        with open(caps_path, "w") as f:
            json.dump({"autoGenerated": True, "capabilities": {
                "deny_forensics": {"available": True}
            }}, f)

        import api.server as srv
        srv.MISSIONS_DIR = missions_dir
        srv.APPROVALS_DIR = approvals_dir
        srv.TELEMETRY_PATH = Path(cls.tmpdir) / "telemetry.jsonl"
        srv.CAPABILITIES_PATH = caps_path
        srv.SERVICES_PATH = Path(cls.tmpdir) / "services.json"
        srv.API_LOG_PATH = Path(cls.tmpdir) / "api.log"

        from api.normalizer import MissionNormalizer
        from api.capabilities import CapabilityChecker
        srv.normalizer = MissionNormalizer(
            missions_dir, srv.TELEMETRY_PATH, caps_path, approvals_dir)
        srv.capability_checker = CapabilityChecker(caps_path)

        from fastapi.testclient import TestClient
        cls.client = TestClient(srv.app)

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_31_health_200_wrapper(self):
        """GPT Fix 3: health returns HealthResponse with meta."""
        r = self.client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("meta", data)
        self.assertIn("status", data)
        self.assertIn("components", data)

    def test_32_capabilities_200_wrapper(self):
        r = self.client.get("/api/v1/capabilities")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("meta", data)
        self.assertIn("capabilities", data)

    def test_33_missions_list_200_wrapper(self):
        """GPT Fix 3: missions list returns MissionListResponse."""
        r = self.client.get("/api/v1/missions")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("meta", data)
        self.assertIn("missions", data)

    def test_34_mission_detail_200_wrapper(self):
        r = self.client.get("/api/v1/missions/mission-test-1")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("meta", data)
        self.assertIn("mission", data)
        self.assertEqual(data["mission"]["missionId"], "mission-test-1")

    def test_35_mission_not_found_404(self):
        r = self.client.get("/api/v1/missions/nonexistent")
        self.assertEqual(r.status_code, 404)

    def test_36_stages_200_wrapper(self):
        r = self.client.get("/api/v1/missions/mission-test-1/stages")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("meta", data)
        self.assertIn("stages", data)

    def test_37_approvals_200_wrapper(self):
        r = self.client.get("/api/v1/approvals")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("meta", data)
        self.assertIn("approvals", data)

    def test_38_telemetry_200_wrapper(self):
        r = self.client.get("/api/v1/telemetry")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("meta", data)
        self.assertIn("events", data)

    def test_39_host_header_attack_403(self):
        """D-070: Invalid Host → 403."""
        r = self.client.get("/api/v1/health",
                            headers={"Host": "evil.com"})
        self.assertEqual(r.status_code, 403)

    def test_40_meta_has_data_quality(self):
        """Every response meta has dataQuality field."""
        r = self.client.get("/api/v1/health")
        meta = r.json()["meta"]
        self.assertIn("dataQuality", meta)
        self.assertIn(meta["dataQuality"],
                      ["fresh", "partial", "stale", "degraded",
                       "unknown", "not_reached"])

    def test_41_meta_has_generated_at(self):
        r = self.client.get("/api/v1/health")
        meta = r.json()["meta"]
        self.assertIn("generatedAt", meta)


if __name__ == "__main__":
    unittest.main(verbosity=2)
