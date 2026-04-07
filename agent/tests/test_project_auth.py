"""Tests for project API auth enforcement — S76 P1.6.

Negative auth tests: 401 without auth, 403 for viewer, 200 for operator.
Tests run with VEZIR_AUTH_BYPASS unset to enforce auth.
"""
import json
import os

import pytest
from conftest import CSRF_ORIGIN
from fastapi.testclient import TestClient


@pytest.fixture
def auth_client(tmp_path):
    """Create test client with auth enabled (keys configured)."""
    # Create auth.json with test keys
    auth_config = {
        "keys": [
            {"key": "op_key_001", "name": "operator", "role": "operator", "created": "2026-04-06"},
            {"key": "vw_key_001", "name": "viewer", "role": "viewer", "created": "2026-04-06"},
        ]
    }
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    auth_path = config_dir / "auth.json"
    auth_path.write_text(json.dumps(auth_config))

    from persistence.mission_store import MissionStore
    from persistence.project_store import ProjectStore

    ms = MissionStore(store_path=tmp_path / "missions.json")
    ps = ProjectStore(store_path=tmp_path / "projects.json", mission_store=ms)

    from api import project_api
    project_api.set_store(ps)

    # Patch keys to load from our test config
    import auth.keys as keys_mod
    keys_mod._loaded = False
    keys_mod._keys = {}
    original_load = keys_mod._load_keys

    def _test_load():
        data = json.loads(auth_path.read_text())
        keys_mod._keys = {
            e["key"]: keys_mod.ApiKey(
                key=e["key"], name=e["name"], role=e["role"],
                created=e.get("created", ""),
            )
            for e in data.get("keys", [])
        }
        keys_mod._loaded = True

    keys_mod._load_keys = _test_load
    keys_mod._load_keys()

    # Temporarily unset bypass
    old_bypass = os.environ.pop("VEZIR_AUTH_BYPASS", None)

    from api.server import app
    client = TestClient(app)

    yield client, ps

    # Restore
    keys_mod._load_keys = original_load
    keys_mod._loaded = False
    keys_mod._keys = {}
    if old_bypass is not None:
        os.environ["VEZIR_AUTH_BYPASS"] = old_bypass


OPERATOR_HEADERS = {
    "Authorization": "Bearer op_key_001",
    "Origin": CSRF_ORIGIN,
}
VIEWER_HEADERS = {
    "Authorization": "Bearer vw_key_001",
    "Origin": CSRF_ORIGIN,
}
NO_AUTH_HEADERS = {
    "Origin": CSRF_ORIGIN,
}


class TestProjectCreateAuth:
    """P1.6: POST /projects requires operator."""

    def test_create_no_auth_401(self, auth_client):
        c, _ = auth_client
        resp = c.post("/api/v1/projects", json={"name": "X"}, headers=NO_AUTH_HEADERS)
        assert resp.status_code == 401

    def test_create_viewer_403(self, auth_client):
        c, _ = auth_client
        resp = c.post("/api/v1/projects", json={"name": "X"}, headers=VIEWER_HEADERS)
        assert resp.status_code == 403

    def test_create_operator_201(self, auth_client):
        c, _ = auth_client
        resp = c.post("/api/v1/projects", json={"name": "Auth Test"}, headers=OPERATOR_HEADERS)
        assert resp.status_code == 201


class TestProjectUpdateAuth:
    """P1.6: PATCH /projects/{id} requires operator."""

    def test_update_no_auth_401(self, auth_client):
        c, store = auth_client
        proj = store.create("Upd Test")
        resp = c.patch(f"/api/v1/projects/{proj['project_id']}", json={"name": "Y"}, headers=NO_AUTH_HEADERS)
        assert resp.status_code == 401

    def test_update_viewer_403(self, auth_client):
        c, store = auth_client
        proj = store.create("Upd Test")
        resp = c.patch(f"/api/v1/projects/{proj['project_id']}", json={"name": "Y"}, headers=VIEWER_HEADERS)
        assert resp.status_code == 403

    def test_update_operator_200(self, auth_client):
        c, store = auth_client
        proj = store.create("Upd Test")
        resp = c.patch(f"/api/v1/projects/{proj['project_id']}", json={"name": "Updated"}, headers=OPERATOR_HEADERS)
        assert resp.status_code == 200


class TestProjectDeleteAuth:
    """P1.6: DELETE /projects/{id} requires operator."""

    def test_delete_no_auth_401(self, auth_client):
        c, store = auth_client
        proj = store.create("Del Test")
        resp = c.delete(f"/api/v1/projects/{proj['project_id']}", headers=NO_AUTH_HEADERS)
        assert resp.status_code == 401


class TestProjectLinkAuth:
    """P1.6: POST /projects/{id}/missions/{mid} requires operator."""

    def test_link_no_auth_401(self, auth_client):
        c, store = auth_client
        proj = store.create("Link Test")
        resp = c.post(f"/api/v1/projects/{proj['project_id']}/missions/m1", headers=NO_AUTH_HEADERS)
        assert resp.status_code == 401


class TestProjectWorkspaceAuth:
    """P1.6: POST /projects/{id}/workspace/enable requires operator."""

    def test_workspace_no_auth_401(self, auth_client):
        c, store = auth_client
        proj = store.create("WS Test")
        resp = c.post(f"/api/v1/projects/{proj['project_id']}/workspace/enable", headers=NO_AUTH_HEADERS)
        assert resp.status_code == 401


class TestProjectArtifactAuth:
    """P1.6: POST /projects/{id}/artifacts requires operator."""

    def test_publish_no_auth_401(self, auth_client):
        c, store = auth_client
        proj = store.create("Art Test")
        resp = c.post(
            f"/api/v1/projects/{proj['project_id']}/artifacts",
            json={"mission_id": "m1", "artifact_id": "a1"},
            headers=NO_AUTH_HEADERS,
        )
        assert resp.status_code == 401

    def test_unpublish_no_auth_401(self, auth_client):
        c, store = auth_client
        proj = store.create("Art Test")
        resp = c.delete(
            f"/api/v1/projects/{proj['project_id']}/artifacts/a1",
            headers=NO_AUTH_HEADERS,
        )
        assert resp.status_code == 401


class TestGetEndpointsNoAuth:
    """P1.6: GET endpoints should not require auth."""

    def test_list_projects_no_auth(self, auth_client):
        c, _ = auth_client
        resp = c.get("/api/v1/projects")
        assert resp.status_code == 200

    def test_get_project_no_auth(self, auth_client):
        c, store = auth_client
        proj = store.create("Get Test")
        resp = c.get(f"/api/v1/projects/{proj['project_id']}")
        assert resp.status_code == 200

    def test_get_rollup_no_auth(self, auth_client):
        c, store = auth_client
        proj = store.create("Rollup Test")
        resp = c.get(f"/api/v1/projects/{proj['project_id']}/rollup")
        assert resp.status_code == 200
