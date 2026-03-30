"""Cost & Outcome Dashboard API — B-105 (Sprint 46).

Endpoints for cost/token tracking, outcome analytics, and ROI visibility.
Reads mission data from file-based mission store (logs/missions/) via normalizer,
falling back to MissionStore if available.
"""
from __future__ import annotations

import glob
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Query

logger = logging.getLogger("mcc.api.cost")

router = APIRouter(prefix="/cost", tags=["cost"])

# Provider pricing (tokens per 1K) — configurable estimates
PROVIDER_PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "claude-sonnet": {"input": 0.003, "output": 0.015},
    "ollama": {"input": 0.0, "output": 0.0},
    "mock": {"input": 0.0, "output": 0.0},
}

DEFAULT_PRICING = {"input": 0.005, "output": 0.015}


def _get_missions_dir() -> Path:
    """Get missions directory path."""
    root = Path(__file__).resolve().parent.parent.parent
    return root / "logs" / "missions"


def _load_file_missions() -> list[dict]:
    """Load missions from file-based storage (logs/missions/).

    Reads mission JSON files and extracts cost-relevant fields.
    Skips state/summary companion files.
    """
    missions_dir = _get_missions_dir()
    items = []
    pattern = str(missions_dir / "mission-*.json")
    for fpath in glob.glob(pattern):
        base = os.path.basename(fpath)
        if "-state.json" in base or "-summary.json" in base or "-token-report" in base:
            continue
        try:
            data = json.loads(Path(fpath).read_text(encoding="utf-8"))
            mid = data.get("missionId", "")
            if not mid:
                continue

            # Get status from state file if available
            status = data.get("status", "unknown")
            state_path = missions_dir / f"{mid}-state.json"
            if state_path.exists():
                try:
                    sd = json.loads(state_path.read_text(encoding="utf-8"))
                    status = sd.get("status", status)
                except Exception:
                    pass

            # Prefer summary file for richer stage data (toolCalls, agentUsed, isRework)
            summary_path = missions_dir / f"{mid}-summary.json"
            summary_stages = []
            if summary_path.exists():
                try:
                    sm = json.loads(summary_path.read_text(encoding="utf-8"))
                    summary_stages = sm.get("stages", [])
                except Exception:
                    pass

            # Use summary stages if available, fallback to mission stages
            stages = data.get("stages", [])
            rich_stages = summary_stages if summary_stages else stages
            stage_count = len(rich_stages) if isinstance(rich_stages, list) else 0
            total_tool_calls = 0
            total_duration_ms = 0
            reworks = 0
            provider = "gpt-4o"  # default

            if isinstance(rich_stages, list):
                for s in rich_stages:
                    if isinstance(s, dict):
                        total_tool_calls += s.get("toolCalls", s.get("tool_call_count", 0)) or 0
                        total_duration_ms += s.get("durationMs", s.get("duration_ms", 0)) or 0
                        if s.get("isRework") or s.get("is_rework"):
                            reworks += 1
                        agent = s.get("agentUsed", s.get("agent_used", ""))
                        if agent:
                            al = agent.lower()
                            if "claude" in al:
                                provider = "claude-sonnet"
                            elif "ollama" in al:
                                provider = "ollama"
                            elif "mock" in al:
                                provider = "mock"

            # Token report
            tokens = 0
            token_path = missions_dir / f"{mid}-token-report.json"
            if token_path.exists():
                try:
                    tr = json.loads(token_path.read_text(encoding="utf-8"))
                    tokens = tr.get("total_tokens", 0)
                except Exception:
                    pass

            # Fallback: estimate tokens from stage count
            if tokens == 0 and stage_count > 0:
                tokens = stage_count * 2000  # rough estimate

            ts = data.get("startedAt", data.get("ts", ""))

            items.append({
                "id": mid,
                "goal": data.get("goal", ""),
                "status": status,
                "complexity": data.get("complexity", ""),
                "tokens": tokens,
                "duration": total_duration_ms,
                "stages": stage_count,
                "tools": total_tool_calls,
                "reworks": reworks,
                "provider": provider,
                "ts": ts,
            })
        except Exception as e:
            logger.debug("cost: skip %s: %s", fpath, e)
    return items


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "mission_files", "ageMs": 0, "status": "fresh"}],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _estimate_cost(tokens: int, provider: str = "gpt-4o") -> float:
    """Estimate cost from token count using provider pricing.

    Assumes 60/40 input/output split as approximation.
    """
    pricing = PROVIDER_PRICING.get(provider, DEFAULT_PRICING)
    input_tokens = int(tokens * 0.6)
    output_tokens = tokens - input_tokens
    cost = (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
    return round(cost, 4)


@router.get("/summary")
async def cost_summary():
    """Aggregate cost/outcome KPIs across all missions."""
    items = _load_file_missions()

    # Filter to terminal states only
    terminal = [m for m in items if m["status"] in ("completed", "failed", "aborted", "timed_out")]
    completed = [m for m in terminal if m["status"] == "completed"]
    failed = [m for m in terminal if m["status"] in ("failed", "aborted", "timed_out")]
    total = len(terminal)

    # Cost estimation per provider
    provider_costs: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "missions": 0, "cost": 0.0})
    for m in terminal:
        provider = m.get("provider", "gpt-4o")
        tokens = m.get("tokens", 0)
        provider_costs[provider]["tokens"] += tokens
        provider_costs[provider]["missions"] += 1
        provider_costs[provider]["cost"] += _estimate_cost(tokens, provider)

    total_tokens = sum(m.get("tokens", 0) for m in terminal)
    total_cost = sum(pc["cost"] for pc in provider_costs.values())
    avg_cost_per_mission = round(total_cost / total, 4) if total > 0 else 0
    success_rate = round(len(completed) / total * 100, 1) if total > 0 else 0

    avg_tokens_completed = (
        round(sum(m.get("tokens", 0) for m in completed) / len(completed))
        if completed else 0
    )
    durations = [m.get("duration", 0) for m in terminal if m.get("duration")]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    return {
        "meta": _meta(),
        "total_missions": total,
        "completed": len(completed),
        "failed": len(failed),
        "success_rate": success_rate,
        "total_tokens": total_tokens,
        "total_estimated_cost": round(total_cost, 4),
        "avg_cost_per_mission": avg_cost_per_mission,
        "avg_tokens_per_completed": avg_tokens_completed,
        "avg_duration_ms": avg_duration,
        "total_tool_calls": sum(m.get("tools", 0) for m in terminal),
        "total_reworks": sum(m.get("reworks", 0) for m in terminal),
        "total_budget_events": 0,
        "provider_breakdown": {
            k: {
                "tokens": v["tokens"],
                "missions": v["missions"],
                "estimated_cost": round(v["cost"], 4),
            }
            for k, v in provider_costs.items()
        },
        "pricing_model": PROVIDER_PRICING,
    }


@router.get("/missions")
async def cost_per_mission(
    limit: int = Query(50, ge=1, le=200),
    offset: int = 0,
    sort: str = "cost_desc",
):
    """Per-mission cost breakdown, sorted by cost or tokens."""
    items = _load_file_missions()
    terminal = [m for m in items if m["status"] in ("completed", "failed", "aborted", "timed_out")]

    enriched = []
    for m in terminal:
        tokens = m.get("tokens", 0)
        provider = m.get("provider", "gpt-4o")
        cost = _estimate_cost(tokens, provider)
        enriched.append({
            "id": m.get("id", ""),
            "goal": m.get("goal", ""),
            "status": m.get("status", ""),
            "complexity": m.get("complexity", ""),
            "tokens": tokens,
            "estimated_cost": cost,
            "provider": provider,
            "duration_ms": m.get("duration", 0),
            "stages": m.get("stages", 0),
            "tool_calls": m.get("tools", 0),
            "reworks": m.get("reworks", 0),
            "budget_pct": 0,
            "ts": m.get("ts", ""),
        })

    # Sort
    if sort == "cost_desc":
        enriched.sort(key=lambda x: x["estimated_cost"], reverse=True)
    elif sort == "tokens_desc":
        enriched.sort(key=lambda x: x["tokens"], reverse=True)
    elif sort == "duration_desc":
        enriched.sort(key=lambda x: x["duration_ms"], reverse=True)
    else:
        enriched.sort(key=lambda x: x["ts"], reverse=True)

    paginated = enriched[offset:offset + limit]

    return {
        "meta": _meta(),
        "total": len(enriched),
        "missions": paginated,
    }


@router.get("/trends")
async def cost_trends(
    bucket: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
):
    """Cost trends aggregated by time bucket."""
    items = _load_file_missions()
    terminal = [m for m in items if m["status"] in ("completed", "failed", "aborted", "timed_out")]

    buckets: dict[str, dict] = defaultdict(
        lambda: {"tokens": 0, "cost": 0.0, "missions": 0, "completed": 0, "failed": 0}
    )

    for m in terminal:
        ts = m.get("ts", "")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        if bucket == "daily":
            key = dt.strftime("%Y-%m-%d")
        elif bucket == "weekly":
            key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
        else:
            key = dt.strftime("%Y-%m")

        tokens = m.get("tokens", 0)
        provider = m.get("provider", "gpt-4o")
        cost = _estimate_cost(tokens, provider)
        buckets[key]["tokens"] += tokens
        buckets[key]["cost"] += cost
        buckets[key]["missions"] += 1
        if m.get("status") == "completed":
            buckets[key]["completed"] += 1
        elif m.get("status") in ("failed", "aborted"):
            buckets[key]["failed"] += 1

    sorted_buckets = sorted(buckets.items())
    trend_data = [
        {
            "period": k,
            "tokens": v["tokens"],
            "estimated_cost": round(v["cost"], 4),
            "missions": v["missions"],
            "completed": v["completed"],
            "failed": v["failed"],
            "success_rate": round(v["completed"] / v["missions"] * 100, 1) if v["missions"] > 0 else 0,
        }
        for k, v in sorted_buckets
    ]

    return {
        "meta": _meta(),
        "bucket": bucket,
        "trends": trend_data,
    }
