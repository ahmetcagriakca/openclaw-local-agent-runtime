"""Path resolver — D-049 canonical path resolution and containment checks."""
import os
import re


def resolve_canonical(raw_path: str, base_dir: str = None) -> str | None:
    """Resolve to canonical absolute path. Returns None if resolution fails.

    D-058 hardening:
    - Null byte injection → None
    - UNC paths (\\\\server\\...) → None
    """
    try:
        # D-058: Reject null bytes
        if '\x00' in raw_path:
            return None
        # D-058: Reject UNC paths
        if raw_path.startswith('\\\\'):
            return None
        if base_dir and not os.path.isabs(raw_path):
            raw_path = os.path.join(base_dir, raw_path)
        resolved = os.path.realpath(os.path.normpath(raw_path))
        return resolved
    except (OSError, ValueError):
        return None


def is_path_within(resolved_path: str, allowed_paths: list[str]) -> bool:
    """Check if resolved path is exactly one of the allowed paths."""
    normalized = os.path.normcase(resolved_path)
    return any(os.path.normcase(p) == normalized for p in allowed_paths)


def is_path_under_directory(resolved_path: str, allowed_dirs: list[str]) -> bool:
    """Check if resolved path is under one of the allowed directories."""
    normalized = os.path.normcase(resolved_path)
    for d in allowed_dirs:
        norm_d = os.path.normcase(d)
        if normalized == norm_d or normalized.startswith(norm_d + os.sep):
            return True
    return False


def is_path_forbidden(resolved_path: str, forbidden_dirs: list[str],
                      forbidden_patterns: list[str]) -> bool:
    """Check if resolved path falls in a forbidden zone."""
    normalized = os.path.normcase(resolved_path)
    # Check forbidden directories
    for d in forbidden_dirs:
        norm_d = os.path.normcase(d)
        if normalized == norm_d or normalized.startswith(norm_d + os.sep):
            return True
    # Check forbidden patterns
    for pattern in forbidden_patterns:
        if re.search(pattern, resolved_path, re.IGNORECASE):
            return True
    return False
