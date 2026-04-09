"""Endpoint-level tests for D-151 GitHub project API routes.

Exercises request/response behavior for:
- GET /projects/{id}/github
- POST /projects/{id}/github/bind
- POST /projects/{id}/github/sync
- POST /projects/{id}/github/comment

Uses FastAPI TestClient with VEZIR_AUTH_BYPASS=1 (conftest).
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.project_api import router, set_store
from persistence.project_store import ProjectStore


@pytest.fixture
def app():
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
    return TestClient(app), store


class TestGetProjectGitHub:
    """GET /projects/{id}/github"""

    def test_returns_empty_github_state(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        resp = tc.get(f"/api/v1/projects/{pid}/github")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["binding"] is None
        assert data["activity"] == []
        assert data["last_sync_at"] is None

    def test_returns_404_for_unknown_project(self, client):
        tc, _ = client
        resp = tc.get("/api/v1/projects/proj_nonexistent/github")
        assert resp.status_code == 404

    def test_returns_bound_state(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        store.bind_github(pid, "owner/repo", issue_number=42)
        resp = tc.get(f"/api/v1/projects/{pid}/github")
        assert resp.status_code == 200
        binding = resp.json()["data"]["binding"]
        assert binding["repo_full_name"] == "owner/repo"
        assert binding["issue_number"] == 42


class TestBindProjectGitHub:
    """POST /projects/{id}/github/bind"""

    def test_bind_issue_201(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        resp = tc.post(
            f"/api/v1/projects/{pid}/github/bind",
            json={"repo_full_name": "ahmetcagriakca/vezir", "issue_number": 448},
        )
        assert resp.status_code == 201
        binding = resp.json()["data"]
        assert binding["repo_full_name"] == "ahmetcagriakca/vezir"
        assert binding["issue_number"] == 448
        assert binding["thread_number"] == 448
        assert binding["provider"] == "github"

    def test_bind_pr_201(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        resp = tc.post(
            f"/api/v1/projects/{pid}/github/bind",
            json={"repo_full_name": "owner/repo", "pr_number": 100},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["pr_number"] == 100

    def test_bind_422_no_issue_or_pr(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        resp = tc.post(
            f"/api/v1/projects/{pid}/github/bind",
            json={"repo_full_name": "owner/repo"},
        )
        assert resp.status_code == 422

    def test_bind_422_both_issue_and_pr(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        resp = tc.post(
            f"/api/v1/projects/{pid}/github/bind",
            json={"repo_full_name": "owner/repo", "issue_number": 1, "pr_number": 2},
        )
        assert resp.status_code == 422

    def test_bind_404_unknown_project(self, client):
        tc, _ = client
        resp = tc.post(
            "/api/v1/projects/proj_nonexistent/github/bind",
            json={"repo_full_name": "owner/repo", "issue_number": 1},
        )
        assert resp.status_code == 404

    def test_bind_persists_in_project_detail(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        tc.post(
            f"/api/v1/projects/{pid}/github/bind",
            json={"repo_full_name": "owner/repo", "issue_number": 5},
        )
        detail_resp = tc.get(f"/api/v1/projects/{pid}")
        assert detail_resp.status_code == 200
        github = detail_resp.json()["data"]["github"]
        assert github["binding"]["repo_full_name"] == "owner/repo"


class TestSyncProjectGitHub:
    """POST /projects/{id}/github/sync"""

    def test_sync_409_no_binding(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        resp = tc.post(f"/api/v1/projects/{pid}/github/sync")
        assert resp.status_code == 409
        assert "no GitHub binding" in resp.json()["detail"]

    def test_sync_404_unknown_project(self, client):
        tc, _ = client
        resp = tc.post("/api/v1/projects/proj_nonexistent/github/sync")
        assert resp.status_code == 404

    @patch("api.project_api.GitHubProjectService")
    def test_sync_200_with_mock_service(self, mock_cls, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        store.bind_github(pid, "owner/repo", issue_number=1)

        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        mock_service.sync_binding.return_value = {
            "repo_full_name": "owner/repo",
            "fetched_at": "2026-04-09T12:00:00+00:00",
            "activity": [
                {"activity_id": "issue:1", "kind": "issue", "body": "hello"},
            ],
        }
        resp = tc.post(f"/api/v1/projects/{pid}/github/sync")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["activity"]) == 1
        assert data["last_sync_at"] is not None

    @patch("api.project_api.GitHubProjectService")
    def test_sync_502_on_github_error(self, mock_cls, client):
        from services.github_project_service import GitHubProjectServiceError

        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        store.bind_github(pid, "owner/repo", issue_number=1)

        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        mock_service.sync_binding.side_effect = GitHubProjectServiceError("API error")
        resp = tc.post(f"/api/v1/projects/{pid}/github/sync")
        assert resp.status_code == 502


class TestPublishGitHubComment:
    """POST /projects/{id}/github/comment"""

    def test_comment_409_no_binding(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        resp = tc.post(
            f"/api/v1/projects/{pid}/github/comment",
            json={"body": "test comment"},
        )
        assert resp.status_code == 409

    def test_comment_404_unknown_project(self, client):
        tc, _ = client
        resp = tc.post(
            "/api/v1/projects/proj_nonexistent/github/comment",
            json={"body": "test"},
        )
        assert resp.status_code == 404

    def test_comment_422_empty_body(self, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        store.bind_github(pid, "owner/repo", issue_number=1)
        resp = tc.post(
            f"/api/v1/projects/{pid}/github/comment",
            json={"body": ""},
        )
        assert resp.status_code == 422

    @patch("api.project_api.GitHubProjectService")
    def test_comment_201_with_mock_service(self, mock_cls, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        store.bind_github(pid, "owner/repo", issue_number=42)

        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        mock_service.post_issue_comment.return_value = {
            "id": 99999,
            "body": "D-151 connectivity check",
            "created_at": "2026-04-09T12:00:00Z",
            "updated_at": "2026-04-09T12:00:00Z",
            "html_url": "https://github.com/owner/repo/issues/42#issuecomment-99999",
        }
        resp = tc.post(
            f"/api/v1/projects/{pid}/github/comment",
            json={"body": "D-151 connectivity check"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["activity_id"] == "issue_comment:99999"
        assert data["kind"] == "issue_comment"
        assert data["direction"] == "outbound"
        assert data["comment_id"] == 99999
        assert data["thread_number"] == 42

    @patch("api.project_api.GitHubProjectService")
    def test_comment_502_on_github_error(self, mock_cls, client):
        from services.github_project_service import GitHubProjectServiceError

        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        store.bind_github(pid, "owner/repo", issue_number=1)

        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        mock_service.post_issue_comment.side_effect = GitHubProjectServiceError("fail")
        resp = tc.post(
            f"/api/v1/projects/{pid}/github/comment",
            json={"body": "test"},
        )
        assert resp.status_code == 502

    @patch("api.project_api.GitHubProjectService")
    def test_comment_appends_to_activity(self, mock_cls, client):
        tc, store = client
        proj = store.create("Test Project")
        pid = proj["project_id"]
        store.bind_github(pid, "owner/repo", issue_number=1)

        mock_service = MagicMock()
        mock_cls.return_value = mock_service
        mock_service.post_issue_comment.return_value = {
            "id": 555,
            "body": "hello",
            "created_at": "2026-04-09T12:00:00Z",
            "updated_at": "2026-04-09T12:00:00Z",
            "html_url": "https://github.com/owner/repo/issues/1#issuecomment-555",
        }
        tc.post(
            f"/api/v1/projects/{pid}/github/comment",
            json={"body": "hello"},
        )
        # Verify activity persisted
        gh = store.get_github(pid)
        assert len(gh["activity"]) == 1
        assert gh["activity"][0]["comment_id"] == 555
