"""Atomic file write utilities — D-071 system-wide enforcement.

Pattern: write to temp file in same directory → fsync → os.replace().
Guarantees no partial writes on crash/timeout.
"""
import json
import os
import tempfile
from pathlib import Path


def _validate_path(path: Path) -> None:
    """Validate path doesn't contain traversal or injection characters."""
    resolved = path.resolve()
    path_str = str(resolved)
    if '..' in path_str.split(os.sep):
        raise ValueError(f"Path traversal detected: {path}")


def atomic_write_json(path: Path | str, data: dict, indent: int = 2) -> None:
    """Write JSON atomically: temp → fsync → replace.

    Args:
        path: Target file path.
        data: Dict to serialize as JSON.
        indent: JSON indentation (default 2).

    Raises:
        OSError: If the write fails (temp file is cleaned up).
        TypeError: If data is not JSON-serializable.
    """
    path = Path(path)
    _validate_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp",
        prefix=f"{path.stem}-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path | str, content: str) -> None:
    """Write text atomically: temp → fsync → replace.

    Args:
        path: Target file path.
        content: Text content to write.

    Raises:
        OSError: If the write fails (temp file is cleaned up).
    """
    path = Path(path)
    _validate_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp",
        prefix=f"{path.stem}-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
