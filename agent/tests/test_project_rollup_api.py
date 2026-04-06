"""Tests for project rollup API — D-145 Faz 2B (T75.10).

Tests GET /projects/{id}/rollup endpoint.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.project_api import router, set_store
from persistence.project_store import ProjectStore, ProjectStoreError


@pytest.fixture
def app():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app, tmp_path):
    store_path = tmp_path / "projects.json"
    mission_store = MagicMock()
    mission_store.list.return_value = ([], 0)
    store = ProjectStore(store_path=store_path, mission_store=mission_store)
    set_store(store)
    return TestClient(app), store, mission_store


class TestRollupAPI:
    """T75.10: Rollup API endpoint tests."""

    def test_get_rollup_200(self, client):
        tc, store, _ = client
        proj = store.create("API Test")
        pid = proj["project_id"]
        resp = tc.get(f"/api/v1/projects/{pid}/rollup")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["project_id"] == pid
        assert data["total_missions"] == 0
        assert "computed_at" in data

    def test_get_rollup_with_missions(self, client):
        tc, store, mission_store = client
        proj = store.create("With Missions")
        pid = proj["project_id"]
        missions = [
            {"id": "m1", "status": "completed", "project_id": pid, "total_tokens": 100, "ts": "2026-04-06T10:00:00Z"},
            {"id": "m2", "status": "executing", "project_id": pid, "total_tokens": 50, "ts": "2026-04-06T11:00:00Z"},
        ]
        mission_store.list.return_value = (missions, 2)
        resp = tc.get(f"/api/v1/projects/{pid}/rollup")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_missions"] == 2
        assert data["active_count"] == 1
        assert data["quiescent_count"] == 1
        assert data["total_tokens"] == 150

    def test_get_rollup_404(self, client):
        tc, _, _ = client
        resp = tc.get("/api/v1/projects/nonexistent/rollup")
        assert resp.status_code == 404

    def test_get_rollup_has_meta(self, client):
        tc, store, _ = client
        proj = store.create("Meta Test")
        resp = tc.get(f"/api/v1/projects/{proj['project_id']}/rollup")
        assert "meta" in resp.json()
        assert "generatedAt" in resp.json()["meta"]

    def test_get_rollup_by_status_breakdown(self, client):
        tc, store, mission_store = client
        proj = store.create("Breakdown")
        pid = proj["project_id"]
        missions = [
            {"id": "m1", "status": "completed", "project_id": pid, "total_tokens": 0, "ts": "t1"},
            {"id": "m2", "status": "completed", "project_id": pid, "total_tokens": 0, "ts": "t2"},
            {"id": "m3", "status": "failed", "project_id": pid, "total_tokens": 0, "ts": "t3"},
        ]
        mission_store.list.return_value = (missions, 3)
        resp = tc.get(f"/api/v1/projects/{pid}/rollup")
        data = resp.json()["data"]
        assert data["by_status"]["completed"] == 2
        assert data["by_status"]["failed"] == 1
