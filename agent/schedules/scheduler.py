"""Background mission scheduler — D-120 / B-101.

Runs as an asyncio task, checks cron schedules every 60 seconds,
and spawns missions when due.
"""
import asyncio
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from schedules.schema import cron_matches
from schedules.store import ScheduleStore

logger = logging.getLogger("mcc.scheduler")

CHECK_INTERVAL_S = 60  # Check schedules every minute


class MissionScheduler:
    """Background scheduler that executes missions based on cron schedules."""

    def __init__(self, schedule_store: ScheduleStore, missions_dir: Path):
        self._store = schedule_store
        self._missions_dir = missions_dir
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start the scheduler background task."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started (check interval: %ds)", CHECK_INTERVAL_S)

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                await asyncio.sleep(CHECK_INTERVAL_S)
                self._check_and_execute()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler error: %s", e)

    def _check_and_execute(self):
        """Check all enabled schedules and execute due ones."""
        now = datetime.now(timezone.utc)
        schedules = self._store.list(enabled_only=True)

        for sched_data in schedules:
            sched_id = sched_data["id"]
            cron_expr = sched_data.get("cron", "")
            template_id = sched_data.get("template_id", "")

            if not cron_expr or not template_id:
                continue

            try:
                if cron_matches(cron_expr, now):
                    # Avoid duplicate runs within the same minute
                    last_run = sched_data.get("last_run")
                    if last_run:
                        last_dt = datetime.fromisoformat(last_run)
                        if (now - last_dt).total_seconds() < 60:
                            continue

                    logger.info("Schedule %s triggered (cron=%s)", sched_id, cron_expr)
                    self._execute_scheduled_mission(sched_id, template_id, sched_data.get("parameters", {}))
            except Exception as e:
                logger.error("Error checking schedule %s: %s", sched_id, e)

    def _execute_scheduled_mission(self, schedule_id: str, template_id: str, parameters: dict):
        """Execute a scheduled mission by creating it via the template system."""
        try:
            from templates.store import TemplateStore
            template_store = TemplateStore()
            template = template_store.get(template_id)

            if not template:
                logger.error("Schedule %s references missing template %s", schedule_id, template_id)
                return

            # Validate and render goal
            errors = template.validate_params(parameters)
            if errors:
                logger.error("Schedule %s param validation failed: %s", schedule_id, errors)
                return

            goal = template.render_goal(parameters)

            # Create mission via controller in background thread
            mission_id = self._create_mission(goal, schedule_id)
            if mission_id:
                self._store.record_run(schedule_id, mission_id)
                logger.info("Scheduled mission created: %s (schedule=%s)", mission_id, schedule_id)

        except Exception as e:
            logger.error("Failed to execute schedule %s: %s", schedule_id, e)

    def _create_mission(self, goal: str, schedule_id: str) -> str | None:
        """Create and start a mission in a background thread."""
        import json
        import os
        import time
        import uuid

        mission_id = f"mission-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self._missions_dir.mkdir(parents=True, exist_ok=True)

        # Write mission placeholder
        mission_data = {
            "missionId": mission_id,
            "goal": goal,
            "status": "pending",
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "finishedAt": None,
            "stages": [],
            "artifacts": [],
            "error": None,
            "createdFrom": f"schedule:{schedule_id}",
        }

        mission_path = self._missions_dir / f"{mission_id}.json"
        mission_path.write_text(json.dumps(mission_data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Run mission controller in background thread
        def _run():
            try:
                import sys
                agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if agent_dir not in sys.path:
                    sys.path.insert(0, agent_dir)

                from mission.controller import MissionController
                controller = MissionController()
                result = controller.execute_mission(
                    goal=goal,
                    user_id="scheduler",
                    session_id=f"sched-{schedule_id}-{int(time.time())}",
                )
                status = result.get("status", "completed")
                logger.info("Scheduled mission %s finished: %s", mission_id, status)
            except Exception as e:
                logger.error("Scheduled mission %s failed: %s", mission_id, e)
                # Update mission status to failed
                try:
                    mission_data["status"] = "failed"
                    mission_data["error"] = str(e)
                    mission_data["finishedAt"] = datetime.now(timezone.utc).isoformat()
                    mission_path.write_text(json.dumps(mission_data, indent=2), encoding="utf-8")
                except Exception as e:
                    logger.debug("mission status update: %s", e)

        thread = threading.Thread(target=_run, daemon=True, name=f"sched-mission-{mission_id[:20]}")
        thread.start()
        return mission_id
