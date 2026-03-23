"""Summary cache — caches artifact summaries for zero-cost reuse."""


class SummaryCache:
    """Cache artifact summaries. Key: (artifactId, compressionLevel)."""

    def __init__(self):
        self._cache = {}  # (artifactId, level) -> summary_text
        self._hits = 0
        self._misses = 0

    def get(self, artifact_id: str, level: str = "B") -> str | None:
        """Get cached summary. Returns None on miss."""
        key = (artifact_id, level)
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, artifact_id: str, summary: str, level: str = "B"):
        """Store summary in cache."""
        self._cache[(artifact_id, level)] = summary

    def has(self, artifact_id: str, level: str = "B") -> bool:
        return (artifact_id, level) in self._cache

    def stats(self) -> dict:
        return {"hits": self._hits, "misses": self._misses,
                "entries": len(self._cache)}

    def clear(self):
        self._cache.clear()
        self._hits = 0
        self._misses = 0


def generate_basic_summary(artifact: dict, max_tokens: int = 500) -> str:
    """Generate a basic summary without LLM.

    Preserves structural keys + IDs + critical values.
    Truncates non-critical values.
    """
    data = artifact.get("data", artifact)
    header = artifact.get("_artifact_header", {})

    summary_parts = []

    # Header identity
    if header:
        summary_parts.append(
            f"[{header.get('artifactType', '?')}] "
            f"by {header.get('producedByRole', '?')} "
            f"at stage {header.get('producedByStage', '?')}"
        )

    # Structural summary — keys + first 100 chars of values
    for key, value in data.items():
        if isinstance(value, str):
            truncated = value[:100] + "..." if len(value) > 100 else value
            summary_parts.append(f"  {key}: {truncated}")
        elif isinstance(value, list):
            summary_parts.append(f"  {key}: [{len(value)} items]")
        elif isinstance(value, dict):
            summary_parts.append(f"  {key}: {{{', '.join(value.keys())}}}")
        else:
            summary_parts.append(f"  {key}: {value}")

    full_summary = "\n".join(summary_parts)

    # Rough token truncation
    if len(full_summary) > max_tokens * 4:
        full_summary = full_summary[:max_tokens * 4] + "\n[truncated]"

    return full_summary


def generate_metadata_view(artifact: dict) -> dict:
    """Generate metadata-only view (Tier A).

    Field names + types + IDs, no bodies.
    """
    data = artifact.get("data", artifact)
    header = artifact.get("_artifact_header", {})

    meta = {"_header": {
        "artifactId": header.get("artifactId"),
        "artifactType": header.get("artifactType"),
        "version": header.get("version"),
        "sizeTokens": header.get("sizeTokens")
    }}

    for key, value in data.items():
        if isinstance(value, str):
            meta[key] = {"type": "string", "length": len(value)}
        elif isinstance(value, list):
            meta[key] = {"type": "array", "count": len(value)}
        elif isinstance(value, dict):
            meta[key] = {"type": "object", "keys": list(value.keys())}
        else:
            meta[key] = {"type": type(value).__name__, "value": value}

    return meta
