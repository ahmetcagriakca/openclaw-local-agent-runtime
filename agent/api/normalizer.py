"""MissionNormalizer — D-065: Multiple sources → single normalized response.

Precedence (BF-4):
  - Status: state > mission
  - Forensics: summary > telemetry
  - Timing: mission > state

Freshness (BF-1): freshnessMs = max(source.ageMs) — oldest source determines.
Data quality (GPT Fix 2): 6 states, priority: degraded > stale > partial > fresh.
"""
import glob
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from api.cache import IncrementalFileCache, CacheStatus
from api.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from api.schemas import (
    DataQuality, SourceInfo, ResponseMeta,
    MissionSummary, MissionListItem, StageDetail,
    GateResultDetail, Finding,
    TelemetryEntry, ApprovalEntry,
)


# BF-1: Stale thresholds per response type (ms)
STALE_THRESHOLDS = {
    "mission_detail": 10_000,
    "mission_list": 30_000,
    "health": 60_000,
    "telemetry": 30_000,
    "approval": 30_000,
}

# Per-source stale thresholds (used for source-level status)
_SOURCE_STALE = {
    "state": 10_000,
    "mission": 10_000,
    "summary": 30_000,
    "telemetry": 30_000,
    "capabilities": 60_000,
    "approvals": 30_000,
}


class MissionNormalizer:
    """Aggregation layer — reads sources, returns normalized API responses."""

    def __init__(self, missions_dir: str | Path, telemetry_path: str | Path,
                 capabilities_path: str | Path, approvals_dir: str | Path):
        self._missions_dir = Path(missions_dir)
        self._telemetry_path = Path(telemetry_path)
        self._capabilities_path = Path(capabilities_path)
        self._approvals_dir = Path(approvals_dir)
        self._cache = IncrementalFileCache()
        self._cb = CircuitBreaker(failure_threshold=3, recovery_timeout_s=30)

    # ── Mission List ─────────────────────────────────────────────

    def list_missions(self) -> tuple[list[MissionListItem], ResponseMeta]:
        """List all missions with meta."""
        items = []
        sources_used = []
        sources_missing = []

        pattern = str(self._missions_dir / "mission-*.json")
        found_any = False
        for fpath in sorted(glob.glob(pattern)):
            base = os.path.basename(fpath)
            if "-state.json" in base or "-summary.json" in base:
                continue
            found_any = True
            try:
                data, _ = self._read_source("mission", fpath)
                if data is None:
                    continue
                stages = data.get("stages", [])
                items.append(MissionListItem(
                    missionId=data.get("missionId", ""),
                    state=data.get("status", "unknown"),
                    goal=data.get("goal"),
                    startedAt=data.get("startedAt"),
                    stageCount=len(stages),
                    currentStage=data.get("currentStage", 0),
                    stageSummary=f"{len(stages)} stages",
                ))
            except Exception:
                continue

        if not found_any:
            sources_missing.append("missions")

        dq = self._compute_quality(sources_used, sources_missing)
        meta = ResponseMeta(
            freshnessMs=0,
            dataQuality=dq,
            sourcesUsed=sources_used,
            sourcesMissing=sources_missing,
        )
        return items, meta

    # ── Mission Detail ───────────────────────────────────────────

    def get_mission(self, mission_id: str) -> Optional[
            tuple[MissionSummary, ResponseMeta]]:
        """Get normalized mission detail with meta."""
        sources_used = []
        sources_missing = []
        max_age = 0

        # Source 1: Mission file
        mission_path = self._missions_dir / f"{mission_id}.json"
        mission_data, mission_age = self._read_tracked(
            "mission", mission_path, sources_used, sources_missing)
        if mission_data is None:
            return None
        max_age = max(max_age, mission_age)

        # Source 2: State file (BF-4: state > mission for status)
        state_path = self._missions_dir / f"{mission_id}-state.json"
        state_data, state_age = self._read_tracked(
            "state", state_path, sources_used, sources_missing)
        if state_age > 0:
            max_age = max(max_age, state_age)

        # Source 3: Summary (BF-4: summary > telemetry for forensics)
        summary_path = self._missions_dir / f"{mission_id}-summary.json"
        summary_data, summary_age = self._read_tracked(
            "summary", summary_path, sources_used, sources_missing)
        if summary_age > 0:
            max_age = max(max_age, summary_age)

        # BF-4 precedence: status
        status = mission_data.get("status", "unknown")
        if state_data:
            state_status = state_data.get("status", "")
            if state_status:
                status = state_status

        # Stages: summary preferred, fallback to mission
        stages = self._build_stages(summary_data, mission_data)

        # Deny forensics: summary (BF-4)
        deny_forensics = []
        if summary_data and summary_data.get("denyForensics"):
            deny_forensics = summary_data["denyForensics"]

        # Build response
        dq = self._compute_quality(sources_used, sources_missing)
        # State transitions from state file or summary
        transitions = []
        if state_data and state_data.get("transitionLog"):
            transitions = state_data["transitionLog"]
        elif summary_data and summary_data.get("stateTransitions"):
            transitions = summary_data["stateTransitions"]

        # Error: mission-level error message
        error_msg = mission_data.get("error")
        if not error_msg and summary_data:
            error_msg = summary_data.get("error")
        # Fallback: extract error from last state transition reason
        if not error_msg and transitions:
            last = transitions[-1]
            if last.get("to") in ("failed", "aborted"):
                error_msg = last.get("reason")

        # Propagate error to failed stages from transitions or mission error
        for s in stages:
            if s.status == "failed" and not s.error:
                # Try mission-level error
                if error_msg:
                    s.error = error_msg
                # Try matching transition
                for t in transitions:
                    if t.get("to") in ("failed",) and s.role and s.role in t.get("reason", ""):
                        s.error = t.get("reason")
                        break

        mission = MissionSummary(
            missionId=mission_data.get("missionId", mission_id),
            state=status,
            goal=mission_data.get("goal"),
            complexity=mission_data.get("complexity"),
            error=error_msg,
            stages=stages,
            denyForensics=deny_forensics,
            totalPolicyDenies=(summary_data or {}).get("totalPolicyDenies", 0),
            artifactCount=(summary_data or {}).get("artifactCount", 0),
            totalDurationMs=mission_data.get("totalDurationMs"),
            startedAt=mission_data.get("startedAt"),
            completedAt=mission_data.get("finishedAt"),
            finalState=(summary_data or {}).get("finalState")
            or (state_data or {}).get("status"),
            stateTransitions=transitions,
        )
        meta = ResponseMeta(
            freshnessMs=max_age,
            dataQuality=dq,
            sourcesUsed=sources_used,
            sourcesMissing=sources_missing,
        )
        return mission, meta

    # ── Approvals ────────────────────────────────────────────────

    def list_approvals(self) -> tuple[list[ApprovalEntry], ResponseMeta]:
        """List all approval records."""
        items = []
        if not self._approvals_dir.exists():
            meta = ResponseMeta(
                dataQuality=DataQuality.UNKNOWN,
                sourcesMissing=["approvals"])
            return items, meta

        for fpath in sorted(self._approvals_dir.glob("apv-*.json"),
                            reverse=True):
            try:
                data, _ = self._read_source("approvals", str(fpath))
                if data is None:
                    continue
                items.append(self._approval_from_data(data))
            except Exception:
                continue

        meta = ResponseMeta(dataQuality=DataQuality.FRESH)
        return items, meta

    def get_approval(self, apv_id: str) -> Optional[
            tuple[ApprovalEntry, ResponseMeta]]:
        """Get single approval."""
        fpath = self._approvals_dir / f"{apv_id}.json"
        data, _ = self._read_tracked("approvals", fpath, [], [])
        if data is None:
            return None
        meta = ResponseMeta(dataQuality=DataQuality.FRESH)
        return self._approval_from_data(data), meta

    # ── Telemetry ────────────────────────────────────────────────

    def get_telemetry(self, mission_id: str = None,
                      limit: int = 200) -> tuple[
            list[TelemetryEntry], ResponseMeta]:
        """Read telemetry events."""
        if not self._telemetry_path.exists():
            meta = ResponseMeta(
                dataQuality=DataQuality.NOT_REACHED,
                sourcesMissing=["telemetry"])
            return [], meta

        entries = []
        source_file = self._telemetry_path.name
        try:
            with open(self._telemetry_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        event_mid = (event.get("data") or {}).get("mission_id")
                        if mission_id and event_mid != mission_id:
                            continue
                        entries.append(TelemetryEntry(
                            type=event.get("event_type",
                                           event.get("type", "unknown")),
                            timestamp=event.get("timestamp"),
                            missionId=event_mid,
                            sourceFile=source_file,
                            data=event.get("data", {}),
                        ))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        if limit and len(entries) > limit:
            entries = entries[-limit:]

        meta = ResponseMeta(dataQuality=DataQuality.FRESH)
        return entries, meta

    # ── Cache Stats ──────────────────────────────────────────────

    def get_cache_stats(self):
        return self._cache.stats()

    # ── Private ──────────────────────────────────────────────────

    def _read_source(self, source_name: str,
                     path: str) -> tuple[Optional[dict], int]:
        """Read through cache + circuit breaker. Returns (data, age_ms)."""
        def _do_read():
            return self._cache.get(Path(path))
        try:
            data, _ = self._cb.call(source_name, _do_read)
        except CircuitBreakerOpen:
            return None, 0
        except Exception:
            return None, 0
        if data is None:
            return None, 0
        try:
            age_ms = int((time.time() - os.path.getmtime(path)) * 1000)
        except OSError:
            age_ms = 0
        return data, age_ms

    def _read_tracked(self, source_name: str, path: Path,
                      sources_used: list, sources_missing: list
                      ) -> tuple[Optional[dict], int]:
        """Read source with tracking."""
        if not path.exists():
            sources_missing.append(source_name)
            return None, 0
        data, age_ms = self._read_source(source_name, str(path))
        threshold = _SOURCE_STALE.get(source_name, 30_000)
        if data is not None:
            src_dq = (DataQuality.STALE if age_ms > threshold
                      else DataQuality.FRESH)
            sources_used.append(SourceInfo(
                name=source_name, ageMs=age_ms, status=src_dq))
        else:
            sources_used.append(SourceInfo(
                name=source_name, ageMs=age_ms,
                status=DataQuality.DEGRADED))
        return data, age_ms

    def _compute_quality(self, sources_used: list[SourceInfo],
                         sources_missing: list[str]) -> DataQuality:
        """GPT Fix 2: Priority: degraded > stale > partial > fresh."""
        has_degraded = any(
            s.status == DataQuality.DEGRADED for s in sources_used)
        has_stale = any(
            s.status == DataQuality.STALE for s in sources_used)
        has_missing = len(sources_missing) > 0
        has_used = len(sources_used) > 0

        if not has_used and has_missing:
            return DataQuality.UNKNOWN
        if has_degraded:
            return DataQuality.DEGRADED
        if has_stale:
            return DataQuality.STALE
        if has_missing:
            return DataQuality.PARTIAL
        return DataQuality.FRESH

    def _build_stages(self, summary_data, mission_data) -> list[StageDetail]:
        """Build stage list from summary (preferred) or mission."""
        raw = []
        if summary_data and summary_data.get("stages"):
            raw = summary_data["stages"]
        elif mission_data and mission_data.get("stages"):
            raw = mission_data["stages"]

        stages = []
        for i, s in enumerate(raw):
            stage = StageDetail(
                index=i,
                role=s.get("role", s.get("specialist", "")),
                agentUsed=s.get("agentUsed", s.get("agent_used")),
                status=s.get("status", "unknown"),
                error=s.get("error"),
                result=s.get("result"),
                toolCalls=s.get("toolCalls", s.get("tool_call_count", 0)),
                policyDenies=s.get("policyDenies",
                                   s.get("policy_deny_count", 0)),
                durationMs=s.get("durationMs", s.get("duration_ms")),
                isRework=s.get("isRework", s.get("is_rework", False)),
                reworkCycle=s.get("reworkCycle", s.get("rework_cycle", 0)),
                isRecovery=s.get("isRecovery", s.get("is_recovery", False)),
            )
            gr = s.get("gateResults", s.get("gate_results"))
            if gr:
                stage.gateResults = GateResultDetail(
                    gateName=gr.get("gateName", gr.get("gate_name", "")),
                    passed=gr.get("passed", False),
                    findings=[Finding(**f) for f in gr.get("findings", [])],
                )
            df = s.get("denyForensics", s.get("deny_forensics"))
            if df and isinstance(df, dict):
                stage.denyForensics = df
            stages.append(stage)

        return stages

    def _approval_from_data(self, data: dict) -> ApprovalEntry:
        return ApprovalEntry(
            id=data.get("approvalId", ""),
            missionId=data.get("sessionId"),
            toolName=data.get("toolName"),
            risk=data.get("risk"),
            status=data.get("status", "unknown"),
            requestedAt=data.get("requestedAt"),
            respondedAt=data.get("decidedAt"),
        )
