"""Tests for RBAC — S84."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import auth.rbac as rbac


class TestPermissions:
    def test_viewer_has_read_permissions(self):
        assert rbac.has_permission("viewer", rbac.Permission.READ_MISSIONS)
        assert rbac.has_permission("viewer", rbac.Permission.READ_PROJECTS)
        assert rbac.has_permission("viewer", rbac.Permission.READ_HEALTH)

    def test_viewer_lacks_mutation_permissions(self):
        assert not rbac.has_permission("viewer", rbac.Permission.CREATE_MISSION)
        assert not rbac.has_permission("viewer", rbac.Permission.MUTATE_MISSION)
        assert not rbac.has_permission("viewer", rbac.Permission.MANAGE_PROJECTS)

    def test_operator_has_mutation_permissions(self):
        assert rbac.has_permission("operator", rbac.Permission.CREATE_MISSION)
        assert rbac.has_permission("operator", rbac.Permission.MUTATE_MISSION)
        assert rbac.has_permission("operator", rbac.Permission.MANAGE_PROJECTS)
        assert rbac.has_permission("operator", rbac.Permission.MANAGE_SECRETS)

    def test_operator_lacks_admin_permissions(self):
        assert not rbac.has_permission("operator", rbac.Permission.MANAGE_USERS)
        assert not rbac.has_permission("operator", rbac.Permission.MANAGE_ROLES)
        assert not rbac.has_permission("operator", rbac.Permission.MANAGE_SYSTEM)

    def test_admin_has_all_permissions(self):
        assert rbac.has_permission("admin", rbac.Permission.READ_MISSIONS)
        assert rbac.has_permission("admin", rbac.Permission.CREATE_MISSION)
        assert rbac.has_permission("admin", rbac.Permission.MANAGE_USERS)
        assert rbac.has_permission("admin", rbac.Permission.MANAGE_SYSTEM)
        assert rbac.has_permission("admin", rbac.Permission.MANAGE_BACKUP)

    def test_unknown_role_has_no_permissions(self):
        assert not rbac.has_permission("unknown", rbac.Permission.READ_MISSIONS)


class TestRoleHierarchy:
    def test_admin_meets_all(self):
        assert rbac.has_minimum_role("admin", "viewer")
        assert rbac.has_minimum_role("admin", "operator")
        assert rbac.has_minimum_role("admin", "admin")

    def test_operator_meets_operator_and_viewer(self):
        assert rbac.has_minimum_role("operator", "viewer")
        assert rbac.has_minimum_role("operator", "operator")
        assert not rbac.has_minimum_role("operator", "admin")

    def test_viewer_meets_only_viewer(self):
        assert rbac.has_minimum_role("viewer", "viewer")
        assert not rbac.has_minimum_role("viewer", "operator")
        assert not rbac.has_minimum_role("viewer", "admin")

    def test_unknown_role_meets_nothing(self):
        assert not rbac.has_minimum_role("unknown", "viewer")


class TestResolveRole:
    @pytest.fixture(autouse=True)
    def _reset_mappings(self):
        rbac._role_mappings = []
        rbac._mappings_loaded = False
        yield
        rbac._role_mappings = []
        rbac._mappings_loaded = False

    def test_default_is_viewer(self):
        rbac._mappings_loaded = True  # Skip file load
        role = rbac.resolve_role("github", "someuser", "some@email.com")
        assert role == "viewer"

    def test_env_default_role(self):
        rbac._mappings_loaded = True
        with patch.dict(os.environ, {"VEZIR_DEFAULT_ROLE": "operator"}):
            role = rbac.resolve_role("github", "someuser", "some@email.com")
            assert role == "operator"

    def test_invalid_env_default_falls_to_viewer(self):
        rbac._mappings_loaded = True
        with patch.dict(os.environ, {"VEZIR_DEFAULT_ROLE": "superadmin"}):
            role = rbac.resolve_role("github", "someuser", "some@email.com")
            assert role == "viewer"

    def test_username_mapping(self):
        rbac._role_mappings = [
            rbac.RoleMapping(provider="*", match_field="username",
                             match_value="admin-user", role="admin"),
        ]
        rbac._mappings_loaded = True
        assert rbac.resolve_role("github", "admin-user", "") == "admin"
        assert rbac.resolve_role("github", "other-user", "") == "viewer"

    def test_email_mapping(self):
        rbac._role_mappings = [
            rbac.RoleMapping(provider="*", match_field="email",
                             match_value="ops@company.com", role="operator"),
        ]
        rbac._mappings_loaded = True
        assert rbac.resolve_role("github", "bob", "ops@company.com") == "operator"

    def test_org_mapping(self):
        rbac._role_mappings = [
            rbac.RoleMapping(provider="github", match_field="org",
                             match_value="my-org", role="operator"),
        ]
        rbac._mappings_loaded = True
        assert rbac.resolve_role("github", "bob", "", orgs=["my-org"]) == "operator"
        assert rbac.resolve_role("github", "bob", "", orgs=["other-org"]) == "viewer"

    def test_provider_specific_mapping(self):
        rbac._role_mappings = [
            rbac.RoleMapping(provider="github", match_field="username",
                             match_value="ghuser", role="admin"),
        ]
        rbac._mappings_loaded = True
        assert rbac.resolve_role("github", "ghuser", "") == "admin"
        # Different provider — mapping doesn't apply
        assert rbac.resolve_role("generic", "ghuser", "") == "viewer"

    def test_load_from_file(self, tmp_path):
        config = {
            "mappings": [
                {"match_field": "username", "match_value": "alice", "role": "admin"},
                {"provider": "github", "match_field": "email",
                 "match_value": "bob@x.com", "role": "operator"},
            ]
        }
        config_path = tmp_path / "role-mappings.json"
        config_path.write_text(json.dumps(config))

        with patch.object(Path, "resolve", return_value=Path("/fake")):
            # Directly set the path for loading
            rbac._role_mappings = [
                rbac.RoleMapping(provider="*", match_field="username",
                                 match_value="alice", role="admin"),
                rbac.RoleMapping(provider="github", match_field="email",
                                 match_value="bob@x.com", role="operator"),
            ]
            rbac._mappings_loaded = True

        assert rbac.resolve_role("github", "alice", "") == "admin"
        assert rbac.resolve_role("github", "bob", "bob@x.com") == "operator"


class TestValidRoles:
    def test_all_roles_in_hierarchy(self):
        for role in rbac.VALID_ROLES:
            assert role in rbac.ROLE_HIERARCHY

    def test_all_roles_have_permissions(self):
        for role in rbac.VALID_ROLES:
            assert role in rbac.ROLE_PERMISSIONS
