#!/usr/bin/env python3
"""Decision drift scanner for DECISIONS.md.

Scans frozen decisions for potential implementation drift indicators.
No external dependencies — stdlib only.

Usage:
    python tools/verify_decision_drift.py
"""

import re
import sys
from pathlib import Path

DECISIONS_PATH = Path(__file__).resolve().parent.parent / "docs" / "ai" / "DECISIONS.md"

# Patterns that may indicate drift (tool/pattern adopted after decision was frozen)
DRIFT_KEYWORDS = [
    "deferred", "not yet", "manual", "no auto", "prohibited",
    "later phase", "future sprint", "not implemented", "placeholder",
]


def parse_decisions(text: str) -> list[dict]:
    """Extract decision entries from DECISIONS.md."""
    pattern = re.compile(
        r"### (D-\d{3}): (.+)\n\n"
        r"\*\*Phase:\*\* (.+?) \| \*\*Status:\*\* (\w+)",
        re.MULTILINE,
    )
    decisions = []
    for m in pattern.finditer(text):
        # Grab body text until next --- or ### heading
        start = m.end()
        next_sep = text.find("\n---", start)
        next_head = text.find("\n### ", start)
        end = min(p for p in (next_sep, next_head, len(text)) if p > 0)
        body = text[start:end].strip()
        decisions.append({
            "id": m.group(1),
            "title": m.group(2),
            "phase": m.group(3),
            "status": m.group(4),
            "body": body,
        })
    return decisions


def scan_drift(decisions: list[dict]) -> list[dict]:
    """Flag frozen decisions whose body contains drift keywords."""
    flagged = []
    for d in decisions:
        if d["status"] != "Frozen":
            continue
        hits = [kw for kw in DRIFT_KEYWORDS if kw in d["body"].lower()]
        if hits:
            flagged.append({"decision": d, "keywords": hits})
    return flagged


def main() -> None:
    if not DECISIONS_PATH.exists():
        print(f"ERROR: {DECISIONS_PATH} not found", file=sys.stderr)
        sys.exit(1)

    text = DECISIONS_PATH.read_text(encoding="utf-8")
    decisions = parse_decisions(text)

    # Status counts
    counts: dict[str, int] = {}
    for d in decisions:
        counts[d["status"]] = counts.get(d["status"], 0) + 1

    print("=== Decision Drift Scan ===")
    print(f"Total decisions scanned: {len(decisions)}")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

    flagged = scan_drift(decisions)
    print(f"\nFrozen decisions with drift indicators: {len(flagged)}")
    for item in flagged:
        d = item["decision"]
        kws = ", ".join(item["keywords"])
        print(f"  {d['id']}: {d['title']}")
        print(f"    Keywords: {kws}")

    if not flagged:
        print("  (none — all clear)")

    print("\nDone.")


if __name__ == "__main__":
    main()
