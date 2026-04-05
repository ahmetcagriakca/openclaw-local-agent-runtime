"""MissionPersistenceAdapter — extracted from MissionController (D-139, B-139).

Handles all mission-related disk I/O with atomic write pattern (D-071).
Pattern: temp → fsync → os.replace() — prevents corrupt JSON on crash/timeout.
"""
import json
import logging
import os
import tempfile
from datetime import datetime, timezone

logger = logging.getLogger("mcc.mission.persistence_adapter")

MISSIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "missions"
)


class MissionPersistenceAdapter:
    """Atomic file persistence for missions, state machines, and token reports."""

    def __init__(self, missions_dir: str | None = None):
        self._missions_dir = missions_dir or MISSIONS_DIR
        os.makedirs(self._missions_dir, exist_ok=True)

    @staticmethod
    def _atomic_write_json(path: str, data: dict, directory: str | None = None):
        """Atomic write: temp → fsync → os.replace (D-071)."""
        target_dir = directory or os.path.dirname(path)
        os.makedirs(target_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=target_dir, suffix=".tmp", prefix="atomic-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def save_mission(self, mission: dict):
        """Save mission state to disk (BF-8.0, D-071)."""
        path = os.path.join(self._missions_dir,
                            f"{mission['missionId']}.json")
        try:
            self._atomic_write_json(path, mission, self._missions_dir)
        except Exception:
            pass  # Best effort — don't block mission execution

    def persist_mission_state(self, mission_state) -> None:
        """5C-1: Persist mission state machine to disk (D-071)."""
        state_path = os.path.join(
            self._missions_dir,
            f"{mission_state.mission_id}-state.json")
        try:
            self._atomic_write_json(
                state_path, mission_state.to_dict(), self._missions_dir)
        except Exception:
            pass

    def save_token_report(self, mission: dict):
        """Save aggregated token report to {mission_id}-token-report.json (D-071)."""
        mission_id = mission.get("missionId", "")
        if not mission_id:
            return

        stages = mission.get("stages", [])
        stage_reports = []
        total_tokens = 0
        total_tool_calls = 0
        total_truncations = 0
        total_blocks = 0

        for stage in stages:
            sr = stage.get("token_report")
            if sr and isinstance(sr, dict):
                for s in sr.get("stages", []):
                    stage_reports.append(s)
                total_tokens += sr.get("total_tokens", 0)
                total_tool_calls += sr.get("total_tool_calls", 0)
                total_truncations += sr.get("truncations", 0)
                total_blocks += sr.get("blocks", 0)
            elif stage.get("status") == "completed":
                from context.token_budget import estimate_tokens
                result_tokens = estimate_tokens(stage.get("result", ""))
                stage_reports.append({
                    "stage": stage.get("stageId", ""),
                    "tokens_consumed": result_tokens,
                    "tool_calls": stage.get("tool_call_count", 0),
                    "pct_of_total": 0,
                })
                total_tokens += result_tokens
                total_tool_calls += stage.get("tool_call_count", 0)

        for s in stage_reports:
            if total_tokens > 0:
                s["pct_of_total"] = round(
                    s["tokens_consumed"] / total_tokens * 100, 1)

        report = {
            "mission_id": mission_id,
            "status": mission.get("status", "unknown"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_tokens": total_tokens,
            "total_tool_calls": total_tool_calls,
            "truncations": total_truncations,
            "blocks": total_blocks,
            "stages": stage_reports,
        }

        report_path = os.path.join(
            self._missions_dir, f"{mission_id}-token-report.json")
        try:
            self._atomic_write_json(report_path, report, self._missions_dir)
        except Exception:
            pass  # Best effort

    @staticmethod
    def find_stage_index(stages: list, target_stage_id: str) -> int | None:
        """Find index of stage by ID."""
        for i, s in enumerate(stages):
            if s.get("id") == target_stage_id:
                return i
        return None
