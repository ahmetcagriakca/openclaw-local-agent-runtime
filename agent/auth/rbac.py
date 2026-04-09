"""RBAC — Role-Based Access Control — S84.

Defines roles, permissions, and role mapping from OAuth claims.
Three roles: admin, operator, viewer.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("mcc.auth.rbac")


# ── Role definitions ───────────────────────────────────────────────

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

VALID_ROLES = {ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER}

# Permission hierarchy: admin > operator > viewer
ROLE_HIERARCHY = {
    ROLE_ADMIN: 3,
    ROLE_OPERATOR: 2,
    ROLE_VIEWER: 1,
}


# ── Permission matrix ─────────────────────────────────────────────

class Permission:
    """Permission constants."""
    # Read operations
    READ_MISSIONS = "missions:read"
    READ_PROJECTS = "projects:read"
    READ_HEALTH = "health:read"
    READ_TELEMETRY = "telemetry:read"
    READ_APPROVALS = "approvals:read"
    READ_POLICIES = "policies:read"
    READ_AUDIT = "audit:read"

    # Mutation operations
    CREATE_MISSION = "missions:create"
    MUTATE_MISSION = "missions:mutate"
    MANAGE_PROJECTS = "projects:manage"
    MANAGE_APPROVALS = "approvals:manage"
    MANAGE_POLICIES = "policies:manage"
    MANAGE_TEMPLATES = "templates:manage"
    MANAGE_PLUGINS = "plugins:manage"
    MANAGE_SECRETS = "secrets:manage"

    # Admin operations
    MANAGE_USERS = "users:manage"
    MANAGE_ROLES = "roles:manage"
    MANAGE_SYSTEM = "system:manage"
    VIEW_AUDIT_EXPORT = "audit:export"
    MANAGE_BACKUP = "backup:manage"


# Role → permissions mapping
ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_VIEWER: {
        Permission.READ_MISSIONS,
        Permission.READ_PROJECTS,
        Permission.READ_HEALTH,
        Permission.READ_TELEMETRY,
        Permission.READ_APPROVALS,
        Permission.READ_POLICIES,
        Permission.READ_AUDIT,
    },
    ROLE_OPERATOR: {
        # Inherits all viewer permissions
        Permission.READ_MISSIONS,
        Permission.READ_PROJECTS,
        Permission.READ_HEALTH,
        Permission.READ_TELEMETRY,
        Permission.READ_APPROVALS,
        Permission.READ_POLICIES,
        Permission.READ_AUDIT,
        # Mutation permissions
        Permission.CREATE_MISSION,
        Permission.MUTATE_MISSION,
        Permission.MANAGE_PROJECTS,
        Permission.MANAGE_APPROVALS,
        Permission.MANAGE_POLICIES,
        Permission.MANAGE_TEMPLATES,
        Permission.MANAGE_PLUGINS,
        Permission.MANAGE_SECRETS,
    },
    ROLE_ADMIN: {
        # All permissions
        Permission.READ_MISSIONS,
        Permission.READ_PROJECTS,
        Permission.READ_HEALTH,
        Permission.READ_TELEMETRY,
        Permission.READ_APPROVALS,
        Permission.READ_POLICIES,
        Permission.READ_AUDIT,
        Permission.CREATE_MISSION,
        Permission.MUTATE_MISSION,
        Permission.MANAGE_PROJECTS,
        Permission.MANAGE_APPROVALS,
        Permission.MANAGE_POLICIES,
        Permission.MANAGE_TEMPLATES,
        Permission.MANAGE_PLUGINS,
        Permission.MANAGE_SECRETS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_ROLES,
        Permission.MANAGE_SYSTEM,
        Permission.VIEW_AUDIT_EXPORT,
        Permission.MANAGE_BACKUP,
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms


def has_minimum_role(user_role: str, required_role: str) -> bool:
    """Check if user's role meets or exceeds the required role level."""
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level


# ── Role mapping from OAuth claims ────────────────────────────────

@dataclass
class RoleMapping:
    """Maps OAuth identity to Vezir role."""
    provider: str  # "github", "*"
    match_field: str  # "username", "email", "org"
    match_value: str  # exact match value
    role: str  # target role


_role_mappings: list[RoleMapping] = []
_mappings_loaded = False


def _load_role_mappings() -> None:
    """Load role mappings from config/role-mappings.json."""
    global _role_mappings, _mappings_loaded

    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "role-mappings.json"
    if not config_path.exists():
        _role_mappings = []
        _mappings_loaded = True
        return

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        _role_mappings = [
            RoleMapping(
                provider=m.get("provider", "*"),
                match_field=m["match_field"],
                match_value=m["match_value"],
                role=m["role"],
            )
            for m in data.get("mappings", [])
            if m.get("role") in VALID_ROLES
        ]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to load role mappings: %s", e)
        _role_mappings = []
    _mappings_loaded = True


def resolve_role(
    provider: str,
    username: str,
    email: str,
    orgs: list[str] | None = None,
) -> str:
    """Resolve Vezir role from OAuth user attributes.

    Checks role-mappings.json for explicit mappings.
    Falls back to VEZIR_DEFAULT_ROLE env var, then 'viewer'.
    """
    import os

    if not _mappings_loaded:
        _load_role_mappings()

    # Build lookup dict for matching
    fields = {
        "username": username,
        "email": email,
    }
    # Add org memberships if available
    org_set = set(orgs or [])

    for mapping in _role_mappings:
        # Provider must match (or wildcard)
        if mapping.provider != "*" and mapping.provider != provider:
            continue

        if mapping.match_field == "org":
            if mapping.match_value in org_set:
                logger.info(
                    "Role mapping matched: org=%s → %s",
                    mapping.match_value, mapping.role,
                )
                return mapping.role
        else:
            field_value = fields.get(mapping.match_field, "")
            if field_value == mapping.match_value:
                logger.info(
                    "Role mapping matched: %s=%s → %s",
                    mapping.match_field, mapping.match_value, mapping.role,
                )
                return mapping.role

    # Default role from environment
    default_role = os.environ.get("VEZIR_DEFAULT_ROLE", ROLE_VIEWER)
    if default_role not in VALID_ROLES:
        default_role = ROLE_VIEWER
    return default_role


def reload_role_mappings() -> None:
    """Force reload role mappings."""
    global _mappings_loaded
    _mappings_loaded = False
    _load_role_mappings()
