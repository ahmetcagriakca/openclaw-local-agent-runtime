"""User isolation helpers — Sprint 40.

Provides user-scoped data filtering for multi-user environments.
When auth is not configured, returns all data (single-operator mode).
When auth is active, filters by authenticated user's user_id.
"""
from typing import Optional

from auth.keys import ApiKey, is_auth_enabled


def get_user_id(user: Optional[ApiKey]) -> Optional[str]:
    """Extract user_id from authenticated user. Returns None if no isolation needed."""
    if not is_auth_enabled():
        return None  # Single-operator mode — no filtering
    if user is None:
        return None  # Unauthenticated — no filtering (GET endpoints)
    return user.user_id or user.name


def filter_by_owner(items: list[dict], user_id: Optional[str],
                    owner_field: str = "userId") -> list[dict]:
    """Filter a list of dicts by owner user_id.

    When user_id is None (no auth or single-operator), returns all items.
    When user_id is set, only returns items where owner_field matches.
    Items without the owner_field are included (backwards compatibility).
    """
    if user_id is None:
        return items
    return [
        item for item in items
        if item.get(owner_field) in (None, "", user_id)
    ]


def check_ownership(item: dict, user_id: Optional[str],
                    owner_field: str = "userId") -> bool:
    """Check if a user owns a specific item.

    Returns True if:
    - No isolation needed (user_id is None)
    - Item has no owner (backwards compatibility)
    - Item owner matches user_id
    """
    if user_id is None:
        return True
    item_owner = item.get(owner_field)
    if not item_owner:
        return True  # No owner set — allow (backwards compat)
    return item_owner == user_id
