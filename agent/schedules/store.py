"""Mission schedule store — D-120 / B-101.

File-based CRUD for mission schedules. Follows TemplateStore pattern.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from schedules.schema import MissionSchedule, next_cron_time

logger = logging.getLogger("mcc.schedules")


class ScheduleStore:
    """File-based schedule storage."""

    def __init__(self, schedules_dir: Path | None = None):
        self._dir = schedules_dir or Path(__file__).resolve().parent.parent.parent / "config" / "schedules"
        self._dir.mkdir(parents=True, exist_ok=True)

    def list(self, enabled_only: bool = False) -> list[dict]:
        """List all schedules."""
        schedules = []
        for f in sorted(self._dir.glob("*.json")):
            sched = self._load(f)
            if sched:
                if enabled_only and not sched.enabled:
                    continue
                schedules.append(sched.to_dict())
        return schedules

    def get(self, schedule_id: str) -> Optional[MissionSchedule]:
        """Get schedule by ID."""
        path = self._dir / f"{schedule_id}.json"
        if not path.exists():
            return None
        return self._load(path)

    def create(self, data: dict) -> MissionSchedule:
        """Create a new schedule."""
        now = datetime.now(timezone.utc)
        sched = MissionSchedule(
            name=data.get("name", "Untitled Schedule"),
            template_id=data.get("template_id", ""),
            cron=data.get("cron", ""),
            timezone=data.get("timezone", "Europe/Istanbul"),
            parameters=data.get("parameters", {}),
            enabled=data.get("enabled", True),
            max_concurrent=data.get("max_concurrent", 1),
        )
        # Calculate next run
        if sched.cron and sched.enabled:
            try:
                sched.next_run = next_cron_time(sched.cron, now).isoformat()
            except ValueError:
                logger.warning("Invalid cron expression: %s", sched.cron)
        self._save(sched)
        logger.info("Schedule created: %s (%s) cron=%s", sched.name, sched.id, sched.cron)
        return sched

    def update(self, schedule_id: str, data: dict) -> Optional[MissionSchedule]:
        """Update existing schedule."""
        sched = self.get(schedule_id)
        if not sched:
            return None
        for key in ("name", "cron", "timezone", "parameters", "enabled", "max_concurrent"):
            if key in data:
                setattr(sched, key, data[key])
        sched.updated_at = datetime.now(timezone.utc).isoformat()
        # Recalculate next run if cron changed
        if "cron" in data or "enabled" in data:
            if sched.cron and sched.enabled:
                try:
                    sched.next_run = next_cron_time(sched.cron, datetime.now(timezone.utc)).isoformat()
                except ValueError:
                    sched.next_run = None
            else:
                sched.next_run = None
        self._save(sched)
        logger.info("Schedule updated: %s", schedule_id)
        return sched

    def delete(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        path = self._dir / f"{schedule_id}.json"
        if not path.exists():
            return False
        path.unlink()
        logger.info("Schedule deleted: %s", schedule_id)
        return True

    def record_run(self, schedule_id: str, mission_id: str) -> Optional[MissionSchedule]:
        """Record a schedule execution."""
        sched = self.get(schedule_id)
        if not sched:
            return None
        now = datetime.now(timezone.utc)
        sched.last_run = now.isoformat()
        sched.last_mission_id = mission_id
        sched.run_count += 1
        sched.updated_at = now.isoformat()
        # Calculate next run
        if sched.cron and sched.enabled:
            try:
                sched.next_run = next_cron_time(sched.cron, now).isoformat()
            except ValueError:
                sched.next_run = None
        self._save(sched)
        return sched

    def _save(self, sched: MissionSchedule) -> None:
        path = self._dir / f"{sched.id}.json"
        path.write_text(json.dumps(sched.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _load(self, path: Path) -> Optional[MissionSchedule]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return MissionSchedule(
                id=data["id"],
                name=data.get("name", ""),
                template_id=data.get("template_id", ""),
                cron=data.get("cron", ""),
                timezone=data.get("timezone", "Europe/Istanbul"),
                parameters=data.get("parameters", {}),
                enabled=data.get("enabled", True),
                last_run=data.get("last_run"),
                last_mission_id=data.get("last_mission_id"),
                next_run=data.get("next_run"),
                run_count=data.get("run_count", 0),
                max_concurrent=data.get("max_concurrent", 1),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load schedule %s: %s", path, e)
            return None
