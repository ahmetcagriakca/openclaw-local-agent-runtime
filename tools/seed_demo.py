"""B-112 Local Dev Sandbox / Seeded Demo — seed sample data for development.

Creates sample missions, policies, templates, and state files so that
new developers can start with a populated dashboard immediately.

Usage:
    python tools/seed_demo.py seed              # seed all sample data
    python tools/seed_demo.py seed --clean      # wipe + seed fresh
    python tools/seed_demo.py clean             # remove seeded data only
    python tools/seed_demo.py status            # show what's seeded
"""
import argparse
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger("mcc.seed_demo")

OC_ROOT = Path(__file__).resolve().parent.parent
MISSIONS_DIR = OC_ROOT / "logs" / "missions"
POLICIES_DIR = OC_ROOT / "config" / "policies"
TEMPLATES_DIR = OC_ROOT / "config" / "templates"

# Marker to identify seeded data
SEED_MARKER = "__seeded_demo__"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _past_iso(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def _sample_missions() -> list[dict]:
    """Generate sample missions covering various states and complexities."""
    return [
        {
            "missionId": "demo-mission-001",
            "goal": "Analyze system logs and generate summary report",
            "userId": "demo-user",
            "sessionId": "demo-session",
            "status": "completed",
            "complexity": "standard",
            "risk_level": "low",
            SEED_MARKER: True,
            "startedAt": _past_iso(2),
            "finishedAt": _past_iso(1),
            "currentStage": 3,
            "stages": [
                {
                    "id": "stage-1",
                    "specialist": "analyst",
                    "description": "Collect and parse log files",
                    "status": "completed",
                    "result": "Parsed 150 log entries from 3 sources",
                    "tool_call_count": 2,
                },
                {
                    "id": "stage-2",
                    "specialist": "researcher",
                    "description": "Identify patterns and anomalies",
                    "status": "completed",
                    "result": "Found 3 warning patterns and 1 error spike at 14:00 UTC",
                    "tool_call_count": 1,
                },
                {
                    "id": "stage-3",
                    "specialist": "writer",
                    "description": "Generate summary report",
                    "status": "completed",
                    "result": "Report generated: 150 entries, 3 warnings, 1 error spike. Recommended: increase log rotation frequency.",
                    "tool_call_count": 0,
                },
            ],
            "artifacts": [],
            "error": None,
        },
        {
            "missionId": "demo-mission-002",
            "goal": "Deploy updated configuration to staging environment",
            "userId": "demo-user",
            "sessionId": "demo-session",
            "status": "failed",
            "complexity": "complex",
            "risk_level": "high",
            SEED_MARKER: True,
            "startedAt": _past_iso(5),
            "finishedAt": _past_iso(4),
            "currentStage": 2,
            "stages": [
                {
                    "id": "stage-1",
                    "specialist": "planner",
                    "description": "Validate configuration changes",
                    "status": "completed",
                    "result": "Configuration validated: 12 changes, 3 new keys",
                    "tool_call_count": 3,
                },
                {
                    "id": "stage-2",
                    "specialist": "executor",
                    "description": "Apply configuration to staging",
                    "status": "failed",
                    "result": None,
                    "error": "Connection timeout to staging server",
                    "tool_call_count": 1,
                },
            ],
            "artifacts": [],
            "error": "Stage 2 failed: Connection timeout to staging server",
        },
        {
            "missionId": "demo-mission-003",
            "goal": "Run security audit on API endpoints",
            "userId": "demo-user",
            "sessionId": "demo-session",
            "status": "completed",
            "complexity": "standard",
            "risk_level": "medium",
            SEED_MARKER: True,
            "startedAt": _past_iso(8),
            "finishedAt": _past_iso(7),
            "currentStage": 2,
            "stages": [
                {
                    "id": "stage-1",
                    "specialist": "security_analyst",
                    "description": "Scan API endpoints for vulnerabilities",
                    "status": "completed",
                    "result": "Scanned 76 endpoints: 0 critical, 2 medium, 5 low findings",
                    "tool_call_count": 4,
                },
                {
                    "id": "stage-2",
                    "specialist": "writer",
                    "description": "Generate security report",
                    "status": "completed",
                    "result": "Security audit complete. 7 findings total. Top recommendation: add rate limiting to /admin endpoints.",
                    "tool_call_count": 0,
                },
            ],
            "artifacts": [],
            "error": None,
        },
    ]


def seed_missions(missions_dir: Path | None = None) -> int:
    """Create sample mission files. Returns count of files created."""
    missions_dir = missions_dir or MISSIONS_DIR
    missions_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for mission in _sample_missions():
        path = missions_dir / f"{mission['missionId']}.json"
        path.write_text(
            json.dumps(mission, indent=2, ensure_ascii=False),
            encoding="utf-8")
        count += 1
    return count


def seed_policies(policies_dir: Path | None = None) -> int:
    """Create sample policy files if they don't exist. Returns count."""
    policies_dir = policies_dir or POLICIES_DIR
    policies_dir.mkdir(parents=True, exist_ok=True)

    samples = [
        {
            "name": "demo_cost_limit.yaml",
            "content": (
                "# Demo cost limit policy (D-133 schema)\n"
                "name: demo_cost_limit\n"
                "priority: 900\n"
                "description: Demo — deny when budget exceeded\n"
                "condition:\n"
                "  budget_exceeded: true\n"
                "decision: deny\n"
            ),
        },
        {
            "name": "demo_stage_limit.yaml",
            "content": (
                "# Demo stage limit policy (D-133 schema)\n"
                "name: demo_stage_limit\n"
                "priority: 910\n"
                "description: Demo — deny when stage count exceeded\n"
                "condition:\n"
                "  stage_count_exceeded: true\n"
                "decision: deny\n"
            ),
        },
    ]

    count = 0
    for sample in samples:
        path = policies_dir / sample["name"]
        if not path.exists():
            path.write_text(sample["content"], encoding="utf-8")
            count += 1
    return count


def clean_seeded(missions_dir: Path | None = None) -> int:
    """Remove only seeded demo data (identified by marker). Returns count."""
    missions_dir = missions_dir or MISSIONS_DIR
    removed = 0
    if not missions_dir.exists():
        return 0
    for f in missions_dir.glob("demo-mission-*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get(SEED_MARKER):
                f.unlink()
                removed += 1
        except (json.JSONDecodeError, OSError):
            continue
    return removed


def get_seed_status(missions_dir: Path | None = None) -> dict:
    """Check what seeded data exists."""
    missions_dir = missions_dir or MISSIONS_DIR
    seeded_missions = 0
    total_missions = 0
    if missions_dir.exists():
        for f in missions_dir.glob("*.json"):
            if f.name.startswith("demo-mission-"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if data.get(SEED_MARKER):
                        seeded_missions += 1
                except (json.JSONDecodeError, OSError):
                    pass
            total_missions += 1
    return {
        "seeded_missions": seeded_missions,
        "total_missions": total_missions,
        "missions_dir": str(missions_dir),
    }


def seed_all(missions_dir: Path | None = None,
             policies_dir: Path | None = None,
             clean_first: bool = False) -> dict:
    """Seed all sample data. Returns summary."""
    if clean_first:
        cleaned = clean_seeded(missions_dir)
    else:
        cleaned = 0

    missions = seed_missions(missions_dir)
    policies = seed_policies(policies_dir)

    return {
        "cleaned": cleaned,
        "missions_seeded": missions,
        "policies_seeded": policies,
    }


def main():
    parser = argparse.ArgumentParser(
        description="B-112: Local dev sandbox / seeded demo")
    sub = parser.add_subparsers(dest="command")

    seed_p = sub.add_parser("seed", help="Seed sample data")
    seed_p.add_argument("--clean", action="store_true",
                        help="Clean existing seeded data before seeding")

    sub.add_parser("clean", help="Remove seeded demo data")
    sub.add_parser("status", help="Show seed status")

    args = parser.parse_args()

    if args.command == "seed":
        result = seed_all(clean_first=getattr(args, "clean", False))
        print(f"Seeded: {result['missions_seeded']} missions, "
              f"{result['policies_seeded']} policies")
        if result["cleaned"]:
            print(f"Cleaned {result['cleaned']} previous seeded files")

    elif args.command == "clean":
        removed = clean_seeded()
        print(f"Removed {removed} seeded file(s)")

    elif args.command == "status":
        status = get_seed_status()
        print(json.dumps(status, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
