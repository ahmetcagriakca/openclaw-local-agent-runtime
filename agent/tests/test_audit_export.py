"""Tests for audit export — B-115 (Sprint 55).

Covers: export logic, filtering, redaction, fail-closed, checksum, CSV.
"""
import json

# Setup path for imports
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

AGENT_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = AGENT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "tools"))
sys.path.insert(0, str(AGENT_DIR))

from audit_export import (
    MAX_MISSIONS,
    _in_range,
    _load_approvals,
    _load_audit_log,
    _load_dlq,
    _load_missions,
    _parse_ts,
    _redact_dict,
    _sha256,
    _to_csv,
    export_audit,
)

# ── Redaction tests ──────────────────────────────────────────────


class TestRedaction:
    def test_redacts_api_key(self):
        d = {"name": "test", "api_key": "sk-123", "value": "ok"}
        result = _redact_dict(d)
        assert result["api_key"] == "[REDACTED]"
        assert result["name"] == "test"
        assert result["value"] == "ok"

    def test_redacts_secret(self):
        d = {"my_secret": "hidden", "public": "visible"}
        result = _redact_dict(d)
        assert result["my_secret"] == "[REDACTED]"
        assert result["public"] == "visible"

    def test_redacts_nested(self):
        d = {"config": {"api_key": "sk-123", "host": "localhost"}}
        result = _redact_dict(d)
        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["config"]["host"] == "localhost"

    def test_redacts_in_list(self):
        d = {"items": [{"token": "abc"}, {"name": "ok"}]}
        result = _redact_dict(d)
        assert result["items"][0]["token"] == "[REDACTED]"
        assert result["items"][1]["name"] == "ok"

    def test_redacts_password(self):
        d = {"password": "p@ss", "username": "admin"}
        result = _redact_dict(d)
        assert result["password"] == "[REDACTED]"
        assert result["username"] == "admin"

    def test_redacts_llm_response(self):
        d = {"llm_response": "long text...", "status": "ok"}
        result = _redact_dict(d)
        assert result["llm_response"] == "[REDACTED]"

    def test_preserves_non_sensitive(self):
        d = {"id": "m-1", "goal": "test", "status": "completed"}
        result = _redact_dict(d)
        assert result == d


# ── Timestamp filtering tests ────────────────────────────────────


class TestTimestampFiltering:
    def test_parse_ts_valid(self):
        dt = _parse_ts("2026-01-15T10:00:00")
        assert dt is not None
        assert dt.year == 2026

    def test_parse_ts_none(self):
        assert _parse_ts(None) is None

    def test_parse_ts_invalid(self):
        assert _parse_ts("not-a-date") is None

    def test_in_range_no_filters(self):
        assert _in_range("2026-01-15T10:00:00", None, None) is True

    def test_in_range_from_only(self):
        from_dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert _in_range("2026-01-15T10:00:00", from_dt, None) is True
        assert _in_range("2025-12-31T10:00:00", from_dt, None) is False

    def test_in_range_to_only(self):
        to_dt = datetime(2026, 6, 1, tzinfo=timezone.utc)
        assert _in_range("2026-01-15T10:00:00", None, to_dt) is True
        assert _in_range("2026-07-01T10:00:00", None, to_dt) is False

    def test_in_range_both(self):
        from_dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        to_dt = datetime(2026, 6, 1, tzinfo=timezone.utc)
        assert _in_range("2026-03-15T10:00:00", from_dt, to_dt) is True
        assert _in_range("2025-12-01T10:00:00", from_dt, to_dt) is False
        assert _in_range("2026-07-01T10:00:00", from_dt, to_dt) is False

    def test_in_range_none_ts_no_filter(self):
        assert _in_range(None, None, None) is True

    def test_in_range_none_ts_with_filter(self):
        from_dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert _in_range(None, from_dt, None) is False


# ── SHA-256 tests ────────────────────────────────────────────────


class TestSha256:
    def test_sha256_empty(self):
        h = _sha256(b"")
        assert len(h) == 64

    def test_sha256_deterministic(self):
        h1 = _sha256(b"test data")
        h2 = _sha256(b"test data")
        assert h1 == h2

    def test_sha256_different(self):
        h1 = _sha256(b"data1")
        h2 = _sha256(b"data2")
        assert h1 != h2


# ── CSV conversion tests ────────────────────────────────────────


class TestCsv:
    def test_csv_empty(self):
        assert _to_csv([], "test") == ""

    def test_csv_basic(self):
        records = [{"id": "1", "name": "test"}]
        csv_str = _to_csv(records, "test")
        assert "id" in csv_str
        assert "name" in csv_str
        assert "test" in csv_str

    def test_csv_nested_dict(self):
        records = [{"id": "1", "meta": {"key": "val"}}]
        csv_str = _to_csv(records, "test")
        assert "meta" in csv_str


# ── Data loading tests ───────────────────────────────────────────


class TestLoadMissions:
    def test_load_from_empty_dir(self, tmp_path):
        with patch("audit_export.MISSION_HISTORY", tmp_path / "none.json"), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "missions"):
            result = _load_missions()
            assert result == []

    def test_load_from_history_file(self, tmp_path):
        history = tmp_path / "history.json"
        history.write_text(json.dumps([
            {"id": "m-1", "goal": "test", "ts": "2026-01-15T10:00:00"},
            {"id": "m-2", "goal": "test2", "ts": "2026-02-15T10:00:00"},
        ]))
        missions_dir = tmp_path / "missions"
        missions_dir.mkdir()
        with patch("audit_export.MISSION_HISTORY", history), \
             patch("audit_export.MISSIONS_DIR", missions_dir):
            result = _load_missions()
            assert len(result) == 2

    def test_filter_by_mission_id(self, tmp_path):
        history = tmp_path / "history.json"
        history.write_text(json.dumps([
            {"id": "m-1", "goal": "test1"},
            {"id": "m-2", "goal": "test2"},
        ]))
        with patch("audit_export.MISSION_HISTORY", history), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "m"):
            result = _load_missions(mission_id="m-1")
            assert len(result) == 1
            assert result[0]["id"] == "m-1"

    def test_filter_by_user_id(self, tmp_path):
        history = tmp_path / "history.json"
        history.write_text(json.dumps([
            {"id": "m-1", "operator": "akca"},
            {"id": "m-2", "operator": "other"},
        ]))
        with patch("audit_export.MISSION_HISTORY", history), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "m"):
            result = _load_missions(user_id="akca")
            assert len(result) == 1

    def test_max_missions_limit(self, tmp_path):
        history = tmp_path / "history.json"
        missions = [{"id": f"m-{i}", "goal": f"test-{i}"}
                    for i in range(MAX_MISSIONS + 50)]
        history.write_text(json.dumps(missions))
        with patch("audit_export.MISSION_HISTORY", history), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "m"):
            result = _load_missions()
            assert len(result) == MAX_MISSIONS

    def test_redaction_applied(self, tmp_path):
        history = tmp_path / "history.json"
        history.write_text(json.dumps([
            {"id": "m-1", "api_key": "secret-key", "goal": "test"},
        ]))
        with patch("audit_export.MISSION_HISTORY", history), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "m"):
            result = _load_missions()
            assert result[0]["api_key"] == "[REDACTED]"


class TestLoadDlq:
    def test_load_empty(self, tmp_path):
        with patch("audit_export.DLQ_PATH", tmp_path / "none.json"):
            assert _load_dlq() == []

    def test_load_entries(self, tmp_path):
        dlq = tmp_path / "dlq.json"
        dlq.write_text(json.dumps([
            {"dlq_id": "d-1", "mission_id": "m-1", "failed_at": "2026-01-15"},
        ]))
        with patch("audit_export.DLQ_PATH", dlq):
            result = _load_dlq()
            assert len(result) == 1


class TestLoadAuditLog:
    def test_load_empty(self, tmp_path):
        with patch("audit_export.AUDIT_LOG", tmp_path / "none.jsonl"):
            assert _load_audit_log() == []

    def test_load_entries(self, tmp_path):
        log = tmp_path / "audit.jsonl"
        entries = [
            {"timestamp": "2026-01-15T10:00:00", "event": "mission.start",
             "actor": "akca"},
            {"timestamp": "2026-01-15T11:00:00", "event": "mission.complete",
             "actor": "akca"},
        ]
        log.write_text("\n".join(json.dumps(e) for e in entries))
        with patch("audit_export.AUDIT_LOG", log):
            result = _load_audit_log()
            assert len(result) == 2


class TestLoadApprovals:
    def test_load_empty(self, tmp_path):
        with patch("audit_export.APPROVALS_DIR", tmp_path / "none"):
            assert _load_approvals() == []

    def test_load_approvals(self, tmp_path):
        apv_dir = tmp_path / "approvals"
        apv_dir.mkdir()
        (apv_dir / "apv-1.json").write_text(json.dumps({
            "id": "apv-1", "missionId": "m-1", "status": "approved",
            "requestedAt": "2026-01-15T10:00:00",
        }))
        with patch("audit_export.APPROVALS_DIR", apv_dir):
            result = _load_approvals()
            assert len(result) == 1


# ── Full export tests ────────────────────────────────────────────


class TestExportAudit:
    def test_export_creates_zip(self, tmp_path):
        with patch("audit_export.MISSION_HISTORY", tmp_path / "none.json"), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "missions"), \
             patch("audit_export.DLQ_PATH", tmp_path / "dlq.json"), \
             patch("audit_export.AUDIT_LOG", tmp_path / "audit.jsonl"), \
             patch("audit_export.APPROVALS_DIR", tmp_path / "approvals"), \
             patch("audit_export.POLICIES_DIR", tmp_path / "policies"):
            result = export_audit(output_dir=tmp_path / "out")
            assert Path(result["archive"]).exists()
            assert result["archive"].endswith(".zip")
            assert len(result["checksum"]) == 64

    def test_export_contains_manifest(self, tmp_path):
        with patch("audit_export.MISSION_HISTORY", tmp_path / "none.json"), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "missions"), \
             patch("audit_export.DLQ_PATH", tmp_path / "dlq.json"), \
             patch("audit_export.AUDIT_LOG", tmp_path / "audit.jsonl"), \
             patch("audit_export.APPROVALS_DIR", tmp_path / "approvals"), \
             patch("audit_export.POLICIES_DIR", tmp_path / "policies"):
            result = export_audit(output_dir=tmp_path / "out")
            with zipfile.ZipFile(result["archive"]) as zf:
                names = zf.namelist()
                assert "manifest.json" in names
                assert "missions.json" in names
                assert "dlq-events.json" in names
                assert "audit-log.json" in names
                assert "approvals.json" in names

    def test_export_with_data(self, tmp_path):
        # Setup mission data
        history = tmp_path / "history.json"
        history.write_text(json.dumps([
            {"id": "m-1", "goal": "test mission", "status": "completed",
             "ts": "2026-01-15T10:00:00"},
        ]))
        missions_dir = tmp_path / "missions"
        missions_dir.mkdir()

        with patch("audit_export.MISSION_HISTORY", history), \
             patch("audit_export.MISSIONS_DIR", missions_dir), \
             patch("audit_export.DLQ_PATH", tmp_path / "dlq.json"), \
             patch("audit_export.AUDIT_LOG", tmp_path / "audit.jsonl"), \
             patch("audit_export.APPROVALS_DIR", tmp_path / "approvals"), \
             patch("audit_export.POLICIES_DIR", tmp_path / "policies"):
            result = export_audit(output_dir=tmp_path / "out")
            assert result["counts"]["missions"] == 1
            assert result["total_records"] >= 1

    def test_export_with_csv(self, tmp_path):
        history = tmp_path / "history.json"
        history.write_text(json.dumps([
            {"id": "m-1", "goal": "test", "ts": "2026-01-15"},
        ]))
        with patch("audit_export.MISSION_HISTORY", history), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "m"), \
             patch("audit_export.DLQ_PATH", tmp_path / "dlq.json"), \
             patch("audit_export.AUDIT_LOG", tmp_path / "audit.jsonl"), \
             patch("audit_export.APPROVALS_DIR", tmp_path / "approvals"), \
             patch("audit_export.POLICIES_DIR", tmp_path / "policies"):
            result = export_audit(output_dir=tmp_path / "out",
                                  include_csv=True)
            with zipfile.ZipFile(result["archive"]) as zf:
                assert "missions.csv" in zf.namelist()

    def test_export_checksum_valid(self, tmp_path):
        with patch("audit_export.MISSION_HISTORY", tmp_path / "none.json"), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "missions"), \
             patch("audit_export.DLQ_PATH", tmp_path / "dlq.json"), \
             patch("audit_export.AUDIT_LOG", tmp_path / "audit.jsonl"), \
             patch("audit_export.APPROVALS_DIR", tmp_path / "approvals"), \
             patch("audit_export.POLICIES_DIR", tmp_path / "policies"):
            result = export_audit(output_dir=tmp_path / "out")
            import hashlib
            actual = hashlib.sha256(
                Path(result["archive"]).read_bytes()
            ).hexdigest()
            assert actual == result["checksum"]

    def test_export_filter_by_mission(self, tmp_path):
        history = tmp_path / "history.json"
        history.write_text(json.dumps([
            {"id": "m-1", "goal": "first"},
            {"id": "m-2", "goal": "second"},
        ]))
        with patch("audit_export.MISSION_HISTORY", history), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "m"), \
             patch("audit_export.DLQ_PATH", tmp_path / "dlq.json"), \
             patch("audit_export.AUDIT_LOG", tmp_path / "audit.jsonl"), \
             patch("audit_export.APPROVALS_DIR", tmp_path / "approvals"), \
             patch("audit_export.POLICIES_DIR", tmp_path / "policies"):
            result = export_audit(output_dir=tmp_path / "out",
                                  mission_id="m-1")
            assert result["counts"]["missions"] == 1

    def test_export_redaction_in_archive(self, tmp_path):
        history = tmp_path / "history.json"
        history.write_text(json.dumps([
            {"id": "m-1", "api_key": "secret-123", "goal": "test"},
        ]))
        with patch("audit_export.MISSION_HISTORY", history), \
             patch("audit_export.MISSIONS_DIR", tmp_path / "m"), \
             patch("audit_export.DLQ_PATH", tmp_path / "dlq.json"), \
             patch("audit_export.AUDIT_LOG", tmp_path / "audit.jsonl"), \
             patch("audit_export.APPROVALS_DIR", tmp_path / "approvals"), \
             patch("audit_export.POLICIES_DIR", tmp_path / "policies"):
            result = export_audit(output_dir=tmp_path / "out")
            with zipfile.ZipFile(result["archive"]) as zf:
                missions = json.loads(zf.read("missions.json"))
                assert missions[0]["api_key"] == "[REDACTED]"
                assert "secret-123" not in zf.read("missions.json").decode()


# ── API endpoint tests ───────────────────────────────────────────


class TestAuditExportAPI:
    """Tests for audit export API router."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        sys.path.insert(0, str(AGENT_DIR))
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.audit_export_api import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        return TestClient(app)

    def test_list_exports_empty(self, client, tmp_path):
        with patch("api.audit_export_api.EXPORT_DIR", tmp_path / "none"):
            resp = client.get("/api/v1/audit/exports")
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] == 0
            assert "meta" in data

    def test_list_exports_with_files(self, client, tmp_path):
        export_dir = tmp_path / "exports"
        export_dir.mkdir()
        dummy = export_dir / "audit-export-20260101-120000.zip"
        dummy.write_bytes(b"fake zip")
        with patch("api.audit_export_api.EXPORT_DIR", export_dir):
            resp = client.get("/api/v1/audit/exports")
            assert resp.status_code == 200
            assert resp.json()["count"] == 1
