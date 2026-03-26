"""AuditTrail handler — chain-hash immutable event log.

Registered as a global handler (priority=0) so it sees every event.
Never halts. Writes to append-only JSONL with chain hash for tamper
detection.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone

from events.bus import Event, HandlerResult

logger = logging.getLogger("mcc.audit")

AUDIT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs"
)


class AuditTrailHandler:
    """Immutable chain-hash audit log. Global handler, priority 0."""

    def __init__(self, log_dir: str | None = None):
        self.log_dir = log_dir or AUDIT_DIR
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path = os.path.join(self.log_dir, "audit-trail.jsonl")
        self._prev_hash = "genesis"
        self._count = 0

        # Resume chain from last entry if file exists
        if os.path.isfile(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            self._prev_hash = entry.get("hash", self._prev_hash)
                            self._count += 1
            except Exception:
                pass  # start fresh chain on corrupt file

    def __call__(self, event: Event) -> HandlerResult:
        """Log event with chain hash. Never halts."""
        entry = {
            "seq": self._count,
            "ts": event.ts.isoformat(),
            "type": event.type,
            "source": event.source,
            "correlation_id": event.correlation_id,
            "data": self._sanitize(event.data),
            "prev_hash": self._prev_hash,
        }

        # Chain hash: SHA256(prev_hash + json(entry without hash))
        entry_json = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry["hash"] = hashlib.sha256(
            (self._prev_hash + entry_json).encode()
        ).hexdigest()[:16]

        self._prev_hash = entry["hash"]
        self._count += 1

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("[AUDIT] Write failed: %s", e)

        return HandlerResult.proceed()

    def verify_chain(self) -> tuple[bool, int, str]:
        """Verify the chain hash integrity.

        Returns: (valid, entries_checked, error_message)
        """
        if not os.path.isfile(self.log_path):
            return True, 0, ""

        prev_hash = "genesis"
        count = 0

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    return False, count, f"Line {line_num}: invalid JSON"

                stored_hash = entry.pop("hash", None)
                if entry.get("prev_hash") != prev_hash:
                    return False, count, (
                        f"Line {line_num}: prev_hash mismatch "
                        f"(expected {prev_hash}, got {entry.get('prev_hash')})")

                entry_json = json.dumps(entry, sort_keys=True, ensure_ascii=False)
                expected_hash = hashlib.sha256(
                    (prev_hash + entry_json).encode()
                ).hexdigest()[:16]

                if stored_hash != expected_hash:
                    return False, count, (
                        f"Line {line_num}: hash mismatch "
                        f"(expected {expected_hash}, got {stored_hash})")

                prev_hash = stored_hash
                count += 1

        return True, count, ""

    @staticmethod
    def _sanitize(data: dict) -> dict:
        """Remove large binary data from audit log entries."""
        sanitized = {}
        for k, v in data.items():
            if isinstance(v, str) and len(v) > 2000:
                sanitized[k] = v[:200] + f"...[truncated {len(v)} chars]"
            elif isinstance(v, bytes):
                sanitized[k] = f"[bytes: {len(v)}]"
            else:
                sanitized[k] = v
        return sanitized
