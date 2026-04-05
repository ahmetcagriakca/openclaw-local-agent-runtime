"""Tests for B-136: Auth Session Quarantine + Actor Chain.

Validates:
1. get_session() emits DeprecationWarning
2. Session dataclass still works (not broken)
3. resolve_source_user() returns correct values for all 3 tiers
4. Mutation audit captures actor field
"""
import json
import os
import unittest
import warnings
from unittest.mock import MagicMock, patch


class TestSessionDeprecation(unittest.TestCase):
    """B-136: session.py deprecation warnings."""

    def test_get_session_emits_deprecation_warning(self):
        """get_session() must emit DeprecationWarning."""
        # Reset global session to force creation
        import auth.session as mod
        from auth.session import get_session
        mod._current_session = None

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            get_session()
            self.assertTrue(len(w) >= 1, "Expected at least one warning")
            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            self.assertTrue(len(dep_warnings) >= 1, "Expected DeprecationWarning")
            self.assertIn("B-136", str(dep_warnings[0].message))

    def test_session_dataclass_still_works(self):
        """Session dataclass must remain functional after deprecation."""
        from auth.session import Session

        s = Session(operator="test-user", source="cli")
        self.assertEqual(s.operator, "test-user")
        self.assertEqual(s.source, "cli")
        self.assertIsInstance(s.session_id, str)
        self.assertTrue(len(s.session_id) > 0)

        d = s.to_dict()
        self.assertEqual(d["operator"], "test-user")
        self.assertEqual(d["source"], "cli")
        self.assertIn("session_id", d)
        self.assertIn("started_at", d)

    def test_get_operator_still_works(self):
        """get_operator() is not deprecated, must still work."""
        from auth.session import get_operator

        result = get_operator()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_new_session_still_works(self):
        """new_session() must still work (not deprecated itself)."""
        from auth.session import new_session

        s = new_session(source="telegram")
        self.assertEqual(s.source, "telegram")


class TestSourceUserResolver(unittest.TestCase):
    """B-136: resolve_source_user() 3-tier precedence."""

    def _make_request(self, host="127.0.0.1", headers=None):
        """Create a mock FastAPI Request."""
        req = MagicMock()
        req.client = MagicMock()
        req.client.host = host
        req.headers = headers or {}
        return req

    def test_tier1_operator_dict(self):
        """Tier 1: authenticated operator dict takes precedence."""
        from auth.source_user_resolver import resolve_source_user

        req = self._make_request(headers={"X-Source-User": "header-user"})
        result = resolve_source_user(req, operator={"operator": "auth-user"})
        self.assertEqual(result, "auth-user")

    def test_tier1_operator_dict_user_id(self):
        """Tier 1: operator dict with user_id key."""
        from auth.source_user_resolver import resolve_source_user

        req = self._make_request()
        result = resolve_source_user(req, operator={"user_id": "uid-123"})
        self.assertEqual(result, "uid-123")

    def test_tier1_operator_string(self):
        """Tier 1: operator as plain string."""
        from auth.source_user_resolver import resolve_source_user

        req = self._make_request()
        result = resolve_source_user(req, operator="string-user")
        self.assertEqual(result, "string-user")

    def test_tier2_header_trusted_origin(self):
        """Tier 2: X-Source-User header from trusted origin."""
        from auth.source_user_resolver import resolve_source_user

        req = self._make_request(
            host="127.0.0.1",
            headers={"X-Source-User": "header-user"},
        )
        result = resolve_source_user(req, operator=None)
        self.assertEqual(result, "header-user")

    def test_tier2_header_untrusted_origin_falls_to_tier3(self):
        """Tier 2: X-Source-User header from untrusted origin falls to tier 3."""
        from auth.source_user_resolver import resolve_source_user

        req = self._make_request(
            host="10.0.0.5",
            headers={"X-Source-User": "header-user"},
        )
        # Should fall through to tier 3 (config fallback)
        result = resolve_source_user(req, operator=None)
        self.assertNotEqual(result, "header-user")
        self.assertIsNotNone(result)  # tier 3 fallback

    def test_tier3_config_fallback(self):
        """Tier 3: config fallback when no auth and no header."""
        from auth.source_user_resolver import resolve_source_user

        req = self._make_request(host="127.0.0.1")
        with patch.dict(os.environ, {"VEZIR_DEFAULT_USER": "fallback-user"}):
            result = resolve_source_user(req, operator=None)
        self.assertEqual(result, "fallback-user")

    def test_tier3_default_dashboard(self):
        """Tier 3: default fallback is 'dashboard' when env not set."""
        from auth.source_user_resolver import resolve_source_user

        req = self._make_request(host="127.0.0.1")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VEZIR_DEFAULT_USER", None)
            result = resolve_source_user(req, operator=None)
        self.assertEqual(result, "dashboard")


class TestMutationAuditActor(unittest.TestCase):
    """B-136: mutation audit captures actor field."""

    def test_log_mutation_includes_actor(self):
        """log_mutation() must include actor in the JSON entry."""
        from api.mutation_audit import log_mutation

        with patch("api.mutation_audit.logger") as mock_logger:
            log_mutation(
                request_id="req-test-123",
                operation="cancel",
                target_id="m-456",
                outcome="requested",
                actor="akca",
            )

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            json_str = call_args[0][1]
            entry = json.loads(json_str)

            self.assertEqual(entry["actor"], "akca")
            self.assertEqual(entry["operation"], "cancel")
            self.assertEqual(entry["targetId"], "m-456")

    def test_log_mutation_actor_defaults_to_unknown(self):
        """log_mutation() defaults actor to 'unknown' when not provided."""
        from api.mutation_audit import log_mutation

        with patch("api.mutation_audit.logger") as mock_logger:
            log_mutation(
                request_id="req-test-456",
                operation="approve",
                target_id="a-789",
                outcome="applied",
            )

            call_args = mock_logger.info.call_args
            json_str = call_args[0][1]
            entry = json.loads(json_str)
            self.assertEqual(entry["actor"], "unknown")

    def test_log_mutation_includes_all_fields(self):
        """log_mutation() must include all standard fields plus actor."""
        from api.mutation_audit import log_mutation

        with patch("api.mutation_audit.logger") as mock_logger:
            log_mutation(
                request_id="req-full",
                operation="retry",
                target_id="m-full",
                outcome="requested",
                tab_id="tab-1",
                session_id="sess-1",
                detail="test detail",
                actor="test-actor",
            )

            call_args = mock_logger.info.call_args
            json_str = call_args[0][1]
            entry = json.loads(json_str)

            self.assertIn("timestamp", entry)
            self.assertEqual(entry["source"], "dashboard")
            self.assertEqual(entry["operation"], "retry")
            self.assertEqual(entry["targetId"], "m-full")
            self.assertEqual(entry["outcome"], "requested")
            self.assertEqual(entry["requestId"], "req-full")
            self.assertEqual(entry["tabId"], "tab-1")
            self.assertEqual(entry["sessionId"], "sess-1")
            self.assertEqual(entry["detail"], "test detail")
            self.assertEqual(entry["actor"], "test-actor")


if __name__ == "__main__":
    unittest.main()
