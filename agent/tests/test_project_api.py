"""Tests for Project API — D-144 §7.

Task 73.10: 7 endpoints + error codes (409, 422, 404).
"""
import pytest
from conftest import AUTH_HEADERS
from conftest import MUTATION_HEADERS as POST_HEADERS
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """Create test client with isolated project store."""
    from persistence.mission_store import MissionStore
    from persistence.project_store import ProjectStore

    ms = MissionStore(store_path=tmp_path / "missions.json")
    ps = ProjectStore(
        store_path=tmp_path / "projects.json",
        mission_store=ms,
    )

    # Inject store into API
    from api import project_api
    project_api.set_store(ps)

    from api.server import app
    return TestClient(app), ps, ms


class TestCreateProject:
    def test_create_success(self, client):
        c, _, _ = client
        resp = c.post(
            "/api/v1/projects",
            json={"name": "Test Project"},
            headers=POST_HEADERS,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "Test Project"
        assert data["status"] == "draft"
        assert data["project_id"].startswith("proj_")

    def test_create_with_all_fields(self, client):
        c, _, _ = client
        resp = c.post(
            "/api/v1/projects",
            json={
                "name": "Full",
                "description": "A project",
                "owner": "akca",
            },
            headers=POST_HEADERS,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["description"] == "A project"
        assert data["owner"] == "akca"


class TestListProjects:
    def test_list_empty(self, client):
        c, _, _ = client
        resp = c.get("/api/v1/projects", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_with_items(self, client):
        c, ps, _ = client
        ps.create("A")
        ps.create("B")
        resp = c.get("/api/v1/projects", headers=AUTH_HEADERS)
        assert resp.json()["total"] == 2

    def test_list_filter_status(self, client):
        c, ps, _ = client
        ps.create("Draft")
        p2 = ps.create("Active")
        ps.transition_status(p2["project_id"], "active")
        resp = c.get(
            "/api/v1/projects?status=active",
            headers=AUTH_HEADERS,
        )
        assert resp.json()["total"] == 1
        assert resp.json()["data"][0]["status"] == "active"


class TestGetProject:
    def test_get_success(self, client):
        c, ps, _ = client
        proj = ps.create("Detail Test")
        resp = c.get(
            f"/api/v1/projects/{proj['project_id']}",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert "project" in body
        assert "mission_summary" in body
        assert body["project"]["name"] == "Detail Test"

    def test_get_not_found(self, client):
        c, _, _ = client
        resp = c.get(
            "/api/v1/projects/proj_nonexistent",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 404

    def test_get_includes_mission_summary(self, client):
        c, ps, ms = client
        proj = ps.create("With Missions")
        ms.record({
            "id": "mis-1",
            "goal": "test",
            "status": "completed",
            "project_id": proj["project_id"],
        })
        resp = c.get(
            f"/api/v1/projects/{proj['project_id']}",
            headers=AUTH_HEADERS,
        )
        summary = resp.json()["data"]["mission_summary"]
        assert summary["total"] == 1
        assert summary["quiescent_count"] == 1


class TestUpdateProject:
    def test_update_name(self, client):
        c, ps, _ = client
        proj = ps.create("Old Name")
        resp = c.patch(
            f"/api/v1/projects/{proj['project_id']}",
            json={"name": "New Name"},
            headers=POST_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "New Name"

    def test_update_status_valid(self, client):
        c, ps, _ = client
        proj = ps.create("Test")
        resp = c.patch(
            f"/api/v1/projects/{proj['project_id']}",
            json={"status": "active"},
            headers=POST_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "active"

    def test_update_status_invalid_422(self, client):
        c, ps, _ = client
        proj = ps.create("Test")
        resp = c.patch(
            f"/api/v1/projects/{proj['project_id']}",
            json={"status": "archived"},
            headers=POST_HEADERS,
        )
        assert resp.status_code == 422

    def test_update_status_active_missions_409(self, client):
        c, ps, ms = client
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ms.record({
            "id": "mis-1",
            "goal": "test",
            "status": "running",
            "project_id": proj["project_id"],
        })
        resp = c.patch(
            f"/api/v1/projects/{proj['project_id']}",
            json={"status": "completed"},
            headers=POST_HEADERS,
        )
        assert resp.status_code == 409

    def test_update_not_found(self, client):
        c, _, _ = client
        resp = c.patch(
            "/api/v1/projects/proj_fake",
            json={"name": "Fail"},
            headers=POST_HEADERS,
        )
        assert resp.status_code == 404


class TestDeleteProject:
    def test_delete_draft(self, client):
        c, ps, _ = client
        proj = ps.create("Delete Me")
        resp = c.delete(
            f"/api/v1/projects/{proj['project_id']}",
            headers=POST_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    def test_delete_completed_409(self, client):
        c, ps, _ = client
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ps.transition_status(proj["project_id"], "completed")
        resp = c.delete(
            f"/api/v1/projects/{proj['project_id']}",
            headers=POST_HEADERS,
        )
        assert resp.status_code == 409

    def test_delete_with_active_missions_409(self, client):
        c, ps, ms = client
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ms.record({
            "id": "mis-1",
            "goal": "block delete",
            "status": "running",
            "project_id": proj["project_id"],
        })
        resp = c.delete(
            f"/api/v1/projects/{proj['project_id']}",
            headers=POST_HEADERS,
        )
        assert resp.status_code == 409

    def test_delete_not_found(self, client):
        c, _, _ = client
        resp = c.delete(
            "/api/v1/projects/proj_fake",
            headers=POST_HEADERS,
        )
        assert resp.status_code == 404


class TestLinkMission:
    def test_link_success(self, client):
        c, ps, ms = client
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ms.record({"id": "mis-1", "goal": "test", "status": "pending"})
        resp = c.post(
            f"/api/v1/projects/{proj['project_id']}/missions/mis-1",
            headers=POST_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["linked"] is True

        # Verify mission got project_id
        mission = ms.get("mis-1")
        assert mission["project_id"] == proj["project_id"]

    def test_link_paused_project_409(self, client):
        c, ps, ms = client
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ps.transition_status(proj["project_id"], "paused")
        ms.record({"id": "mis-2", "goal": "test", "status": "pending"})
        resp = c.post(
            f"/api/v1/projects/{proj['project_id']}/missions/mis-2",
            headers=POST_HEADERS,
        )
        assert resp.status_code == 409

    def test_link_completed_project_409(self, client):
        c, ps, ms = client
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ps.transition_status(proj["project_id"], "completed")
        ms.record({"id": "mis-3", "goal": "test", "status": "pending"})
        resp = c.post(
            f"/api/v1/projects/{proj['project_id']}/missions/mis-3",
            headers=POST_HEADERS,
        )
        assert resp.status_code == 409


class TestUnlinkMission:
    def test_unlink_success(self, client):
        c, ps, ms = client
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ms.record({
            "id": "mis-1",
            "goal": "test",
            "status": "pending",
            "project_id": proj["project_id"],
        })
        resp = c.delete(
            f"/api/v1/projects/{proj['project_id']}/missions/mis-1",
            headers=POST_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["unlinked"] is True

        mission = ms.get("mis-1")
        assert mission["project_id"] is None

    def test_unlink_archived_project_409(self, client):
        c, ps, ms = client
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "cancelled")
        ps.transition_status(proj["project_id"], "archived")
        ms.record({
            "id": "mis-2",
            "goal": "test",
            "status": "completed",
            "project_id": proj["project_id"],
        })
        resp = c.delete(
            f"/api/v1/projects/{proj['project_id']}/missions/mis-2",
            headers=POST_HEADERS,
        )
        assert resp.status_code == 409
