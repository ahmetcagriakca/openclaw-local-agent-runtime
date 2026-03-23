#!/usr/bin/env python3
"""OpenClaw Agent Runner — AI-powered Windows automation via MCP tools."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
import argparse
import json
import os
import sys
import time

# Add agent directory to path
agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, agent_dir)

from oc_agent_runner_lib import run_agent_with_config


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Agent Runner")
    parser.add_argument("--message", "-m", required=True, help="User message")
    parser.add_argument("--agent", default="gpt-general", help="Agent ID")
    parser.add_argument("--user-id", default="8654710624", help="User ID")
    parser.add_argument("--session-id", default=None, help="Session ID")
    parser.add_argument("--max-turns", type=int, default=10, help="Max turns")
    parser.add_argument("--mission", action="store_true",
                        help="Run as multi-agent mission (breaks task into stages)")
    args = parser.parse_args()

    # D-057: Startup metadata gate — validate tool catalog governance
    from services.tool_catalog import validate_catalog_governance
    errors = validate_catalog_governance()
    if errors:
        print("FATAL: Tool catalog governance validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("Runtime cannot start. Fix tool catalog metadata.", file=sys.stderr)
        sys.exit(1)

    session_id = args.session_id or f"sess-{int(time.time())}-{os.getpid()}"

    if args.mission:
        from mission.controller import MissionController
        controller = MissionController(planner_agent_id=args.agent)
        result = controller.execute_mission(
            goal=args.message,
            user_id=args.user_id,
            session_id=session_id
        )
        # Format mission result as JSON envelope
        output = {
            "status": result.get("status"),
            "missionId": result.get("missionId"),
            "response": result.get("summary", ""),
            "stages": [
                {
                    "id": s.get("id"),
                    "specialist": s.get("specialist"),
                    "objective": s.get("objective"),
                    "status": s.get("status"),
                    "result_preview": (s.get("result") or "")[:200]
                }
                for s in result.get("stages", [])
            ],
            "totalDurationMs": result.get("totalDurationMs"),
            "artifactCount": len(result.get("artifacts", []))
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        result = run_agent_with_config(
            message=args.message,
            agent_id=args.agent,
            user_id=args.user_id,
            session_id=session_id,
            max_turns=args.max_turns
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result.get("status") == "completed" else 1)


if __name__ == "__main__":
    main()
