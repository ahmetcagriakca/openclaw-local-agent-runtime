"""B-111 Mission Replay / Fixture Runner — replay completed missions for testing.

Loads a completed mission from disk and replays its stage execution
without making real LLM calls. Useful for:
- Debugging mission flow
- Generating test fixtures from real missions
- Validating stage boundary isolation (D-102 L1)
- Performance profiling of non-LLM code paths

Usage:
    python tools/replay.py list                          # list completed missions
    python tools/replay.py replay <mission-id>           # dry-run replay
    python tools/replay.py fixture <mission-id>          # generate test fixture
    python tools/replay.py fixture <mission-id> -o out.json
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("mcc.replay")

OC_ROOT = Path(__file__).resolve().parent.parent
MISSIONS_DIR = OC_ROOT / "logs" / "missions"
FIXTURES_DIR = OC_ROOT / "agent" / "tests" / "fixtures"

# Auxiliary file suffixes to skip
_AUX_SUFFIXES = ("-state.json", "-summary.json", "-token-report.json")


def list_completed_missions(missions_dir: Path | None = None,
                            limit: int = 20) -> list[dict]:
    """List completed missions with basic metadata.

    Returns list of dicts with missionId, goal, status, stageCount, completedAt.
    """
    missions_dir = missions_dir or MISSIONS_DIR
    if not missions_dir.exists():
        return []

    missions = []
    for f in sorted(missions_dir.glob("mission-*.json"), reverse=True):
        if any(f.name.endswith(s) for s in _AUX_SUFFIXES):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            status = data.get("status", "")
            if status in ("completed", "failed"):
                missions.append({
                    "missionId": data.get("missionId", ""),
                    "goal": data.get("goal", "")[:80],
                    "status": status,
                    "stageCount": len(data.get("stages", [])),
                    "completedAt": data.get("finishedAt", ""),
                    "complexity": data.get("complexity", ""),
                })
        except (json.JSONDecodeError, OSError):
            continue
        if len(missions) >= limit:
            break

    return missions


def load_mission(mission_id: str,
                 missions_dir: Path | None = None) -> dict | None:
    """Load a mission by ID from disk."""
    missions_dir = missions_dir or MISSIONS_DIR
    # Try direct path first
    path = missions_dir / f"{mission_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    # Search by missionId field
    for f in missions_dir.glob("mission-*.json"):
        if any(f.name.endswith(s) for s in _AUX_SUFFIXES):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("missionId") == mission_id:
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None


def replay_mission(mission_data: dict) -> dict:
    """Dry-run replay of a mission — walk through stages without LLM calls.

    Returns a replay report with per-stage timings and validation results.
    """
    mission_id = mission_data.get("missionId", "unknown")
    stages = mission_data.get("stages", [])
    goal = mission_data.get("goal", "")

    report = {
        "missionId": mission_id,
        "goal": goal,
        "replayedAt": datetime.now(timezone.utc).isoformat(),
        "originalStatus": mission_data.get("status", ""),
        "stageCount": len(stages),
        "stages": [],
        "issues": [],
    }

    for i, stage in enumerate(stages):
        stage_id = stage.get("id", f"stage-{i+1}")
        specialist = stage.get("specialist", "unknown")
        status = stage.get("status", "unknown")
        result_text = stage.get("result", "")
        tool_count = stage.get("tool_call_count", 0)

        stage_report = {
            "index": i,
            "id": stage_id,
            "specialist": specialist,
            "status": status,
            "hasResult": bool(result_text),
            "resultLength": len(str(result_text)) if result_text else 0,
            "toolCallCount": tool_count,
            "tokenReport": stage.get("token_report", {}),
        }

        # Validate stage data
        if status == "completed" and not result_text:
            report["issues"].append({
                "stage": stage_id,
                "issue": "completed_without_result",
                "detail": "Stage marked completed but has no result text",
            })

        if not specialist:
            report["issues"].append({
                "stage": stage_id,
                "issue": "missing_specialist",
                "detail": "No specialist assigned to stage",
            })

        report["stages"].append(stage_report)

    report["valid"] = len(report["issues"]) == 0
    return report


def generate_fixture(mission_data: dict, output_path: Path | None = None) -> dict:
    """Generate a test fixture from a completed mission.

    Strips sensitive data (userId, sessionId) and normalizes timestamps.
    Returns fixture dict suitable for use in tests.
    """
    fixture = {
        "_fixture": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "source": mission_data.get("missionId", "unknown"),
            "description": f"Fixture from: {mission_data.get('goal', '')[:60]}",
        },
        "missionId": f"fixture-{mission_data.get('missionId', 'unknown')}",
        "goal": mission_data.get("goal", ""),
        "status": mission_data.get("status", ""),
        "complexity": mission_data.get("complexity", "standard"),
        "risk_level": mission_data.get("risk_level", "medium"),
        "stages": [],
    }

    for stage in mission_data.get("stages", []):
        fixture_stage = {
            "id": stage.get("id", ""),
            "specialist": stage.get("specialist", ""),
            "description": stage.get("description", ""),
            "status": stage.get("status", ""),
            "result": stage.get("result", ""),
            "tool_call_count": stage.get("tool_call_count", 0),
        }
        fixture["stages"].append(fixture_stage)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(fixture, indent=2, ensure_ascii=False),
            encoding="utf-8")

    return fixture


def main():
    parser = argparse.ArgumentParser(
        description="B-111: Mission replay / fixture runner")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List completed missions")

    replay_p = sub.add_parser("replay", help="Dry-run replay a mission")
    replay_p.add_argument("mission_id", help="Mission ID to replay")

    fix_p = sub.add_parser("fixture", help="Generate test fixture from mission")
    fix_p.add_argument("mission_id", help="Mission ID")
    fix_p.add_argument("-o", "--output", help="Output file path",
                       default=None)

    args = parser.parse_args()

    if args.command == "list":
        missions = list_completed_missions()
        if not missions:
            print("No completed missions found.")
        else:
            print(f"Found {len(missions)} mission(s):\n")
            for m in missions:
                print(f"  {m['missionId']}: {m['goal']} "
                      f"[{m['status']}, {m['stageCount']} stages]")

    elif args.command == "replay":
        data = load_mission(args.mission_id)
        if not data:
            print(f"Mission not found: {args.mission_id}")
            sys.exit(1)
        report = replay_mission(data)
        print(json.dumps(report, indent=2))

    elif args.command == "fixture":
        data = load_mission(args.mission_id)
        if not data:
            print(f"Mission not found: {args.mission_id}")
            sys.exit(1)
        out = Path(args.output) if args.output else None
        fixture = generate_fixture(data, out)
        if out:
            print(f"Fixture written to {out}")
        else:
            print(json.dumps(fixture, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
