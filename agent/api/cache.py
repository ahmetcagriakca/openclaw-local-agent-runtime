"""Incremental file cache — mtime-based cache for normalizer sources.

Avoids re-reading files when their mtime hasn't changed.
D-068: Corrupt JSON → error status, no stale data served.
"""
import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class CacheStatus(str, Enum):
    hit = "hit"
    miss = "miss"
    stale = "stale"
    error = "error"


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    errors: int = 0
    entries: int = 0


@dataclass
class _CacheEntry:
    data: dict | list | None = None
    mtime: float = 0.0
    status: CacheStatus = CacheStatus.miss


class IncrementalFileCache:
    def __init__(self):
        self._cache: dict[str, _CacheEntry] = {}
        self._stats = CacheStats()

    def get(self, path: Path | str) -> tuple[Optional[dict | list], CacheStatus]:
        """Get cached file content.

        Returns (data, status):
        - (data, hit): mtime unchanged, served from cache
        - (data, miss): first read or mtime changed, re-read from disk
        - (None, error): file missing or corrupt JSON
        """
        path = str(path)
        try:
            current_mtime = os.path.getmtime(path)
        except OSError:
            self._stats.errors += 1
            return None, CacheStatus.error

        entry = self._cache.get(path)
        if entry and entry.mtime == current_mtime:
            self._stats.hits += 1
            return entry.data, CacheStatus.hit

        # Miss — read from disk
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cache[path] = _CacheEntry(
                data=data, mtime=current_mtime, status=CacheStatus.hit)
            self._stats.misses += 1
            self._stats.entries = len(self._cache)
            return data, CacheStatus.miss
        except (json.JSONDecodeError, UnicodeDecodeError):
            # D-068: corrupt → error, don't serve stale
            self._cache.pop(path, None)
            self._stats.errors += 1
            return None, CacheStatus.error
        except OSError:
            self._stats.errors += 1
            return None, CacheStatus.error

    def invalidate(self, path: Path | str) -> None:
        """Remove a path from cache."""
        self._cache.pop(str(path), None)

    def stats(self) -> CacheStats:
        """Return cache statistics."""
        self._stats.entries = len(self._cache)
        return self._stats
