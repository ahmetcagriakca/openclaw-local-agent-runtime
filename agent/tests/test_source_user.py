"""Tests for source user identity resolver — D-134 (Sprint 55).

Covers: 3-tier precedence, fail-closed, trusted origin validation.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth.source_user_resolver import (
    resolve_source_user,
    _is_trusted_origin,
    SOURCE_USER_HEADER,
    TRUSTED_ORIGINS,
    DEFAULT_USER_ENV,
)


def _mock_request(host: str = "127.0.0.1", headers: dict | None = None):
    """Create a mock FastAPI Request."""
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = host
    req.headers = headers or {}
    return req


# ── Trusted origin tests ─────────────────────────────────────────


class TestTrustedOrigin:
    def test_localhost_trusted(self):
        req = _mock_request("127.0.0.1")
        assert _is_trusted_origin(req) is True

    def test_localhost_name_trusted(self):
        req = _mock_request("localhost")
        assert _is_trusted_origin(req) is True

    def test_ipv6_localhost_trusted(self):
        req = _mock_request("::1")
        assert _is_trusted_origin(req) is True

    def test_external_ip_untrusted(self):
        req = _mock_request("192.168.1.100")
        assert _is_trusted_origin(req) is False

    def test_public_ip_untrusted(self):
        req = _mock_request("8.8.8.8")
        assert _is_trusted_origin(req) is False

    def test_no_client_untrusted(self):
        req = MagicMock()
        req.client = None
        assert _is_trusted_origin(req) is False


# ── Tier 1: Auth context tests ───────────────────────────────────


class TestTier1AuthContext:
    def test_operator_dict_with_operator_field(self):
        req = _mock_request()
        result = resolve_source_user(req, {"operator": "akca"})
        assert result == "akca"

    def test_operator_dict_with_user_id_field(self):
        req = _mock_request()
        result = resolve_source_user(req, {"user_id": "admin"})
        assert result == "admin"

    def test_operator_string(self):
        req = _mock_request()
        result = resolve_source_user(req, "akca")
        assert result == "akca"

    def test_operator_takes_precedence_over_header(self):
        req = _mock_request(headers={SOURCE_USER_HEADER: "header-user"})
        result = resolve_source_user(req, "auth-user")
        assert result == "auth-user"

    def test_operator_takes_precedence_over_config(self):
        req = _mock_request()
        with patch.dict(os.environ, {DEFAULT_USER_ENV: "config-user"}):
            result = resolve_source_user(req, "auth-user")
            assert result == "auth-user"


# ── Tier 2: Header tests ────────────────────────────────────────


class TestTier2Header:
    def test_header_from_trusted_origin(self):
        req = _mock_request("127.0.0.1",
                            headers={SOURCE_USER_HEADER: "header-user"})
        result = resolve_source_user(req, None)
        assert result == "header-user"

    def test_header_from_localhost_name(self):
        req = _mock_request("localhost",
                            headers={SOURCE_USER_HEADER: "header-user"})
        result = resolve_source_user(req, None)
        assert result == "header-user"

    def test_header_rejected_from_untrusted(self):
        """Header from untrusted origin must be rejected per D-070."""
        req = _mock_request("192.168.1.100",
                            headers={SOURCE_USER_HEADER: "attacker"})
        # Should fall through to tier 3 or fail-closed
        with patch.dict(os.environ, {}, clear=True):
            env_backup = os.environ.pop(DEFAULT_USER_ENV, None)
            try:
                result = resolve_source_user(req, None)
                # Without config fallback, should be None (fail-closed)
                assert result is None
            finally:
                if env_backup:
                    os.environ[DEFAULT_USER_ENV] = env_backup

    def test_header_rejected_falls_to_config(self):
        """Rejected header should fall through to config fallback."""
        req = _mock_request("8.8.8.8",
                            headers={SOURCE_USER_HEADER: "attacker"})
        with patch.dict(os.environ, {DEFAULT_USER_ENV: "fallback-user"}):
            result = resolve_source_user(req, None)
            assert result == "fallback-user"

    def test_no_header_no_auth(self):
        req = _mock_request()
        with patch.dict(os.environ, {DEFAULT_USER_ENV: "config-user"}):
            result = resolve_source_user(req, None)
            assert result == "config-user"


# ── Tier 3: Config fallback tests ────────────────────────────────


class TestTier3ConfigFallback:
    def test_config_fallback(self):
        req = _mock_request()
        with patch.dict(os.environ, {DEFAULT_USER_ENV: "default-user"}):
            result = resolve_source_user(req, None)
            assert result == "default-user"

    def test_config_fallback_used_when_no_auth_no_header(self):
        req = _mock_request()
        with patch.dict(os.environ, {DEFAULT_USER_ENV: "fallback"}):
            result = resolve_source_user(req, None)
            assert result == "fallback"


# ── Fail-closed tests ───────────────────────────────────────────


class TestFailClosed:
    def test_fail_closed_no_source(self):
        """No auth, no header, no config → None (fail-closed per D-134)."""
        req = _mock_request()
        with patch.dict(os.environ, {}, clear=True):
            env_backup = os.environ.pop(DEFAULT_USER_ENV, None)
            try:
                result = resolve_source_user(req, None)
                assert result is None
            finally:
                if env_backup:
                    os.environ[DEFAULT_USER_ENV] = env_backup

    def test_fail_closed_empty_operator(self):
        req = _mock_request()
        with patch.dict(os.environ, {}, clear=True):
            env_backup = os.environ.pop(DEFAULT_USER_ENV, None)
            try:
                result = resolve_source_user(req, "")
                assert result is None
            finally:
                if env_backup:
                    os.environ[DEFAULT_USER_ENV] = env_backup

    def test_fail_closed_empty_dict(self):
        req = _mock_request()
        with patch.dict(os.environ, {}, clear=True):
            env_backup = os.environ.pop(DEFAULT_USER_ENV, None)
            try:
                result = resolve_source_user(req, {})
                assert result is None
            finally:
                if env_backup:
                    os.environ[DEFAULT_USER_ENV] = env_backup


# ── Precedence order tests ───────────────────────────────────────


class TestPrecedenceOrder:
    def test_auth_over_header_over_config(self):
        """Full precedence: auth > header > config."""
        req = _mock_request("127.0.0.1",
                            headers={SOURCE_USER_HEADER: "header-user"})
        with patch.dict(os.environ, {DEFAULT_USER_ENV: "config-user"}):
            # Tier 1 wins
            assert resolve_source_user(req, "auth-user") == "auth-user"

    def test_header_over_config(self):
        """Without auth: header > config."""
        req = _mock_request("127.0.0.1",
                            headers={SOURCE_USER_HEADER: "header-user"})
        with patch.dict(os.environ, {DEFAULT_USER_ENV: "config-user"}):
            assert resolve_source_user(req, None) == "header-user"

    def test_config_when_no_auth_no_header(self):
        """Without auth and header: config fallback."""
        req = _mock_request()
        with patch.dict(os.environ, {DEFAULT_USER_ENV: "config-user"}):
            assert resolve_source_user(req, None) == "config-user"
