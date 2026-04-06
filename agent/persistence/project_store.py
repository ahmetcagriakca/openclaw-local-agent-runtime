"""ProjectStore — project aggregate persistence (JSON file).

D-144: Project entity + CRUD + FSM enforcement + lifecycle constraints.
Persists project data with atomic write pattern (temp → fsync → os.replace).
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.persistence.projects")


class ProjectStatus(Enum):
    """6-state project FSM per D-144 §4."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


# D-144 §4: Transition matrix
VALID_PROJECT_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.DRAFT: {ProjectStatus.ACTIVE, ProjectStatus.CANCELLED},
    ProjectStatus.ACTIVE: {
        ProjectStatus.PAUSED,
        ProjectStatus.COMPLETED,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.PAUSED: {ProjectStatus.ACTIVE, ProjectStatus.CANCELLED},
    ProjectStatus.COMPLETED: {ProjectStatus.ARCHIVED},
    ProjectStatus.CANCELLED: {ProjectStatus.ARCHIVED},
    ProjectStatus.ARCHIVED: set(),
}

# D-144 §5: Statuses that require all linked missions quiescent
QUIESCENT_REQUIRED_TARGETS = {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}

# D-144 §5: Statuses where delete is allowed
DELETABLE_STATUSES = {ProjectStatus.DRAFT, ProjectStatus.ACTIVE, ProjectStatus.PAUSED}

# D-144 §5: Statuses that accept new mission links
LINKABLE_STATUSES = {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}

# D-144 §5: Statuses that allow unlink
UNLINKABLE_STATUSES = {ProjectStatus.DRAFT, ProjectStatus.ACTIVE, ProjectStatus.PAUSED}

# D-144 §5: Archive only from these
ARCHIVABLE_STATUSES = {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}

# D-144 §3: Mission quiescent states
MISSION_QUIESCENT_STATUSES = {"completed", "failed", "timed_out"}


class ProjectStoreError(Exception):
    """Base error for project store operations."""


class InvalidTransitionError(ProjectStoreError):
    """Raised when a status transition is invalid per FSM."""

    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid transition: {current} → {target}"
        )


class ActiveMissionsError(ProjectStoreError):
    """Raised when operation blocked by active missions."""

    def __init__(self, mission_ids: list[str], operation: str):
        self.mission_ids = mission_ids
        self.operation = operation
        super().__init__(
            f"Cannot {operation}: {len(mission_ids)} active mission(s): "
            f"{', '.join(mission_ids[:5])}"
        )


class ProjectLifecycleError(ProjectStoreError):
    """Raised when lifecycle constraint is violated."""

    def __init__(self, message: str):
        super().__init__(message)


def generate_project_id() -> str:
    """Generate project ID with proj_ prefix per D-144 §2."""
    return f"proj_{uuid.uuid4().hex[:12]}"


class ProjectStore:
    """Persistent project store with FSM enforcement.

    Storage: single JSON file with all projects.
    Pattern: matches MissionStore (atomic write, thread-safe).
    """

    def __init__(self, store_path: Path | str | None = None,
                 mission_store=None):
        if store_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            store_path = root / "logs" / "project-history.json"
        self._path = Path(store_path)
        self._lock = threading.Lock()
        self._projects: dict[str, dict] = {}
        self._mission_store = mission_store
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._projects = data.get("projects", {})
                logger.info("ProjectStore loaded %d projects",
                            len(self._projects))
            except Exception as e:
                logger.warning("ProjectStore load failed: %s", e)
                self._projects = {}

    def _save(self) -> None:
        try:
            atomic_write_json(self._path, {
                "version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "projects": self._projects,
            })
        except Exception as e:
            logger.error("ProjectStore save failed: %s", e)

    # ── CRUD ─────────────────────────────────────────────────────

    def create(self, name: str, description: str = "",
               owner: str = "operator") -> dict:
        """Create a new project in draft status."""
        now = datetime.now(timezone.utc).isoformat()
        project_id = generate_project_id()
        project = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "status": ProjectStatus.DRAFT.value,
            "owner": owner,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            self._projects[project_id] = project
            self._save()
        logger.info("Project created: %s (%s)", project_id, name)
        return dict(project)

    def get(self, project_id: str) -> dict | None:
        """Get a single project by ID."""
        with self._lock:
            proj = self._projects.get(project_id)
            return dict(proj) if proj else None

    def list(
        self,
        status: list[str] | None = None,
        search: str | None = None,
        sort: str = "updated_at_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List projects with filters and pagination."""
        with self._lock:
            items = [dict(p) for p in self._projects.values()]

        if status:
            items = [p for p in items if p.get("status") in status]
        if search:
            q = search.lower()
            items = [p for p in items
                     if q in p.get("name", "").lower()
                     or q in p.get("description", "").lower()]

        total = len(items)

        # Sort
        if sort == "updated_at_desc":
            items.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        elif sort == "name_asc":
            items.sort(key=lambda p: p.get("name", "").lower())
        elif sort == "created_at_desc":
            items.sort(key=lambda p: p.get("created_at", ""), reverse=True)

        items = items[offset:offset + limit]
        return items, total

    def update(self, project_id: str, **fields) -> dict:
        """Update project fields. Status changes go through transition_status."""
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            allowed_fields = {"name", "description", "owner"}
            for key, value in fields.items():
                if key in allowed_fields:
                    proj[key] = value

            proj["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
            return dict(proj)

    def delete(self, project_id: str) -> dict:
        """Soft-delete a project (sets status to cancelled).

        D-144 §5: Only allowed for draft/active/paused.
        Completed/archived projects cannot be deleted.
        Projects with active missions cannot be deleted.
        """
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            current = ProjectStatus(proj["status"])

            # Already cancelled = no-op
            if current == ProjectStatus.CANCELLED:
                return dict(proj)

            if current not in DELETABLE_STATUSES:
                raise ProjectLifecycleError(
                    f"Cannot delete {current.value} project. "
                    f"Completed projects must be archived, not deleted."
                )

            # Check for active missions
            active = self._get_active_mission_ids_unlocked(project_id)
            if active:
                raise ActiveMissionsError(active, "delete")

            proj["status"] = ProjectStatus.CANCELLED.value
            proj["deleted_at"] = datetime.now(timezone.utc).isoformat()
            proj["updated_at"] = proj["deleted_at"]
            self._save()
            logger.info("Project soft-deleted: %s", project_id)
            return dict(proj)

    # ── Status FSM ───────────────────────────────────────────────

    def transition_status(self, project_id: str,
                          target_status: str) -> dict:
        """Transition project status per D-144 §4 FSM.

        Raises InvalidTransitionError for invalid transitions.
        Raises ActiveMissionsError for complete/cancel with active missions.
        """
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            try:
                current = ProjectStatus(proj["status"])
                target = ProjectStatus(target_status)
            except ValueError:
                raise InvalidTransitionError(
                    proj["status"], target_status)

            # Check FSM validity
            valid_targets = VALID_PROJECT_TRANSITIONS.get(current, set())
            if target not in valid_targets:
                raise InvalidTransitionError(current.value, target.value)

            # D-144 §4: Quiescent check for complete/cancel
            if target in QUIESCENT_REQUIRED_TARGETS:
                active = self._get_active_mission_ids_unlocked(project_id)
                if active:
                    raise ActiveMissionsError(
                        active, f"transition to {target.value}")

            old_status = proj["status"]
            proj["status"] = target.value
            proj["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
            logger.info("Project %s: %s → %s",
                        project_id, old_status, target.value)
            return dict(proj)

    # ── Mission Link/Unlink ──────────────────────────────────────

    def link_mission(self, project_id: str, mission_id: str) -> None:
        """Link a mission to this project.

        D-144 §5: Only allowed for draft/active projects.
        Paused/completed/cancelled/archived reject.
        """
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            current = ProjectStatus(proj["status"])
            if current not in LINKABLE_STATUSES:
                raise ProjectLifecycleError(
                    f"Cannot link mission to {current.value} project. "
                    f"Project must be draft or active."
                )

        # Update mission's project_id via mission_store
        if self._mission_store is not None:
            mission = self._mission_store.get(mission_id)
            if mission is None:
                raise ProjectStoreError(
                    f"Mission not found: {mission_id}")
            mission["project_id"] = project_id
            self._mission_store.record(mission)

    def unlink_mission(self, project_id: str, mission_id: str) -> None:
        """Unlink a mission from this project.

        D-144 §5: Only allowed for draft/active/paused projects.
        Completed/cancelled/archived reject (historical links preserved).
        """
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            current = ProjectStatus(proj["status"])
            if current not in UNLINKABLE_STATUSES:
                raise ProjectLifecycleError(
                    f"Cannot unlink mission from {current.value} project. "
                    f"Historical links are preserved."
                )

        # Clear mission's project_id via mission_store
        if self._mission_store is not None:
            mission = self._mission_store.get(mission_id)
            if mission is None:
                raise ProjectStoreError(
                    f"Mission not found: {mission_id}")
            mission["project_id"] = None
            self._mission_store.record(mission)

    # ── Queries ──────────────────────────────────────────────────

    def get_missions(self, project_id: str) -> list[dict]:
        """Get all missions linked to a project."""
        if self._mission_store is None:
            return []
        missions, _ = self._mission_store.list(limit=1000)
        return [m for m in missions
                if m.get("project_id") == project_id]

    def get_mission_summary(self, project_id: str) -> dict:
        """Compute derived mission summary for project detail.

        D-144 §7: Computed on each GET, not stored.
        """
        missions = self.get_missions(project_id)
        by_status: dict[str, int] = {}
        active_count = 0
        quiescent_count = 0
        last_activity = ""

        for m in missions:
            status = m.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            if status in MISSION_QUIESCENT_STATUSES:
                quiescent_count += 1
            else:
                active_count += 1
            ts = m.get("ts", "")
            if ts > last_activity:
                last_activity = ts

        return {
            "total": len(missions),
            "by_status": by_status,
            "active_count": active_count,
            "quiescent_count": quiescent_count,
            "last_activity": last_activity or None,
        }

    # ── Internal ─────────────────────────────────────────────────

    def _get_active_mission_ids_unlocked(self, project_id: str) -> list[str]:
        """Get IDs of active (non-quiescent) missions. Must hold lock."""
        if self._mission_store is None:
            return []
        missions, _ = self._mission_store.list(limit=1000)
        return [
            m.get("id", "")
            for m in missions
            if m.get("project_id") == project_id
            and m.get("status") not in MISSION_QUIESCENT_STATUSES
        ]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._projects)

    def clear(self) -> None:
        """Clear all projects. For testing only."""
        with self._lock:
            self._projects.clear()
            self._save()
