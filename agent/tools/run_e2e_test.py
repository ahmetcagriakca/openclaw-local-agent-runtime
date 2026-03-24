"""E2E test runner — run missions with controlled test messages and collect metrics.

Usage:
    python agent/tools/run_e2e_test.py --complexity trivial --message "update description"
    python agent/tools/run_e2e_test.py --all
    python agent/tools/run_e2e_test.py --list
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AGENT_DIR = os.path.join(PROJECT_ROOT, "agent")
MISSIONS_DIR = os.path.join(PROJECT_ROOT, "logs", "missions")
TELEMETRY_PATH = os.path.join(PROJECT_ROOT, "logs", "policy-telemetry.jsonl")

# Predefined test cases per complexity level
TEST_CASES = {
    "trivial": {
        "id": "T-OT-1",
        "message": "tool_catalog.py'deki get_system_info description'ini guncelle: "
                   "'Returns CPU, RAM, disk, and uptime information'",
        "expected_roles": 3,
        "expected_max_stages": 5,
        "budget": "$0.10",
    },
    "simple": {
        "id": "T-OT-2",
        "message": "risk_engine.py'ye yeni blocked pattern ekle: Remove-MpPreference",
        "expected_roles": 4,
        "expected_max_stages": 6,
        "budget": "$0.50",
    },
    "medium": {
        "id": "T-OT-3",
        "message": "Yeni bir MCP tool ekle: get_disk_details - "
                   "disk partition bilgilerini getiren tool",
        "expected_roles": 7,
        "expected_max_stages": 10,
        "budget": "$2.00",
    },
    "complex": {
        "id": "T-OT-4",
        "message": "Approval service'e Slack entegrasyonu mimari tasarimi yap",
        "expected_roles": 8,
        "expected_max_stages": 12,
        "budget": "$5.00",
    },
}


def check_prerequisites() -> list[str]:
    """Check that required services and env vars are available."""
    issues = []

    # Check API keys
    if not os.environ.get("OPENAI_API_KEY"):
        issues.append("OPENAI_API_KEY not set")

    # Check MCP server
    try:
        import requests
        resp = requests.get("http://localhost:8001/openapi.json", timeout=5)
        if resp.status_code != 200:
            issues.append(f"MCP server returned {resp.status_code}")
    except Exception as e:
        issues.append(f"MCP server not reachable: {e}")

    return issues


def get_telemetry_line_count() -> int:
    """Get current line count of telemetry file."""
    if not os.path.exists(TELEMETRY_PATH):
        return 0
    try:
        with open(TELEMETRY_PATH, "r") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def find_latest_mission_summary(after_time: float) -> dict | None:
    """Find the most recent mission summary created after the given time."""
    if not os.path.isdir(MISSIONS_DIR):
        return None

    import glob
    pattern = os.path.join(MISSIONS_DIR, "mission-*-summary.json")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

    for path in files:
        if os.path.getmtime(path) >= after_time:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue

    return None


def run_mission(message: str, agent: str = "gpt-general",
                max_turns: int = 15) -> dict:
    """Run a mission and return results."""
    runner_path = os.path.join(AGENT_DIR, "oc-agent-runner.py")

    # Record pre-test state
    before_telemetry_lines = get_telemetry_line_count()
    start_time = time.time()

    # Run the mission
    cmd = [
        sys.executable, runner_path,
        "--mission",
        "-m", message,
        "--agent", agent,
    ]

    print(f"  Running: {' '.join(cmd[:6])}...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=300, cwd=PROJECT_ROOT
        )
        duration = time.time() - start_time
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        exit_code = -1
        stdout = ""
        stderr = "TIMEOUT after 300 seconds"

    # Collect post-test metrics
    after_telemetry_lines = get_telemetry_line_count()
    new_events = after_telemetry_lines - before_telemetry_lines

    # Find mission summary
    summary = find_latest_mission_summary(start_time)

    # Parse agent runner JSON output
    agent_result = None
    try:
        agent_result = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "exitCode": exit_code,
        "durationMs": int(duration * 1000),
        "durationSec": round(duration, 1),
        "newTelemetryEvents": new_events,
        "missionSummary": summary,
        "agentResult": agent_result,
        "stderr": stderr[:500] if stderr else None,
    }


def run_test_case(complexity: str, custom_message: str = None,
                  agent: str = "gpt-general") -> dict:
    """Run a predefined test case."""
    if complexity not in TEST_CASES:
        print(f"  ERROR: Unknown complexity '{complexity}'")
        return {"error": f"Unknown complexity: {complexity}"}

    tc = TEST_CASES[complexity]
    message = custom_message or tc["message"]

    print(f"\n{'=' * 60}")
    print(f"  Test: {tc['id']} ({complexity})")
    print(f"  Expected roles: {tc['expected_roles']}")
    print(f"  Budget: {tc['budget']}")
    print(f"  Message: {message[:80]}...")
    print(f"{'=' * 60}")

    result = run_mission(message, agent=agent)

    # Analyze results
    summary = result.get("missionSummary")
    status = "UNKNOWN"
    stage_count = 0
    reworks = 0

    if summary:
        status = summary.get("status", "unknown").upper()
        stages = summary.get("stages", [])
        stage_count = len(stages)
        reworks = sum(s.get("reworkCycle", 0) for s in stages)

    print(f"\n  Results:")
    print(f"    Status: {status}")
    print(f"    Duration: {result['durationSec']}s")
    print(f"    Stages: {stage_count} (max expected: {tc['expected_max_stages']})")
    print(f"    Reworks: {reworks}")
    print(f"    New telemetry events: {result['newTelemetryEvents']}")
    print(f"    Exit code: {result['exitCode']}")

    if result.get("stderr"):
        print(f"    Stderr: {result['stderr'][:200]}")

    return {
        "testId": tc["id"],
        "complexity": complexity,
        "status": status,
        **result,
        "stageCount": stage_count,
        "reworks": reworks,
    }


def run_all_tests(agent: str = "gpt-general") -> list[dict]:
    """Run all predefined test cases."""
    results = []
    for complexity in ["trivial", "simple", "medium", "complex"]:
        result = run_test_case(complexity, agent=agent)
        results.append(result)
        # Brief pause between tests
        time.sleep(2)

    # Print comparison table
    print(f"\n{'=' * 60}")
    print("  E2E Test Results Summary")
    print(f"{'=' * 60}")
    print(f"  {'Test':<10} {'Status':<12} {'Duration':<10} {'Stages':<8} {'Reworks':<8}")
    print(f"  {'-' * 48}")
    for r in results:
        print(f"  {r.get('testId', '?'):<10} "
              f"{r.get('status', '?'):<12} "
              f"{r.get('durationSec', '?')}s{'':<5} "
              f"{r.get('stageCount', '?'):<8} "
              f"{r.get('reworks', '?'):<8}")

    return results


def list_test_cases():
    """Print available test cases."""
    print("\nAvailable E2E Test Cases:")
    print(f"  {'ID':<10} {'Complexity':<10} {'Roles':<6} {'Budget':<8} Message")
    print(f"  {'-' * 70}")
    for complexity, tc in TEST_CASES.items():
        print(f"  {tc['id']:<10} {complexity:<10} {tc['expected_roles']:<6} "
              f"{tc['budget']:<8} {tc['message'][:40]}...")


def main():
    parser = argparse.ArgumentParser(description="OpenClaw E2E Test Runner")
    parser.add_argument("--complexity", choices=TEST_CASES.keys(),
                        help="Run specific complexity level")
    parser.add_argument("--message", type=str, help="Custom mission message")
    parser.add_argument("--agent", type=str, default="gpt-general",
                        help="Agent to use (default: gpt-general)")
    parser.add_argument("--all", action="store_true",
                        help="Run all test cases")
    parser.add_argument("--list", action="store_true",
                        help="List available test cases")
    parser.add_argument("--check", action="store_true",
                        help="Check prerequisites only")
    args = parser.parse_args()

    if args.list:
        list_test_cases()
        return

    if args.check:
        issues = check_prerequisites()
        if issues:
            print("Prerequisites NOT met:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print("All prerequisites met.")
            return

    # Check prerequisites
    issues = check_prerequisites()
    if issues:
        print("WARNING: Some prerequisites not met:")
        for issue in issues:
            print(f"  - {issue}")
        print("Continuing anyway...\n")

    if args.all:
        results = run_all_tests(agent=args.agent)
        # Save results
        results_path = os.path.join(
            PROJECT_ROOT, "logs",
            f"e2e-results-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json")
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n  Results saved to: {results_path}")
    elif args.complexity:
        run_test_case(args.complexity, custom_message=args.message,
                      agent=args.agent)
    elif args.message:
        result = run_mission(args.message, agent=args.agent)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
