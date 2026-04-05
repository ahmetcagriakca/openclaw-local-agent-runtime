#!/usr/bin/env python3
"""Mission Replay CLI Tool — B-146.

Merges three event sources into a chronological unified timeline:
  1. logs/audit-trail.jsonl (or logs/agent-audit.jsonl) — audit events
  2. logs/missions/<mission_id>*-summary.json — stateTransitions
  3. logs/policy-telemetry.jsonl — policy events

Usage:
  python tools/replay-mission.py <mission_id>
  python tools/replay-mission.py <mission_id> --json
  python tools/replay-mission.py <mission_id> --filter state_transition
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime

# Base directories
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(REPO_ROOT, "logs")
MISSIONS_DIR = os.path.join(LOGS_DIR, "missions")


def parse_iso(ts_str: str) -> datetime:
    """Parse ISO 8601 timestamp, tolerating various formats."""
    # Strip trailing Z and replace with +00:00
    ts_str = ts_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts_str)
    except ValueError:
        # Fallback: strip timezone and parse naive
        return datetime.fromisoformat(ts_str[:19])


def load_audit_events(mission_id: str) -> list[dict]:
    """Load audit trail events matching the mission_id (correlation_id or missionId)."""
    events = []

    # Try both audit trail files
    audit_files = [
        os.path.join(LOGS_DIR, "audit-trail.jsonl"),
        os.path.join(LOGS_DIR, "agent-audit.jsonl"),
    ]

    for audit_path in audit_files:
        if not os.path.isfile(audit_path):
            continue
        source_name = os.path.basename(audit_path)
        try:
            with open(audit_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Match by correlation_id, missionId in data, or sessionId
                    corr = entry.get("correlation_id", "")
                    data = entry.get("data", {}) if isinstance(entry.get("data"), dict) else {}
                    mid = data.get("missionId", data.get("mission_id", ""))
                    session_id = entry.get("sessionId", "")

                    if mission_id in (corr, mid, session_id):
                        ts_str = entry.get("ts", entry.get("timestamp", ""))
                        if not ts_str:
                            continue
                        events.append({
                            "timestamp": ts_str,
                            "source": f"audit:{source_name}",
                            "event_type": entry.get("type", entry.get("event", "audit_event")),
                            "detail": _summarize_audit(entry),
                        })
        except OSError:
            continue

    return events


def _summarize_audit(entry: dict) -> str:
    """Build a short detail string from an audit entry."""
    parts = []
    data = entry.get("data", {}) if isinstance(entry.get("data"), dict) else {}

    # Tool call info
    tool_calls = data.get("toolCalls", entry.get("toolCalls", []))
    if tool_calls and isinstance(tool_calls, list):
        tools = [tc.get("tool", "?") for tc in tool_calls if isinstance(tc, dict)]
        if tools:
            parts.append(f"tools=[{','.join(tools)}]")

    # Status
    status = data.get("status", entry.get("status", ""))
    if status:
        parts.append(f"status={status}")

    # Source
    source = entry.get("source", "")
    if source:
        parts.append(f"source={source}")

    # Response preview
    resp = data.get("response", entry.get("response", ""))
    if resp and isinstance(resp, str):
        preview = resp[:80].replace("\n", " ")
        parts.append(f'"{preview}"')

    return " | ".join(parts) if parts else json.dumps(entry.get("data", {}), ensure_ascii=False)[:120]


def load_state_transitions(mission_id: str) -> list[dict]:
    """Load stateTransitions from mission summary JSON files."""
    events = []

    if not os.path.isdir(MISSIONS_DIR):
        return events

    # Find matching mission files (summary or regular)
    patterns = [
        os.path.join(MISSIONS_DIR, f"{mission_id}*-summary.json"),
        os.path.join(MISSIONS_DIR, f"{mission_id}*.json"),
    ]

    matched_files = set()
    for pattern in patterns:
        for path in glob.glob(pattern):
            matched_files.add(path)

    for path in sorted(matched_files):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        transitions = data.get("stateTransitions", [])
        if not isinstance(transitions, list):
            continue

        for t in transitions:
            ts_str = t.get("timestamp", "")
            if not ts_str:
                continue
            events.append({
                "timestamp": ts_str,
                "source": "mission",
                "event_type": "state_transition",
                "detail": f"{t.get('from', '?')} → {t.get('to', '?')} ({t.get('reason', '')})",
            })

        # Also extract stage info
        stages = data.get("stages", [])
        if isinstance(stages, list):
            for stage in stages:
                if not isinstance(stage, dict):
                    continue
                artifacts = stage.get("artifacts", [])
                if isinstance(artifacts, list):
                    for art in artifacts:
                        if isinstance(art, dict) and art.get("ts"):
                            events.append({
                                "timestamp": art["ts"],
                                "source": "mission",
                                "event_type": f"artifact:{art.get('type', 'unknown')}",
                                "detail": f"stage={stage.get('id', '?')} specialist={stage.get('specialist', '?')}",
                            })

    return events


def load_policy_telemetry(mission_id: str) -> list[dict]:
    """Load policy telemetry events matching the mission_id."""
    events = []
    telemetry_path = os.path.join(LOGS_DIR, "policy-telemetry.jsonl")

    if not os.path.isfile(telemetry_path):
        return events

    try:
        with open(telemetry_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Match by mission_id field
                mid = entry.get("mission_id", entry.get("missionId", ""))
                corr = entry.get("correlation_id", "")
                if mission_id not in (mid, corr):
                    continue

                ts_str = entry.get("timestamp", entry.get("ts", ""))
                if not ts_str:
                    continue

                event_type = entry.get("event", entry.get("type", "policy_event"))
                detail_parts = []
                for key in ("loop", "cycle", "max", "bug_count", "tool", "role",
                            "reason", "resolved_path", "budget_type"):
                    if key in entry:
                        detail_parts.append(f"{key}={entry[key]}")
                detail = " | ".join(detail_parts) if detail_parts else json.dumps(entry, ensure_ascii=False)[:120]

                events.append({
                    "timestamp": ts_str,
                    "source": "policy",
                    "event_type": event_type,
                    "detail": detail,
                })
    except OSError:
        pass

    return events


def merge_and_sort(all_events: list[dict]) -> list[dict]:
    """Merge events and sort chronologically."""
    return sorted(all_events, key=lambda e: parse_iso(e["timestamp"]))


def format_table(events: list[dict]) -> str:
    """Format events as a human-readable table."""
    if not events:
        return "No events found."

    # Column widths
    ts_w = 26
    src_w = max(len(e["source"]) for e in events)
    src_w = max(src_w, 6)
    type_w = max(len(e["event_type"]) for e in events)
    type_w = max(type_w, 10)

    header = f"{'TIMESTAMP':<{ts_w}} | {'SOURCE':<{src_w}} | {'EVENT_TYPE':<{type_w}} | DETAIL"
    separator = "-" * len(header)

    lines = [header, separator]
    for e in events:
        ts = e["timestamp"][:26]
        lines.append(f"{ts:<{ts_w}} | {e['source']:<{src_w}} | {e['event_type']:<{type_w}} | {e['detail']}")

    return "\n".join(lines)


def format_jsonl(events: list[dict]) -> str:
    """Format events as JSONL."""
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in events)


def main():
    parser = argparse.ArgumentParser(
        description="Replay mission timeline from audit trail, mission state, and policy telemetry.",
        epilog="Sources: logs/audit-trail.jsonl, logs/missions/<id>*.json, logs/policy-telemetry.jsonl",
    )
    parser.add_argument("mission_id", help="Mission ID to replay (e.g., mission-20260323092309-28852)")
    parser.add_argument("--json", action="store_true", help="Output as JSONL instead of table")
    parser.add_argument("--filter", metavar="EVENT_TYPE", help="Filter by event_type (e.g., state_transition)")

    args = parser.parse_args()
    mission_id = args.mission_id

    # Collect from all sources (graceful degradation — missing sources are skipped)
    all_events = []
    sources_found = []

    audit = load_audit_events(mission_id)
    if audit:
        sources_found.append(f"audit ({len(audit)} events)")
    all_events.extend(audit)

    transitions = load_state_transitions(mission_id)
    if transitions:
        sources_found.append(f"mission ({len(transitions)} events)")
    all_events.extend(transitions)

    policy = load_policy_telemetry(mission_id)
    if policy:
        sources_found.append(f"policy ({len(policy)} events)")
    all_events.extend(policy)

    if not all_events:
        print(f"Error: No events found for mission '{mission_id}'.", file=sys.stderr)
        print(f"Checked:", file=sys.stderr)
        print(f"  - logs/audit-trail.jsonl, logs/agent-audit.jsonl", file=sys.stderr)
        print(f"  - logs/missions/{mission_id}*.json", file=sys.stderr)
        print(f"  - logs/policy-telemetry.jsonl", file=sys.stderr)
        sys.exit(1)

    # Sort chronologically
    sorted_events = merge_and_sort(all_events)

    # Apply filter
    if args.filter:
        sorted_events = [e for e in sorted_events if args.filter in e["event_type"]]
        if not sorted_events:
            print(f"No events matching filter '{args.filter}'.", file=sys.stderr)
            sys.exit(1)

    # Header
    if not args.json:
        print(f"=== Mission Replay: {mission_id} ===")
        print(f"Sources: {', '.join(sources_found)}")
        print(f"Total events: {len(sorted_events)}")
        if args.filter:
            print(f"Filter: {args.filter}")
        print()

    # Output
    if args.json:
        print(format_jsonl(sorted_events))
    else:
        print(format_table(sorted_events))


if __name__ == "__main__":
    main()
