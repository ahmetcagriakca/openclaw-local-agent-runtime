"""Cost & Outcome Dashboard API — B-105 (Sprint 46).

Endpoints for cost/token tracking, outcome analytics, and ROI visibility.
Aggregates data from MissionStore for cost summary, per-mission breakdown,
and trend analysis.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

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

_mission_store = None


def _get_store():
    global _mission_store
    if _mission_store is None:
        from persistence.mission_store import MissionStore
        _mission_store = MissionStore()
    return _mission_store


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "mission_store", "ageMs": 0, "status": "fresh"}],
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
    store = _get_store()
    summary = store.summary()
    items = store.list(limit=10000)[0]

    total_tokens = summary.get("total_tokens", 0)
    completed = summary.get("completed", 0)
    failed = summary.get("failed", 0)
    total = summary.get("total_missions", 0)

    # Cost estimation per provider
    provider_costs: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "missions": 0, "cost": 0.0})
    for m in items:
        # Try to detect provider from stages_detail
        provider = "gpt-4o"  # default
        stages_detail = m.get("stages_detail", [])
        if stages_detail:
            for sd in stages_detail:
                if sd.get("agentUsed"):
                    agent = sd["agentUsed"].lower()
                    if "claude" in agent:
                        provider = "claude-sonnet"
                    elif "ollama" in agent:
                        provider = "ollama"
                    break
        tokens = m.get("tokens", 0)
        provider_costs[provider]["tokens"] += tokens
        provider_costs[provider]["missions"] += 1
        provider_costs[provider]["cost"] += _estimate_cost(tokens, provider)

    total_cost = sum(pc["cost"] for pc in provider_costs.values())
    avg_cost_per_mission = round(total_cost / total, 4) if total > 0 else 0

    # Success rate
    success_rate = round(completed / total * 100, 1) if total > 0 else 0

    # Avg tokens per completed mission
    completed_items = [m for m in items if m.get("status") == "completed"]
    avg_tokens_completed = (
        round(sum(m.get("tokens", 0) for m in completed_items) / len(completed_items))
        if completed_items else 0
    )

    return {
        "meta": _meta(),
        "total_missions": total,
        "completed": completed,
        "failed": failed,
        "success_rate": success_rate,
        "total_tokens": total_tokens,
        "total_estimated_cost": round(total_cost, 4),
        "avg_cost_per_mission": avg_cost_per_mission,
        "avg_tokens_per_completed": avg_tokens_completed,
        "avg_duration_ms": summary.get("avg_duration", 0),
        "total_tool_calls": summary.get("total_tool_calls", 0),
        "total_reworks": sum(m.get("reworks", 0) for m in items),
        "total_budget_events": summary.get("total_budget_events", 0),
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
    store = _get_store()
    items, total = store.list(limit=10000)

    enriched = []
    for m in items:
        tokens = m.get("tokens", 0)
        provider = "gpt-4o"
        stages_detail = m.get("stages_detail", [])
        if stages_detail:
            for sd in stages_detail:
                if sd.get("agentUsed"):
                    agent = sd["agentUsed"].lower()
                    if "claude" in agent:
                        provider = "claude-sonnet"
                    elif "ollama" in agent:
                        provider = "ollama"
                    break
        cost = _estimate_cost(tokens, provider)
        duration = m.get("duration", 0)
        enriched.append({
            "id": m.get("id", ""),
            "goal": m.get("goal", ""),
            "status": m.get("status", ""),
            "complexity": m.get("complexity", ""),
            "tokens": tokens,
            "estimated_cost": cost,
            "provider": provider,
            "duration_ms": duration,
            "stages": m.get("stages", 0),
            "tool_calls": m.get("tools", 0),
            "reworks": m.get("reworks", 0),
            "budget_pct": m.get("budget_pct", 0),
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
    store = _get_store()
    items, _ = store.list(limit=10000)

    buckets: dict[str, dict] = defaultdict(
        lambda: {"tokens": 0, "cost": 0.0, "missions": 0, "completed": 0, "failed": 0}
    )

    for m in items:
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
        cost = _estimate_cost(tokens)
        buckets[key]["tokens"] += tokens
        buckets[key]["cost"] += cost
        buckets[key]["missions"] += 1
        if m.get("status") == "completed":
            buckets[key]["completed"] += 1
        elif m.get("status") in ("failed", "aborted"):
            buckets[key]["failed"] += 1

    # Sort by key (chronological)
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
