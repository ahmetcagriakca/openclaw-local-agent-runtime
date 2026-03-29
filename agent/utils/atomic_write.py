"""Atomic file write utilities — D-071 system-wide enforcement.

Pattern: write to temp file in same directory → fsync → os.replace().
Guarantees no partial writes on crash/timeout.
"""
import json
import os
import tempfile
from pathlib import Path

# Allowed root directories for writes (resolved at module load)
_ALLOWED_ROOTS: list[str] = []


def _init_allowed_roots() -> None:
    """Initialize allowed write roots from project layout."""
    global _ALLOWED_ROOTS
    if not _ALLOWED_ROOTS:
        project_root = Path(__file__).resolve().parent.parent.parent
        _ALLOWED_ROOTS = [
            str(project_root / "logs"),
            str(project_root / "config"),
            str(project_root / "evidence"),
            str(project_root / "agent"),
            str(project_root / "docs"),
            str(project_root / "baseline"),
            # Temp dirs are also allowed
            str(Path(tempfile.gettempdir()).resolve()),
        ]


def _validate_and_resolve(path: Path) -> str:
    """Validate path is safe and return resolved string path.

    Prevents path traversal by resolving to absolute and checking
    against allowed root directories.
    """
    _init_allowed_roots()
    resolved = str(path.resolve())

    # Check path doesn't traverse outside allowed roots
    if not any(resolved.startswith(root) for root in _ALLOWED_ROOTS):
        raise ValueError(
            f"Path outside allowed directories: {resolved}")

    return resolved


def atomic_write_json(path: Path | str, data: dict, indent: int = 2) -> None:
    """Write JSON atomically: temp -> fsync -> replace.

    Args:
        path: Target file path.
        data: Dict to serialize as JSON.
        indent: JSON indentation (default 2).

    Raises:
        OSError: If the write fails (temp file is cleaned up).
        TypeError: If data is not JSON-serializable.
        ValueError: If path is outside allowed directories.
    """
    safe_path = _validate_and_resolve(Path(path))
    parent_dir = os.path.dirname(safe_path)
    os.makedirs(parent_dir, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=parent_dir, suffix=".tmp",
        prefix=os.path.basename(safe_path).split('.')[0] + "-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, safe_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path | str, content: str) -> None:
    """Write text atomically: temp -> fsync -> replace.

    Args:
        path: Target file path.
        content: Text content to write.

    Raises:
        OSError: If the write fails (temp file is cleaned up).
        ValueError: If path is outside allowed directories.
    """
    safe_path = _validate_and_resolve(Path(path))
    parent_dir = os.path.dirname(safe_path)
    os.makedirs(parent_dir, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=parent_dir, suffix=".tmp",
        prefix=os.path.basename(safe_path).split('.')[0] + "-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, safe_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
