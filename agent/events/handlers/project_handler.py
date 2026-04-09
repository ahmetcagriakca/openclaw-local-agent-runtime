"""ProjectHandler — audit trail + SSE broadcast for project lifecycle events.

D-144 §9: Audit logging for project events.
D-145 Faz 2B: SSE broadcast for project events + rollup invalidation.
Handles 12 project event types. Logs to structured logger.
Does not halt event propagation.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from events.bus import Event, HandlerResult
from events.catalog import EventType

if TYPE_CHECKING:
    from api.sse_manager import SSEManager
    from persistence.project_store import ProjectStore

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
    EventType.PROJECT_ROLLUP_UPDATED,
    EventType.PROJECT_GITHUB_BOUND,
    EventType.PROJECT_GITHUB_SYNCED,
    EventType.PROJECT_GITHUB_COMMENT_PUBLISHED,
})

# Events that should trigger SSE broadcast
SSE_BROADCAST_EVENTS = frozenset({
    EventType.PROJECT_STATUS_CHANGED,
    EventType.PROJECT_ROLLUP_UPDATED,
    EventType.PROJECT_ARTIFACT_PUBLISHED,
    EventType.PROJECT_ARTIFACT_UNPUBLISHED,
    EventType.PROJECT_GITHUB_BOUND,
    EventType.PROJECT_GITHUB_SYNCED,
    EventType.PROJECT_GITHUB_COMMENT_PUBLISHED,
})

# Events that should invalidate rollup cache
ROLLUP_INVALIDATION_EVENTS = frozenset({
    EventType.PROJECT_MISSION_LINKED,
    EventType.PROJECT_MISSION_UNLINKED,
    EventType.PROJECT_STATUS_CHANGED,
})


class ProjectHandler:
    """Audit handler for project lifecycle events.

    Phase 1: logging only.
    Phase 2 (D-145 Faz 2B): SSE broadcast + rollup cache invalidation.
    """

    def __init__(self, sse_manager: SSEManager | None = None,
                 project_store: ProjectStore | None = None):
        self._sse_manager = sse_manager
        self._project_store = project_store

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

        elif event.type == EventType.PROJECT_GITHUB_BOUND:
            logger.info(
                "[PROJECT] GitHub bound: %s repo=%s thread=%s actor=%s",
                project_id,
                data.get("repo_full_name"),
                data.get("thread_number"),
                data.get("actor"))

        elif event.type == EventType.PROJECT_GITHUB_SYNCED:
            logger.info(
                "[PROJECT] GitHub synced: %s repo=%s thread=%s items=%s",
                project_id,
                data.get("repo_full_name"),
                data.get("thread_number"),
                data.get("activity_count"))

        elif event.type == EventType.PROJECT_GITHUB_COMMENT_PUBLISHED:
            logger.info(
                "[PROJECT] GitHub comment published: %s repo=%s thread=%s comment_id=%s actor=%s",
                project_id,
                data.get("repo_full_name"),
                data.get("thread_number"),
                data.get("comment_id"),
                data.get("actor"))

        elif event.type == EventType.PROJECT_ROLLUP_UPDATED:
            logger.info(
                "[PROJECT] Rollup updated: %s total=%s active=%s",
                project_id,
                data.get("total_missions"),
                data.get("active_count"))

        # Rollup cache invalidation
        if (event.type in ROLLUP_INVALIDATION_EVENTS
                and self._project_store is not None):
            self._project_store.invalidate_rollup(project_id)

        # SSE broadcast for relevant events
        if event.type in SSE_BROADCAST_EVENTS and self._sse_manager is not None:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(
                        self._sse_manager.broadcast(event.type, data))
                else:
                    loop.run_until_complete(
                        self._sse_manager.broadcast(event.type, data))
            except RuntimeError:
                logger.debug("SSE broadcast skipped: no event loop")

        return HandlerResult.proceed()
