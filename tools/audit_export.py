"""Audit Export CLI — compliance-ready audit archive.

Sprint 55 Task 55.1 (B-115): Bundles mission logs, policy evaluations,
approval records, and DLQ events into a ZIP archive with SHA-256 checksum.

Usage:
    python tools/audit_export.py --help
    python tools/audit_export.py export
    python tools/audit_export.py export --from 2026-01-01 --to 2026-04-01
    python tools/audit_export.py export --mission-id abc123
    python tools/audit_export.py export --user-id akca
    python tools/audit_export.py export --format csv
"""
import argparse
import csv
import hashlib
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OC_ROOT = SCRIPT_DIR.parent
DEFAULT_EXPORT_DIR = OC_ROOT / "audit-exports"

# Source paths
MISSIONS_DIR = OC_ROOT / "logs" / "missions"
MISSION_HISTORY = OC_ROOT / "logs" / "mission-history.json"
DLQ_PATH = OC_ROOT / "logs" / "dlq.json"
AUDIT_LOG = OC_ROOT / "logs" / "audit" / "audit.jsonl"
APPROVALS_DIR = OC_ROOT / "logs" / "approvals"
POLICIES_DIR = OC_ROOT / "config" / "policies"

MAX_MISSIONS = 1000
EXPORT_TIMEOUT_SECONDS = 60

# Fields to redact from export
REDACT_FIELDS = {"api_key", "secret", "token", "password", "credential",
                 "llm_response", "raw_response", "response_text"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _redact_dict(d: dict) -> dict:
    """Strip sensitive fields from a dict recursively."""
    result = {}
    for k, v in d.items():
        if any(s in k.lower() for s in REDACT_FIELDS):
            result[k] = "[REDACTED]"
        elif isinstance(v, dict):
            result[k] = _redact_dict(v)
        elif isinstance(v, list):
            result[k] = [_redact_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result


def _parse_ts(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def _in_range(ts_str: str | None, from_dt: datetime | None,
              to_dt: datetime | None) -> bool:
    if not ts_str:
        return from_dt is None and to_dt is None
    ts = _parse_ts(ts_str)
    if ts is None:
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if from_dt and from_dt.tzinfo is None:
        from_dt = from_dt.replace(tzinfo=timezone.utc)
    if to_dt and to_dt.tzinfo is None:
        to_dt = to_dt.replace(tzinfo=timezone.utc)
    if from_dt and ts < from_dt:
        return False
    if to_dt and ts > to_dt:
        return False
    return True


def _load_missions(mission_id: str | None = None,
                   user_id: str | None = None,
                   from_dt: datetime | None = None,
                   to_dt: datetime | None = None) -> list[dict]:
    """Load and filter mission records."""
    missions = []

    # Load from mission history
    if MISSION_HISTORY.exists():
        try:
            data = json.loads(MISSION_HISTORY.read_text(encoding="utf-8"))
            if isinstance(data, list):
                missions.extend(data)
            elif isinstance(data, dict) and "missions" in data:
                missions.extend(data["missions"])
        except (json.JSONDecodeError, OSError):
            pass

    # Load individual mission files
    if MISSIONS_DIR.exists():
        for f in MISSIONS_DIR.glob("mission-*.json"):
            if f.name.endswith("-state.json") or f.name.endswith("-summary.json"):
                continue
            try:
                m = json.loads(f.read_text(encoding="utf-8"))
                if not any(em.get("id") == m.get("id") or
                           em.get("missionId") == m.get("missionId")
                           for em in missions):
                    missions.append(m)
            except (json.JSONDecodeError, OSError):
                pass

    # Filter
    filtered = []
    for m in missions:
        mid = m.get("id") or m.get("missionId", "")
        if mission_id and mid != mission_id:
            continue
        if user_id:
            m_user = m.get("operator") or m.get("sourceUserId", "")
            if m_user != user_id:
                continue
        ts = m.get("ts") or m.get("startedAt") or m.get("completedAt")
        if not _in_range(ts, from_dt, to_dt):
            continue
        filtered.append(_redact_dict(m))
        if len(filtered) >= MAX_MISSIONS:
            break

    return filtered


def _load_dlq(mission_id: str | None = None,
              from_dt: datetime | None = None,
              to_dt: datetime | None = None) -> list[dict]:
    """Load and filter DLQ records."""
    if not DLQ_PATH.exists():
        return []
    try:
        data = json.loads(DLQ_PATH.read_text(encoding="utf-8"))
        entries = data if isinstance(data, list) else data.get("entries", [])
    except (json.JSONDecodeError, OSError):
        return []

    filtered = []
    for e in entries:
        if mission_id and e.get("mission_id") != mission_id:
            continue
        ts = e.get("failed_at") or e.get("timestamp")
        if not _in_range(ts, from_dt, to_dt):
            continue
        filtered.append(_redact_dict(e))
    return filtered


def _load_audit_log(from_dt: datetime | None = None,
                    to_dt: datetime | None = None) -> list[dict]:
    """Load and filter audit log entries."""
    if not AUDIT_LOG.exists():
        return []
    entries = []
    try:
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                ts = entry.get("timestamp")
                if _in_range(ts, from_dt, to_dt):
                    entries.append(entry)
    except (json.JSONDecodeError, OSError):
        pass
    return entries


def _load_approvals(mission_id: str | None = None,
                    from_dt: datetime | None = None,
                    to_dt: datetime | None = None) -> list[dict]:
    """Load and filter approval records."""
    if not APPROVALS_DIR.exists():
        return []
    approvals = []
    for f in APPROVALS_DIR.glob("*.json"):
        try:
            a = json.loads(f.read_text(encoding="utf-8"))
            if mission_id and a.get("missionId") != mission_id:
                continue
            ts = a.get("requestedAt") or a.get("respondedAt")
            if not _in_range(ts, from_dt, to_dt):
                continue
            approvals.append(_redact_dict(a))
        except (json.JSONDecodeError, OSError):
            pass
    return approvals


def _load_policies() -> list[dict]:
    """Load policy definitions (metadata only, no secrets)."""
    if not POLICIES_DIR.exists():
        return []
    policies = []
    for f in POLICIES_DIR.glob("*.yaml"):
        policies.append({"file": f.name, "size": f.stat().st_size})
    for f in POLICIES_DIR.glob("*.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            policies.append({"file": f.name, "policy": _redact_dict(p)})
        except (json.JSONDecodeError, OSError):
            policies.append({"file": f.name, "size": f.stat().st_size})
    return policies


def _to_csv(records: list[dict], name: str) -> str:
    """Convert list of dicts to CSV string."""
    if not records:
        return ""
    keys = set()
    for r in records:
        keys.update(r.keys())
    keys = sorted(keys)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    for r in records:
        flat = {}
        for k in keys:
            v = r.get(k, "")
            flat[k] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        writer.writerow(flat)
    return buf.getvalue()


def export_audit(
    output_dir: Path | None = None,
    mission_id: str | None = None,
    user_id: str | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    include_csv: bool = False,
) -> dict:
    """Create an audit export archive.

    Returns dict with export metadata including archive path and checksum.
    """
    from_dt = _parse_ts(from_ts)
    to_dt = _parse_ts(to_ts)

    out = output_dir or DEFAULT_EXPORT_DIR
    out.mkdir(parents=True, exist_ok=True)

    ts_label = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archive_name = f"audit-export-{ts_label}.zip"
    archive_path = out / archive_name

    # Collect data
    missions = _load_missions(mission_id, user_id, from_dt, to_dt)
    dlq_events = _load_dlq(mission_id, from_dt, to_dt)
    audit_entries = _load_audit_log(from_dt, to_dt)
    approvals = _load_approvals(mission_id, from_dt, to_dt)
    policies = _load_policies()

    manifest = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(OC_ROOT),
        "filters": {
            "mission_id": mission_id,
            "user_id": user_id,
            "from": from_ts,
            "to": to_ts,
        },
        "counts": {
            "missions": len(missions),
            "dlq_events": len(dlq_events),
            "audit_entries": len(audit_entries),
            "approvals": len(approvals),
            "policies": len(policies),
        },
        "max_missions": MAX_MISSIONS,
        "redaction_applied": True,
        "files": {},
    }

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Missions
        missions_json = json.dumps(missions, indent=2, ensure_ascii=False)
        zf.writestr("missions.json", missions_json)
        manifest["files"]["missions.json"] = {
            "count": len(missions),
            "sha256": _sha256(missions_json.encode()),
        }

        # DLQ events
        dlq_json = json.dumps(dlq_events, indent=2, ensure_ascii=False)
        zf.writestr("dlq-events.json", dlq_json)
        manifest["files"]["dlq-events.json"] = {
            "count": len(dlq_events),
            "sha256": _sha256(dlq_json.encode()),
        }

        # Audit log
        audit_json = json.dumps(audit_entries, indent=2, ensure_ascii=False)
        zf.writestr("audit-log.json", audit_json)
        manifest["files"]["audit-log.json"] = {
            "count": len(audit_entries),
            "sha256": _sha256(audit_json.encode()),
        }

        # Approvals
        approvals_json = json.dumps(approvals, indent=2, ensure_ascii=False)
        zf.writestr("approvals.json", approvals_json)
        manifest["files"]["approvals.json"] = {
            "count": len(approvals),
            "sha256": _sha256(approvals_json.encode()),
        }

        # Policies
        policies_json = json.dumps(policies, indent=2, ensure_ascii=False)
        zf.writestr("policies.json", policies_json)
        manifest["files"]["policies.json"] = {
            "count": len(policies),
            "sha256": _sha256(policies_json.encode()),
        }

        # CSV summaries
        if include_csv:
            for name, records in [("missions", missions),
                                  ("dlq-events", dlq_events),
                                  ("approvals", approvals)]:
                csv_data = _to_csv(records, name)
                if csv_data:
                    zf.writestr(f"{name}.csv", csv_data)
                    manifest["files"][f"{name}.csv"] = {
                        "count": len(records),
                        "sha256": _sha256(csv_data.encode()),
                    }

        # Manifest (written last)
        manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)
        zf.writestr("manifest.json", manifest_json)

    # Compute archive checksum
    archive_checksum = _sha256(archive_path.read_bytes())

    return {
        "archive": str(archive_path),
        "archive_name": archive_name,
        "checksum": archive_checksum,
        "created_at": manifest["created_at"],
        "counts": manifest["counts"],
        "filters": manifest["filters"],
        "total_records": sum(manifest["counts"].values()),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Audit Export CLI — compliance-ready audit archive (B-115)")
    sub = parser.add_subparsers(dest="command")

    export_cmd = sub.add_parser("export", help="Create audit export archive")
    export_cmd.add_argument("--output", type=str, help="Output directory")
    export_cmd.add_argument("--mission-id", type=str, help="Filter by mission ID")
    export_cmd.add_argument("--user-id", type=str, help="Filter by user ID")
    export_cmd.add_argument("--from", dest="from_ts", type=str,
                            help="From timestamp (ISO format)")
    export_cmd.add_argument("--to", dest="to_ts", type=str,
                            help="To timestamp (ISO format)")
    export_cmd.add_argument("--csv", action="store_true",
                            help="Include CSV summaries")

    args = parser.parse_args()

    if args.command == "export":
        out = Path(args.output) if args.output else None
        result = export_audit(
            output_dir=out,
            mission_id=args.mission_id,
            user_id=args.user_id,
            from_ts=args.from_ts,
            to_ts=args.to_ts,
            include_csv=args.csv,
        )
        print(f"Export created: {result['archive']}")
        print(f"SHA-256: {result['checksum']}")
        print(f"Records: {result['total_records']}")
        for k, v in result["counts"].items():
            print(f"  {k}: {v}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
