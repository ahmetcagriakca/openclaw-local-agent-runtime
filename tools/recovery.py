"""B-023 Corrupted Runtime Recovery — detect and recover corrupted mission state.

Scans logs/missions/ for corrupted JSON files:
- Truncated JSON (incomplete writes)
- Invalid JSON syntax
- Missing required fields (missionId, status, stages)
- Orphaned state/summary files without parent mission

Actions:
- quarantine: move to logs/missions/quarantine/
- repair: attempt auto-repair of truncated JSON
- report: list all issues without taking action

Usage:
    python tools/recovery.py scan                  # report-only scan
    python tools/recovery.py repair                # attempt auto-repair
    python tools/recovery.py quarantine             # move corrupted to quarantine
    python tools/recovery.py scan --json            # JSON output
"""
import argparse
import json
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("mcc.recovery")

OC_ROOT = Path(__file__).resolve().parent.parent
MISSIONS_DIR = OC_ROOT / "logs" / "missions"
QUARANTINE_DIR = MISSIONS_DIR / "quarantine"

REQUIRED_FIELDS = {"missionId", "status"}
VALID_STATUSES = {
    "planning", "executing", "running", "completed", "failed",
    "cancelled", "timed_out", "approval_pending",
}

# Auxiliary file suffixes (not standalone missions)
AUX_SUFFIXES = ("-state.json", "-summary.json", "-token-report.json")


class RecoveryIssue:
    """Single detected issue in a mission file."""

    __slots__ = ("path", "issue_type", "detail", "repairable")

    def __init__(self, path: Path, issue_type: str, detail: str,
                 repairable: bool = False):
        self.path = path
        self.issue_type = issue_type
        self.detail = detail
        self.repairable = repairable

    def to_dict(self) -> dict:
        return {
            "file": str(self.path.name),
            "type": self.issue_type,
            "detail": self.detail,
            "repairable": self.repairable,
        }


def scan_missions(missions_dir: Path | None = None) -> list[RecoveryIssue]:
    """Scan mission files for corruption issues.

    Returns list of RecoveryIssue objects.
    """
    missions_dir = missions_dir or MISSIONS_DIR
    issues: list[RecoveryIssue] = []

    if not missions_dir.exists():
        return issues

    mission_ids: set[str] = set()
    canonical_files: dict[str, Path] = {}

    # First pass: identify canonical mission files
    for f in sorted(missions_dir.glob("*.json")):
        if f.name == "quarantine":
            continue
        is_aux = any(f.name.endswith(s) for s in AUX_SUFFIXES)

        # Try to parse
        try:
            raw = f.read_text(encoding="utf-8")
        except OSError as e:
            issues.append(RecoveryIssue(
                f, "read_error", f"Cannot read file: {e}"))
            continue

        if not raw.strip():
            issues.append(RecoveryIssue(
                f, "empty_file", "File is empty", repairable=False))
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            # Check if truncated (missing closing brace)
            repairable = _is_truncated_json(raw)
            issues.append(RecoveryIssue(
                f, "invalid_json",
                f"JSON parse error at line {e.lineno}: {e.msg}",
                repairable=repairable))
            continue

        if not isinstance(data, dict):
            issues.append(RecoveryIssue(
                f, "not_object", "Root value is not a JSON object"))
            continue

        if is_aux:
            # Track for orphan detection
            continue

        # Canonical mission file — check required fields
        mid = data.get("missionId", "")
        if mid:
            mission_ids.add(mid)
            canonical_files[mid] = f

        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            issues.append(RecoveryIssue(
                f, "missing_fields",
                f"Missing required fields: {', '.join(sorted(missing))}"))

        status = data.get("status", "")
        if status and status not in VALID_STATUSES:
            issues.append(RecoveryIssue(
                f, "invalid_status",
                f"Unknown status: {status}"))

        # Check stages array
        stages = data.get("stages")
        if stages is not None and not isinstance(stages, list):
            issues.append(RecoveryIssue(
                f, "invalid_stages", "stages field is not a list"))

    # Second pass: check for orphaned auxiliary files
    for f in sorted(missions_dir.glob("*.json")):
        is_aux = any(f.name.endswith(s) for s in AUX_SUFFIXES)
        if not is_aux:
            continue
        # Extract mission ID from aux filename
        name = f.name
        for suffix in AUX_SUFFIXES:
            if name.endswith(suffix):
                base = name[:-len(suffix)]
                # Check if parent mission exists
                parent = missions_dir / f"{base}.json"
                if not parent.exists():
                    issues.append(RecoveryIssue(
                        f, "orphaned_aux",
                        f"Auxiliary file without parent mission: {base}"))
                break

    return issues


def _is_truncated_json(raw: str) -> bool:
    """Heuristic: JSON looks truncated (has opening brace but no matching close)."""
    stripped = raw.strip()
    if not stripped:
        return False
    open_braces = stripped.count("{") + stripped.count("[")
    close_braces = stripped.count("}") + stripped.count("]")
    return open_braces > close_braces and stripped[0] in "{["


def repair_truncated(path: Path) -> bool:
    """Attempt to repair a truncated JSON file.

    Strategy: add missing closing braces/brackets.
    Only works for simple truncation (missing trailing delimiters).
    Returns True if repair succeeded.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return False

    if not raw.strip():
        return False

    # Count open/close delimiters
    repaired = raw.rstrip()

    # Track delimiter stack
    stack: list[str] = []
    in_string = False
    escape = False

    for ch in repaired:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack:
                stack.pop()

    if not stack:
        return False  # Already balanced

    # Add missing closers
    repaired += "".join(reversed(stack)) + "\n"

    # Validate repaired JSON
    try:
        json.loads(repaired)
    except json.JSONDecodeError:
        return False

    # Write repaired file atomically
    sys.path.insert(0, str(OC_ROOT / "agent"))
    from utils.atomic_write import atomic_write_text
    atomic_write_text(path, repaired)
    return True


def quarantine_file(path: Path, quarantine_dir: Path | None = None) -> Path:
    """Move a corrupted file to quarantine directory.

    Returns the new path in quarantine.
    """
    quarantine_dir = quarantine_dir or QUARANTINE_DIR
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    dest = quarantine_dir / f"{ts}_{path.name}"
    shutil.move(str(path), str(dest))
    return dest


def run_scan(missions_dir: Path | None = None, output_json: bool = False) -> list[RecoveryIssue]:
    """Run scan and print results."""
    issues = scan_missions(missions_dir)
    if output_json:
        print(json.dumps([i.to_dict() for i in issues], indent=2))
    else:
        if not issues:
            print("No corruption detected.")
        else:
            print(f"Found {len(issues)} issue(s):\n")
            for i in issues:
                repair_tag = " [REPAIRABLE]" if i.repairable else ""
                print(f"  {i.path.name}: {i.issue_type} — {i.detail}{repair_tag}")
    return issues


def run_repair(missions_dir: Path | None = None) -> dict:
    """Scan and attempt to repair repairable issues."""
    issues = scan_missions(missions_dir)
    repaired = 0
    failed = 0
    for issue in issues:
        if issue.repairable and issue.issue_type == "invalid_json":
            if repair_truncated(issue.path):
                repaired += 1
                print(f"  REPAIRED: {issue.path.name}")
            else:
                failed += 1
                print(f"  FAILED:   {issue.path.name}")
    result = {
        "total_issues": len(issues),
        "repair_attempted": repaired + failed,
        "repaired": repaired,
        "failed": failed,
    }
    print(f"\nRepair: {repaired}/{repaired + failed} succeeded")
    return result


def run_quarantine(missions_dir: Path | None = None,
                   quarantine_dir: Path | None = None) -> dict:
    """Scan and quarantine all corrupted files."""
    issues = scan_missions(missions_dir)
    quarantined = 0
    for issue in issues:
        if issue.path.exists():
            dest = quarantine_file(issue.path, quarantine_dir)
            quarantined += 1
            print(f"  QUARANTINED: {issue.path.name} → {dest.name}")
    result = {
        "total_issues": len(issues),
        "quarantined": quarantined,
    }
    print(f"\nQuarantined {quarantined} file(s)")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="B-023: Corrupted runtime recovery for mission files")
    parser.add_argument(
        "action", choices=["scan", "repair", "quarantine"],
        help="Action to perform")
    parser.add_argument(
        "--json", action="store_true", dest="output_json",
        help="Output results as JSON (scan only)")
    args = parser.parse_args()

    if args.action == "scan":
        run_scan(output_json=args.output_json)
    elif args.action == "repair":
        run_repair()
    elif args.action == "quarantine":
        run_quarantine()


if __name__ == "__main__":
    main()
