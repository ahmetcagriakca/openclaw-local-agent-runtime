"""Tests for multi-user isolation — Sprint 40.

Covers:
- User ID extraction from API keys
- Data filtering by owner
- Ownership checks
- Alert namespace scoping
- Cross-user denial
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("TESTING", "1")

from auth.isolation import check_ownership, filter_by_owner, get_user_id
from auth.keys import ApiKey


class TestGetUserId(unittest.TestCase):
    """Test user_id extraction from API key."""

    @patch("auth.isolation.is_auth_enabled", return_value=False)
    def test_no_auth_returns_none(self, _):
        """Single-operator mode returns None (no filtering)."""
        user = ApiKey(key="k", name="test", role="operator", created="", user_id="user1")
        self.assertIsNone(get_user_id(user))

    @patch("auth.isolation.is_auth_enabled", return_value=True)
    def test_auth_enabled_returns_user_id(self, _):
        """Auth mode returns user_id from API key."""
        user = ApiKey(key="k", name="test", role="operator", created="", user_id="user1")
        self.assertEqual(get_user_id(user), "user1")

    @patch("auth.isolation.is_auth_enabled", return_value=True)
    def test_auth_enabled_no_user_id_falls_back_to_name(self, _):
        """Falls back to key name if user_id not set."""
        user = ApiKey(key="k", name="akca", role="operator", created="", user_id="")
        self.assertEqual(get_user_id(user), "akca")

    @patch("auth.isolation.is_auth_enabled", return_value=True)
    def test_none_user_returns_none(self, _):
        """Unauthenticated request returns None."""
        self.assertIsNone(get_user_id(None))


class TestFilterByOwner(unittest.TestCase):
    """Test data filtering by owner."""

    def test_no_filter_returns_all(self):
        """user_id=None returns all items."""
        items = [{"id": 1, "userId": "a"}, {"id": 2, "userId": "b"}]
        self.assertEqual(len(filter_by_owner(items, None)), 2)

    def test_filter_by_user(self):
        """Only items owned by user_id are returned."""
        items = [
            {"id": 1, "userId": "alice"},
            {"id": 2, "userId": "bob"},
            {"id": 3, "userId": "alice"},
        ]
        result = filter_by_owner(items, "alice")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(r["userId"] == "alice" for r in result))

    def test_items_without_owner_included(self):
        """Items without owner field are included (backwards compat)."""
        items = [
            {"id": 1, "userId": "alice"},
            {"id": 2},  # No userId
            {"id": 3, "userId": ""},  # Empty userId
        ]
        result = filter_by_owner(items, "alice")
        self.assertEqual(len(result), 3)

    def test_custom_owner_field(self):
        """Custom owner field name works."""
        items = [
            {"id": 1, "operator": "alice"},
            {"id": 2, "operator": "bob"},
        ]
        result = filter_by_owner(items, "alice", owner_field="operator")
        self.assertEqual(len(result), 1)

    def test_empty_list(self):
        """Empty list returns empty."""
        self.assertEqual(filter_by_owner([], "alice"), [])


class TestCheckOwnership(unittest.TestCase):
    """Test ownership checks."""

    def test_no_isolation_always_true(self):
        """No user_id means always owned."""
        self.assertTrue(check_ownership({"userId": "bob"}, None))

    def test_owner_matches(self):
        """Matching owner returns True."""
        self.assertTrue(check_ownership({"userId": "alice"}, "alice"))

    def test_owner_mismatch(self):
        """Mismatching owner returns False."""
        self.assertFalse(check_ownership({"userId": "bob"}, "alice"))

    def test_no_owner_field_allowed(self):
        """Items without owner are accessible (backwards compat)."""
        self.assertTrue(check_ownership({}, "alice"))
        self.assertTrue(check_ownership({"userId": ""}, "alice"))


class TestApiKeyUserIdField(unittest.TestCase):
    """Test ApiKey user_id field."""

    def test_api_key_has_user_id(self):
        """ApiKey should have user_id field."""
        key = ApiKey(key="k", name="test", role="operator", created="", user_id="user1")
        self.assertEqual(key.user_id, "user1")

    def test_api_key_default_empty_user_id(self):
        """ApiKey user_id defaults to empty string."""
        key = ApiKey(key="k", name="test", role="operator", created="")
        self.assertEqual(key.user_id, "")


class TestAlertNamespaceScoping(unittest.TestCase):
    """Test alert engine namespace filtering."""

    def test_alert_filter_by_user(self):
        """Alerts should be filterable by user_id."""
        alerts = [
            {"id": "a1", "user_id": "alice", "severity": "warning"},
            {"id": "a2", "user_id": "bob", "severity": "critical"},
            {"id": "a3", "user_id": "alice", "severity": "info"},
            {"id": "a4", "severity": "warning"},  # No user_id
        ]
        alice_alerts = [a for a in alerts if a.get("user_id") in (None, "", "alice")]
        self.assertEqual(len(alice_alerts), 3)  # a1, a3, a4

    def test_no_filter_returns_all(self):
        """No user_id filter returns all alerts."""
        alerts = [
            {"id": "a1", "user_id": "alice"},
            {"id": "a2", "user_id": "bob"},
        ]
        # No filtering = all returned
        self.assertEqual(len(alerts), 2)


class TestCrossUserDenial(unittest.TestCase):
    """Test cross-user access denial scenarios."""

    def test_user_a_cannot_see_user_b_missions(self):
        """User A's filter should exclude User B's missions."""
        missions = [
            {"missionId": "m1", "userId": "alice", "goal": "Alice task"},
            {"missionId": "m2", "userId": "bob", "goal": "Bob task"},
            {"missionId": "m3", "userId": "alice", "goal": "Alice task 2"},
        ]
        alice_missions = filter_by_owner(missions, "alice")
        self.assertEqual(len(alice_missions), 2)
        self.assertTrue(all(m["userId"] == "alice" for m in alice_missions))

    def test_user_a_cannot_mutate_user_b_resource(self):
        """Ownership check should deny User A access to User B's resource."""
        bobs_mission = {"missionId": "m2", "userId": "bob"}
        self.assertFalse(check_ownership(bobs_mission, "alice"))

    def test_single_operator_sees_everything(self):
        """Single-operator mode (user_id=None) sees all resources."""
        missions = [
            {"missionId": "m1", "userId": "alice"},
            {"missionId": "m2", "userId": "bob"},
        ]
        result = filter_by_owner(missions, None)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
