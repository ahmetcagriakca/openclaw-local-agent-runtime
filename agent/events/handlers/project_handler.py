"""ProjectHandler — audit trail for project lifecycle events (D-144 §9, D-145).

Handles 8 project event types. Logs to structured logger.
Does not halt event propagation.
"""
from __future__ import annotations

import logging

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.project.events")

PROJECT_EVENT_TYPES = frozenset({
    EventType.PROJECT_CREATED,
    EventType.PROJECT_STATUS_CHANGED,
    EventType.PROJECT_MISSION_LINKED,
    EventType.PROJECT_MISSION_UNLINKED,
    EventType.PROJECT_DELETED,
    EventType.PROJECT_WORKSPACE_ENABLED,
    EventType.PROJECT_ARTIFACT_PUBLISHED,
    EventType.PROJECT_ARTIFACT_UNPUBLISHED,
})


class ProjectHandler:
    """Audit handler for project lifecycle events.

    Phase 1: logging only. Phase 2 adds SSE broadcast + rollup cache.
    """

    def __call__(self, event: Event) -> HandlerResult:
        if event.type not in PROJECT_EVENT_TYPES:
            return HandlerResult.skip()

        data = event.data
        project_id = data.get("project_id", "?")

        if event.type == EventType.PROJECT_CREATED:
            logger.info(
                "[PROJECT] Created: %s name=%s owner=%s",
                project_id, data.get("name"), data.get("owner"))

        elif event.type == EventType.PROJECT_STATUS_CHANGED:
            logger.info(
                "[PROJECT] Status changed: %s %s → %s actor=%s",
                project_id,
                data.get("old_status"),
                data.get("new_status"),
                data.get("actor", "operator"))

        elif event.type == EventType.PROJECT_MISSION_LINKED:
            logger.info(
                "[PROJECT] Mission linked: %s ← mission %s",
                project_id, data.get("mission_id"))

        elif event.type == EventType.PROJECT_MISSION_UNLINKED:
            logger.info(
                "[PROJECT] Mission unlinked: %s → mission %s",
                project_id, data.get("mission_id"))

        elif event.type == EventType.PROJECT_DELETED:
            logger.info(
                "[PROJECT] Deleted: %s at=%s actor=%s",
                project_id,
                data.get("deleted_at"),
                data.get("actor", "operator"))

        elif event.type == EventType.PROJECT_WORKSPACE_ENABLED:
            logger.info(
                "[PROJECT] Workspace enabled: %s root=%s",
                project_id, data.get("workspace_root"))

        elif event.type == EventType.PROJECT_ARTIFACT_PUBLISHED:
            logger.info(
                "[PROJECT] Artifact published: %s artifact=%s mission=%s",
                project_id,
                data.get("artifact_id"),
                data.get("mission_id"))

        elif event.type == EventType.PROJECT_ARTIFACT_UNPUBLISHED:
            logger.info(
                "[PROJECT] Artifact unpublished: %s artifact=%s",
                project_id, data.get("artifact_id"))

        return HandlerResult.proceed()
