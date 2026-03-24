"""Telemetry analyzer — mission summary + policy event analysis.

Usage:
    python agent/tools/analyze_telemetry.py [--json] [--last N]
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TELEMETRY_PATH = os.path.join(PROJECT_ROOT, "logs", "policy-telemetry.jsonl")
MISSIONS_DIR = os.path.join(PROJECT_ROOT, "logs", "missions")

# Model pricing (per 1M tokens, input)
MODEL_PRICING = {
    "claude-sonnet": 3.00,
    "claude-general": 3.00,
    "gpt-4o": 2.50,
    "gpt-general": 2.50,
    "ollama-general": 0.00,
}


def load_telemetry_events(last_n_hours: int = None) -> list[dict]:
    """Load policy telemetry events from JSONL."""
    events = []
    if not os.path.exists(TELEMETRY_PATH):
        return events

    try:
        with open(TELEMETRY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    if last_n_hours and events:
        cutoff = datetime.utcnow().timestamp() - (last_n_hours * 3600)
        events = [e for e in events if _parse_ts(e.get("timestamp", "")) >= cutoff]

    return events


def load_mission_summaries(last_n: int = None) -> list[dict]:
    """Load mission summary files."""
    summaries = []
    if not os.path.isdir(MISSIONS_DIR):
        return summaries

    pattern = os.path.join(MISSIONS_DIR, "mission-*-summary.json")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

    if last_n:
        files = files[:last_n]

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                summaries.append(json.load(f))
        except Exception:
            continue

    return summaries


def analyze_telemetry(events: list[dict]) -> dict:
    """Analyze policy telemetry events."""
    if not events:
        return {"totalEvents": 0}

    event_counts = Counter(e.get("event", "unknown") for e in events)
    deny_reasons = Counter()
    role_denies = Counter()
    mission_events = defaultdict(list)

    for e in events:
        etype = e.get("event", "")
        if etype in ("policy_denied", "policy_soft_denied"):
            deny_reasons[e.get("reason", "unknown")] += 1
            role_denies[e.get("role", "unknown")] += 1

        mid = e.get("mission_id", "")
        if mid:
            mission_events[mid].append(e)

    return {
        "totalEvents": len(events),
        "eventTypeCounts": dict(event_counts),
        "totalDenies": event_counts.get("policy_denied", 0)
                       + event_counts.get("policy_soft_denied", 0),
        "topDenyReasons": [{"reason": r, "count": c}
                           for r, c in deny_reasons.most_common(10)],
        "denyByRole": dict(role_denies),
        "missionsWithEvents": len(mission_events),
    }


def analyze_missions(summaries: list[dict]) -> dict:
    """Analyze mission summaries."""
    if not summaries:
        return {"missionCount": 0}

    completed = [s for s in summaries if s.get("status") == "completed"]
    failed = [s for s in summaries if s.get("status") == "failed"]

    # Duration stats
    durations = [s.get("totalDurationMs", 0) for s in completed if s.get("totalDurationMs")]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Stage counts
    stage_counts = [len(s.get("stages", [])) for s in summaries]
    avg_stages = sum(stage_counts) / len(stage_counts) if stage_counts else 0

    # Rework cycles
    total_reworks = 0
    for s in summaries:
        for stage in s.get("stages", []):
            total_reworks += stage.get("reworkCycle", 0)

    # Gate pass rates
    gate_results = {"gate_1": {"checked": 0, "passed": 0},
                    "gate_2": {"checked": 0, "passed": 0},
                    "gate_3": {"checked": 0, "passed": 0}}
    for s in summaries:
        gates = s.get("gatesChecked", {})
        for gate_name in gate_results:
            if gates.get(gate_name):
                gate_results[gate_name]["checked"] += 1
                # If mission completed, gate passed
                if s.get("status") == "completed":
                    gate_results[gate_name]["passed"] += 1

    gate_pass_rates = {}
    for gate_name, stats in gate_results.items():
        if stats["checked"] > 0:
            rate = stats["passed"] / stats["checked"] * 100
            gate_pass_rates[gate_name] = f"{rate:.0f}%"
        else:
            gate_pass_rates[gate_name] = "N/A"

    # Model usage from stages
    model_usage = defaultdict(lambda: {"count": 0, "roles": set()})
    for s in summaries:
        for stage in s.get("stages", []):
            agent = stage.get("agent", "unknown")
            role = stage.get("role", stage.get("specialist", "unknown"))
            model_usage[agent]["count"] += 1
            model_usage[agent]["roles"].add(role)

    model_usage_report = {
        agent: {"count": data["count"], "roles": sorted(data["roles"])}
        for agent, data in model_usage.items()
    }

    # Context tier distribution
    tier_dist = Counter()
    for s in summaries:
        by_tier = s.get("consumptionByTier", {})
        for tier, count in by_tier.items():
            tier_dist[tier] += count

    # Policy denies
    total_policy_denies = sum(s.get("totalPolicyDenies", 0) for s in summaries)

    # Total rereads
    total_rereads = sum(s.get("totalRereads", 0) for s in summaries)

    # Artifact extraction rate (estimate from stages with structured fields)
    extraction_stats = defaultdict(lambda: {"total": 0, "extracted": 0})
    for s in summaries:
        for stage in s.get("stages", []):
            artifact_type = stage.get("artifactType", "stage_output")
            if artifact_type != "stage_output":
                extraction_stats[artifact_type]["total"] += 1
                # If stage completed successfully, extraction likely worked
                if stage.get("status") == "completed":
                    extraction_stats[artifact_type]["extracted"] += 1

    extraction_rates = {}
    for atype, stats in extraction_stats.items():
        if stats["total"] > 0:
            rate = stats["extracted"] / stats["total"] * 100
            extraction_rates[atype] = f"{rate:.0f}%"

    # Cost estimate
    cost_by_complexity = defaultdict(float)
    for s in summaries:
        complexity = s.get("complexity", "unknown")
        total_tokens = 0
        for stage in s.get("stages", []):
            tokens = stage.get("sizeTokens", 0)
            if not tokens:
                # Estimate: ~1000 tokens per stage
                tokens = 1000
            total_tokens += tokens

        # Weighted average pricing
        avg_price = 2.75  # midpoint between Claude and GPT-4o
        cost = (total_tokens / 1_000_000) * avg_price
        cost_by_complexity[complexity] += cost

    cost_report = {k: f"${v:.4f}" for k, v in cost_by_complexity.items()}

    return {
        "missionCount": len(summaries),
        "completed": len(completed),
        "failed": len(failed),
        "avgDurationMs": int(avg_duration),
        "avgStageCount": round(avg_stages, 1),
        "totalReworks": total_reworks,
        "totalPolicyDenies": total_policy_denies,
        "totalRereads": total_rereads,
        "gatePassRates": gate_pass_rates,
        "modelUsage": model_usage_report,
        "contextTierDistribution": dict(tier_dist),
        "artifactExtractionRate": extraction_rates,
        "costEstimate": cost_report,
    }


def generate_report(telemetry: dict, missions: dict, as_json: bool = False) -> str:
    """Generate human-readable or JSON report."""
    combined = {
        "generatedAt": datetime.utcnow().isoformat(),
        "telemetry": telemetry,
        "missions": missions,
    }

    if as_json:
        return json.dumps(combined, indent=2, ensure_ascii=False, default=str)

    lines = []
    lines.append("=" * 60)
    lines.append("  OpenClaw Telemetry Report")
    lines.append(f"  Generated: {combined['generatedAt']}")
    lines.append("=" * 60)

    # Mission stats
    m = missions
    lines.append("")
    lines.append(f"  Missions: {m.get('missionCount', 0)} total "
                 f"({m.get('completed', 0)} completed, {m.get('failed', 0)} failed)")
    if m.get("avgDurationMs"):
        lines.append(f"  Avg Duration: {m['avgDurationMs']}ms "
                     f"({m['avgDurationMs'] / 1000:.1f}s)")
    lines.append(f"  Avg Stages: {m.get('avgStageCount', 0)}")
    lines.append(f"  Total Reworks: {m.get('totalReworks', 0)}")
    lines.append(f"  Total Policy Denies: {m.get('totalPolicyDenies', 0)}")
    lines.append(f"  Total Rereads: {m.get('totalRereads', 0)}")

    # Gate pass rates
    gpr = m.get("gatePassRates", {})
    if gpr:
        lines.append("")
        lines.append("  Gate Pass Rates:")
        for gate, rate in gpr.items():
            lines.append(f"    {gate}: {rate}")

    # Model usage
    mu = m.get("modelUsage", {})
    if mu:
        lines.append("")
        lines.append("  Model Usage:")
        for model, data in mu.items():
            lines.append(f"    {model}: {data['count']} calls "
                         f"(roles: {', '.join(data['roles'])})")

    # Context tiers
    ct = m.get("contextTierDistribution", {})
    if ct:
        lines.append("")
        lines.append("  Context Tier Distribution:")
        for tier in sorted(ct.keys()):
            lines.append(f"    Tier {tier}: {ct[tier]}")

    # Extraction rates
    er = m.get("artifactExtractionRate", {})
    if er:
        lines.append("")
        lines.append("  Artifact Extraction Rates:")
        for atype, rate in er.items():
            lines.append(f"    {atype}: {rate}")

    # Cost
    ce = m.get("costEstimate", {})
    if ce:
        lines.append("")
        lines.append("  Cost Estimates:")
        for complexity, cost in ce.items():
            lines.append(f"    {complexity}: {cost}")

    # Telemetry events
    t = telemetry
    lines.append("")
    lines.append(f"  Policy Events: {t.get('totalEvents', 0)} total, "
                 f"{t.get('totalDenies', 0)} denies")

    deny_reasons = t.get("topDenyReasons", [])
    if deny_reasons:
        lines.append("  Top Deny Reasons:")
        for dr in deny_reasons[:5]:
            lines.append(f"    {dr['reason']}: {dr['count']}")

    deny_by_role = t.get("denyByRole", {})
    if deny_by_role:
        lines.append("  Denies by Role:")
        for role, count in sorted(deny_by_role.items(), key=lambda x: -x[1]):
            lines.append(f"    {role}: {count}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def _parse_ts(ts_str: str) -> float:
    """Parse ISO timestamp to unix time."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Telemetry Analyzer")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--last", type=int, default=None,
                        help="Only analyze last N missions")
    parser.add_argument("--hours", type=int, default=None,
                        help="Only analyze telemetry from last N hours")
    args = parser.parse_args()

    events = load_telemetry_events(last_n_hours=args.hours)
    summaries = load_mission_summaries(last_n=args.last)

    telemetry_analysis = analyze_telemetry(events)
    mission_analysis = analyze_missions(summaries)

    report = generate_report(telemetry_analysis, mission_analysis, as_json=args.json)
    print(report)


if __name__ == "__main__":
    main()
