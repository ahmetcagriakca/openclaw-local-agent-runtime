"""Audit log tamper resistance — B-008 / D-129.

SHA-256 hash chain on structured audit log entries.
Single append owner. JSONL format.
"""
import hashlib
import json
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("mcc.audit_integrity")

AUDIT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "audit"
)
AUDIT_PATH = os.path.join(AUDIT_DIR, "audit.jsonl")

# D-129: Genesis prev_hash = SHA-256 of empty string
GENESIS_HASH = hashlib.sha256(b"").hexdigest()


def _compute_entry_hash(entry: dict, prev_hash: str) -> str:
    """Compute SHA-256 hash for an audit entry per D-129.

    Hash input = prev_hash + canonical JSON (sorted keys, UTF-8, entry_hash excluded).
    """
    hashable = {k: v for k, v in entry.items() if k != "entry_hash"}
    canonical = json.dumps(hashable, sort_keys=True, ensure_ascii=False)
    payload = prev_hash + canonical
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_entry(event: str, actor: str, detail: str = "",
                 audit_path: str = None) -> dict:
    """Append a new entry to the audit log with hash chain.

    This is the SINGLE runtime append owner per D-129.
    Returns the appended entry.
    """
    path = audit_path or AUDIT_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Get prev_hash from last entry or use genesis
    prev_hash = GENESIS_HASH
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last = json.loads(lines[-1])
                prev_hash = last.get("entry_hash", GENESIS_HASH)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "actor": actor,
        "detail": detail,
        "prev_hash": prev_hash,
    }
    entry["entry_hash"] = _compute_entry_hash(entry, prev_hash)

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")

    return entry


def verify_chain(audit_path: str = None) -> dict:
    """Verify audit log hash chain integrity per D-129.

    Returns:
        {"status": "INTEGRITY_OK", "entry_count": N} on success
        {"status": "INTEGRITY_FAIL", "broken_entry_index": N, "reason": str} on failure
    """
    path = audit_path or AUDIT_PATH

    if not os.path.exists(path):
        return {"status": "INTEGRITY_OK", "entry_count": 0}

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return {"status": "INTEGRITY_OK", "entry_count": 0}

    prev_hash = GENESIS_HASH
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return {
                "status": "INTEGRITY_FAIL",
                "broken_entry_index": i,
                "reason": f"Malformed JSON at entry {i}",
            }

        stored_hash = entry.get("entry_hash")
        if not stored_hash:
            return {
                "status": "INTEGRITY_FAIL",
                "broken_entry_index": i,
                "reason": f"Missing entry_hash at entry {i}",
            }

        expected_prev = entry.get("prev_hash")
        if expected_prev != prev_hash:
            return {
                "status": "INTEGRITY_FAIL",
                "broken_entry_index": i,
                "reason": f"prev_hash mismatch at entry {i}",
            }

        computed = _compute_entry_hash(entry, prev_hash)
        if computed != stored_hash:
            return {
                "status": "INTEGRITY_FAIL",
                "broken_entry_index": i,
                "reason": f"entry_hash mismatch at entry {i} (tampered?)",
            }

        prev_hash = stored_hash

    return {"status": "INTEGRITY_OK", "entry_count": len(lines)}
