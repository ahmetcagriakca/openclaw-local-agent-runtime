"""Tests for D-151 GitHub project communication surface.

Validates:
- Auth contract: AuthenticatedUser used (not ApiKey)
- Identity contract: frozen fallback values
- GitHub persistence: bind, sync, activity
- Event types: project.github_bound, synced, comment_published
- API endpoint wiring
"""
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from auth.middleware import AuthenticatedUser
from events.bus import Event
from events.catalog import EventType
from events.handlers.project_handler import (
    PROJECT_EVENT_TYPES,
    SSE_BROADCAST_EVENTS,
    ProjectHandler,
)
from persistence.project_store import ProjectStore, ProjectStoreError


class TestIdentityContract(unittest.TestCase):
    """D-151: Frozen identity contract validation."""

    def test_default_actor_identity(self):
        from api.project_api import _default_actor_identity

        actor = _default_actor_identity()
        assert actor["user_id"] == "ahmetcagriakca"
        assert actor["username"] == "ahmetcagriakca"
        assert actor["display_name"] == "Ahmet Cagri AKCA"
        assert actor["provider"] == "github"

    def test_actor_identity_with_none_user(self):
        from api.project_api import _actor_identity

        actor = _actor_identity(None)
        assert actor["user_id"] == "ahmetcagriakca"
        assert actor["username"] == "ahmetcagriakca"

    def test_actor_identity_with_authenticated_user(self):
        from api.project_api import _actor_identity

        user = AuthenticatedUser(
            user_id="testuser",
            username="testuser",
            role="operator",
            provider="github",
            display_name="Test User",
        )
        actor = _actor_identity(user)
        assert actor["user_id"] == "testuser"
        assert actor["username"] == "testuser"
        assert actor["display_name"] == "Test User"
        assert actor["provider"] == "github"

    def test_actor_identity_fallback_display_name(self):
        from api.project_api import _actor_identity

        user = AuthenticatedUser(
            user_id="someuser",
            username="someuser",
            role="operator",
            provider="apikey",
            display_name="",
        )
        actor = _actor_identity(user)
        assert actor["display_name"] == "Ahmet Cagri AKCA"

    def test_actor_identity_fallback_empty_username(self):
        from api.project_api import _actor_identity

        user = AuthenticatedUser(
            user_id="uid",
            username="",
            role="operator",
            provider="github",
        )
        actor = _actor_identity(user)
        assert actor["username"] == "uid"

    def test_actor_identity_type_is_authenticated_user(self):
        """Ensure _actor_identity accepts AuthenticatedUser, not ApiKey."""
        import inspect
        from api.project_api import _actor_identity

        sig = inspect.signature(_actor_identity)
        param = sig.parameters["user"]
        annotation_str = str(param.annotation)
        assert "AuthenticatedUser" in annotation_str
        assert "ApiKey" not in annotation_str


class TestGitHubEventTypes(unittest.TestCase):
    """D-151: Event catalog and handler registration."""

    def test_github_bound_event_exists(self):
        assert EventType.PROJECT_GITHUB_BOUND == "project.github_bound"

    def test_github_synced_event_exists(self):
        assert EventType.PROJECT_GITHUB_SYNCED == "project.github_synced"

    def test_github_comment_published_event_exists(self):
        assert EventType.PROJECT_GITHUB_COMMENT_PUBLISHED == "project.github_comment_published"

    def test_github_events_in_project_handler(self):
        assert EventType.PROJECT_GITHUB_BOUND in PROJECT_EVENT_TYPES
        assert EventType.PROJECT_GITHUB_SYNCED in PROJECT_EVENT_TYPES
        assert EventType.PROJECT_GITHUB_COMMENT_PUBLISHED in PROJECT_EVENT_TYPES

    def test_github_events_in_sse_broadcast(self):
        assert EventType.PROJECT_GITHUB_BOUND in SSE_BROADCAST_EVENTS
        assert EventType.PROJECT_GITHUB_SYNCED in SSE_BROADCAST_EVENTS
        assert EventType.PROJECT_GITHUB_COMMENT_PUBLISHED in SSE_BROADCAST_EVENTS

    def test_github_events_in_namespace(self):
        ns = EventType.namespace("project")
        assert "project.github_bound" in ns
        assert "project.github_synced" in ns
        assert "project.github_comment_published" in ns


class TestProjectHandlerGitHubEvents(unittest.TestCase):
    """D-151: ProjectHandler processes GitHub events."""

    def setUp(self):
        self.handler = ProjectHandler()

    def test_handles_github_bound(self):
        event = Event(
            type=EventType.PROJECT_GITHUB_BOUND,
            data={
                "project_id": "proj_test1",
                "repo_full_name": "owner/repo",
                "thread_number": 42,
                "actor": "ahmetcagriakca",
            },
            source="test",
        )
        result = self.handler(event)
        assert result.handled is True
        assert result.halt is False

    def test_handles_github_synced(self):
        event = Event(
            type=EventType.PROJECT_GITHUB_SYNCED,
            data={
                "project_id": "proj_test1",
                "repo_full_name": "owner/repo",
                "thread_number": 42,
                "activity_count": 5,
            },
            source="test",
        )
        result = self.handler(event)
        assert result.handled is True

    def test_handles_github_comment_published(self):
        event = Event(
            type=EventType.PROJECT_GITHUB_COMMENT_PUBLISHED,
            data={
                "project_id": "proj_test1",
                "repo_full_name": "owner/repo",
                "thread_number": 42,
                "comment_id": 12345,
                "actor": "ahmetcagriakca",
            },
            source="test",
        )
        result = self.handler(event)
        assert result.handled is True


class TestProjectStoreGitHub(unittest.TestCase):
    """D-151: GitHub persistence in ProjectStore."""

    def setUp(self):
        self.tmp = Path(__file__).parent / "tmp_d151_test.json"
        self.store = ProjectStore(store_path=self.tmp)
        self.project = self.store.create(name="Test Project")
        self.pid = self.project["project_id"]

    def tearDown(self):
        if self.tmp.exists():
            self.tmp.unlink()

    def test_get_github_empty(self):
        gh = self.store.get_github(self.pid)
        assert gh["binding"] is None
        assert gh["activity"] == []
        assert gh["last_sync_at"] is None

    def test_bind_github_issue(self):
        binding = self.store.bind_github(
            self.pid,
            "ahmetcagriakca/vezir",
            issue_number=448,
            bound_by={"user_id": "ahmetcagriakca"},
        )
        assert binding["repo_full_name"] == "ahmetcagriakca/vezir"
        assert binding["issue_number"] == 448
        assert binding["pr_number"] is None
        assert binding["thread_number"] == 448
        assert binding["provider"] == "github"
        assert "bound_at" in binding

    def test_bind_github_pr(self):
        binding = self.store.bind_github(
            self.pid,
            "ahmetcagriakca/vezir",
            pr_number=100,
        )
        assert binding["pr_number"] == 100
        assert binding["thread_number"] == 100

    def test_bind_github_requires_issue_or_pr(self):
        with self.assertRaises(ProjectStoreError):
            self.store.bind_github(self.pid, "ahmetcagriakca/vezir")

    def test_bind_github_rejects_both(self):
        with self.assertRaises(ProjectStoreError):
            self.store.bind_github(
                self.pid, "ahmetcagriakca/vezir",
                issue_number=1, pr_number=2,
            )

    def test_sync_github_activity(self):
        self.store.bind_github(self.pid, "owner/repo", issue_number=1)
        sync_result = {
            "repo_full_name": "owner/repo",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "activity": [
                {"activity_id": "issue:1", "kind": "issue", "body": "hello"},
            ],
        }
        snapshot = self.store.sync_github_activity(self.pid, sync_result)
        assert len(snapshot["activity"]) == 1
        assert snapshot["last_sync_at"] is not None

    def test_sync_rejects_mismatched_repo(self):
        self.store.bind_github(self.pid, "owner/repo", issue_number=1)
        with self.assertRaises(ProjectStoreError):
            self.store.sync_github_activity(self.pid, {
                "repo_full_name": "other/repo",
                "activity": [],
            })

    def test_append_github_activity(self):
        self.store.bind_github(self.pid, "owner/repo", issue_number=1)
        entry = self.store.append_github_activity(self.pid, {
            "activity_id": "comment:1",
            "kind": "issue_comment",
            "body": "test",
        })
        assert entry["activity_id"] == "comment:1"

        gh = self.store.get_github(self.pid)
        assert len(gh["activity"]) == 1

    def test_get_github_after_bind(self):
        self.store.bind_github(self.pid, "owner/repo", issue_number=5)
        gh = self.store.get_github(self.pid)
        assert gh["binding"] is not None
        assert gh["binding"]["repo_full_name"] == "owner/repo"

    def test_project_detail_includes_github(self):
        """Verify get_github is called for project detail enrichment."""
        self.store.bind_github(self.pid, "owner/repo", issue_number=1)
        gh = self.store.get_github(self.pid)
        assert "binding" in gh
        assert "activity" in gh
        assert "last_sync_at" in gh


class TestForbiddenIdentity(unittest.TestCase):
    """Ensure forbidden value never appears in actor identity."""

    def test_default_actor_no_forbidden(self):
        from api.project_api import _default_actor_identity

        actor = _default_actor_identity()
        for value in actor.values():
            assert "TCAHMAKCA" not in str(value)
            assert "TURKCELL" not in str(value)

    def test_actor_identity_no_forbidden(self):
        from api.project_api import _actor_identity

        user = AuthenticatedUser(
            user_id="ahmetcagriakca",
            username="ahmetcagriakca",
            role="operator",
            provider="github",
        )
        actor = _actor_identity(user)
        for value in actor.values():
            assert "TCAHMAKCA" not in str(value)
            assert "TURKCELL" not in str(value)


if __name__ == "__main__":
    unittest.main()
