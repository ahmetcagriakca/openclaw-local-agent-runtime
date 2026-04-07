"""ProjectStore — project aggregate persistence (JSON file).

D-144: Project entity + CRUD + FSM enforcement + lifecycle constraints.
D-145: Workspace enable + artifact publish/unpublish flow.
Persists project data with atomic write pattern (temp → fsync → os.replace).
"""
from __future__ import annotations

import json
import logging
import shutil
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

# D-145 §1: Workspace can only be enabled for draft/active projects
WORKSPACE_ENABLED_STATUSES = {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}

# D-145 §3: Artifact publish/unpublish restricted to draft/active projects
ARTIFACT_MUTABLE_STATUSES = {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}

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
               owner: str = "operator",
               local_path: str | None = None) -> dict:
        """Create a new project in draft status.

        If local_path is provided, workspace is auto-enabled pointing to that
        directory. The path must exist on disk.
        """
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

        if local_path:
            resolved = Path(local_path).resolve()
            if not resolved.is_dir():
                raise ProjectStoreError(
                    f"Local path does not exist or is not a directory: {local_path}"
                )
            project["local_path"] = str(resolved)
            project["workspace_root"] = str(resolved)

        with self._lock:
            self._projects[project_id] = project
            self._save()
        logger.info("Project created: %s (%s) path=%s", project_id, name, local_path or "-")
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

            allowed_fields = {"name", "description", "owner", "local_path", "workspace_root"}
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

    # ── Workspace (D-145 §1) ────────────────────────────────────

    def enable_workspace(self, project_id: str,
                         projects_root: Path | str | None = None) -> dict:
        """Enable workspace for a project. Creates directory structure.

        D-145 §1: Only draft/active projects. 409 if already enabled.
        """
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            current = ProjectStatus(proj["status"])
            if current not in WORKSPACE_ENABLED_STATUSES:
                raise ProjectLifecycleError(
                    f"Cannot enable workspace for {current.value} project. "
                    f"Project must be draft or active."
                )

            if proj.get("workspace_root") is not None:
                # Already has workspace (e.g. from local_path at creation)
                return dict(proj)

            # Resolve projects root
            if projects_root is None:
                root = Path(__file__).resolve().parent.parent.parent
                projects_root = root / "projects"
            else:
                projects_root = Path(projects_root)

            proj_dir = projects_root / project_id
            workspace_dir = proj_dir / "workspace"
            artifact_dir = proj_dir / "artifacts"
            shared_dir = proj_dir / "shared"

            # Create directory structure
            workspace_dir.mkdir(parents=True, exist_ok=True)
            artifact_dir.mkdir(parents=True, exist_ok=True)
            (shared_dir / "decisions").mkdir(parents=True, exist_ok=True)
            (shared_dir / "notes").mkdir(parents=True, exist_ok=True)
            (shared_dir / "briefs").mkdir(parents=True, exist_ok=True)

            # Update project record
            proj["workspace_root"] = str(workspace_dir)
            proj["artifact_root"] = str(artifact_dir)
            proj["shared_root"] = str(shared_dir)
            proj["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
            logger.info("Workspace enabled for project %s", project_id)
            return dict(proj)

    def get_workspace(self, project_id: str) -> dict | None:
        """Get workspace metadata for a project."""
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                return None
            return {
                "project_id": project_id,
                "enabled": proj.get("workspace_root") is not None,
                "workspace_root": proj.get("workspace_root"),
                "artifact_root": proj.get("artifact_root"),
                "shared_root": proj.get("shared_root"),
            }

    # ── Artifacts (D-145 §3) ────────────────────────────────────

    def publish_artifact(self, project_id: str, mission_id: str,
                         artifact_id: str) -> dict:
        """Publish a mission artifact to project space.

        D-145 §3: Resolves artifact source from mission store.
        No caller-supplied paths. Copy to project artifact dir.
        """
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            current = ProjectStatus(proj["status"])
            if current not in ARTIFACT_MUTABLE_STATUSES:
                raise ProjectLifecycleError(
                    f"Cannot publish artifact on {current.value} project. "
                    f"Project must be draft or active."
                )

            if proj.get("artifact_root") is None:
                raise ProjectStoreError(
                    f"Workspace not enabled for {project_id}")

        # Verify mission is linked to this project
        if self._mission_store is not None:
            mission = self._mission_store.get(mission_id)
            if mission is None:
                raise ProjectStoreError(f"Mission not found: {mission_id}")
            if mission.get("project_id") != project_id:
                raise ProjectLifecycleError(
                    f"Mission {mission_id} is not linked to project "
                    f"{project_id}")
        else:
            raise ProjectStoreError("Mission store not available")

        # Resolve artifact source from mission artifacts
        source_path = self._resolve_artifact_path(mission, artifact_id)
        if source_path is None:
            raise ProjectStoreError(
                f"Artifact {artifact_id} not found in mission {mission_id}")

        source = Path(source_path)
        if not source.exists():
            raise ProjectStoreError(
                f"Artifact file not found: {source_path}")

        # Copy to project artifact directory
        with self._lock:
            proj = self._projects[project_id]
            dest_dir = Path(proj["artifact_root"]) / mission_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / source.name
            shutil.copy2(str(source), str(dest))

            # Track published artifacts in project record
            published = proj.setdefault("published_artifacts", [])
            artifact_entry = {
                "artifact_id": artifact_id,
                "mission_id": mission_id,
                "source_path": str(source),
                "published_path": str(dest),
                "published_at": datetime.now(timezone.utc).isoformat(),
                "published_to_project": True,
            }
            published.append(artifact_entry)
            proj["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()

        logger.info("Artifact %s published to project %s from mission %s",
                     artifact_id, project_id, mission_id)
        return artifact_entry

    def list_artifacts(self, project_id: str,
                       mission_id: str | None = None) -> list[dict]:
        """List published artifacts for a project."""
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            published = proj.get("published_artifacts", [])
            if mission_id:
                published = [a for a in published
                             if a.get("mission_id") == mission_id]
            return [dict(a) for a in published]

    def unpublish_artifact(self, project_id: str,
                           artifact_id: str) -> dict | None:
        """Remove a published artifact from project space.

        D-145 §3: Only draft/active projects. Removes copy, original intact.
        """
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            current = ProjectStatus(proj["status"])
            if current not in ARTIFACT_MUTABLE_STATUSES:
                raise ProjectLifecycleError(
                    f"Cannot unpublish artifact on {current.value} project. "
                    f"Inactive projects have immutable artifact sets."
                )

            published = proj.get("published_artifacts", [])
            entry = None
            for i, a in enumerate(published):
                if a.get("artifact_id") == artifact_id:
                    entry = published.pop(i)
                    break

            if entry is None:
                return None

            # Remove the copied file
            published_path = Path(entry["published_path"])
            if published_path.exists():
                published_path.unlink()

            proj["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
            logger.info("Artifact %s unpublished from project %s",
                         artifact_id, project_id)
            return entry

    # ── Rollup Cache (D-145 Faz 2B) ──────────────────────────────

    def compute_rollup(self, project_id: str) -> dict:
        """Compute rollup summary for a project.

        Returns total missions, by-status breakdown, active/quiescent counts,
        total tokens, last activity, computed timestamp.
        Caches result in project record; use get_rollup() for staleness-aware access.
        """
        missions = self.get_missions(project_id)
        by_status: dict[str, int] = {}
        active_count = 0
        quiescent_count = 0
        total_tokens = 0
        last_activity = ""

        for m in missions:
            status = m.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            if status in MISSION_QUIESCENT_STATUSES:
                quiescent_count += 1
            else:
                active_count += 1
            total_tokens += m.get("total_tokens", 0) or 0
            ts = m.get("ts", "")
            if ts > last_activity:
                last_activity = ts

        now = datetime.now(timezone.utc).isoformat()
        rollup = {
            "project_id": project_id,
            "total_missions": len(missions),
            "by_status": by_status,
            "active_count": active_count,
            "quiescent_count": quiescent_count,
            "total_tokens": total_tokens,
            "last_activity": last_activity or None,
            "computed_at": now,
        }

        # Cache in project record
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is not None:
                proj["_rollup_cache"] = rollup
                self._save()

        return rollup

    def get_rollup(self, project_id: str,
                   staleness_threshold_s: float = 300.0) -> dict:
        """Get rollup for a project with staleness-aware caching.

        If cached rollup is fresh (< staleness_threshold_s), return cached.
        Otherwise recompute from live mission store.
        """
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            cached = proj.get("_rollup_cache")
            if cached is not None:
                computed_at = cached.get("computed_at", "")
                if computed_at:
                    try:
                        computed_dt = datetime.fromisoformat(computed_at)
                        age = (datetime.now(timezone.utc) - computed_dt).total_seconds()
                        if age < staleness_threshold_s:
                            return dict(cached)
                    except (ValueError, TypeError):
                        pass

        # Cache miss or stale — recompute
        return self.compute_rollup(project_id)

    def invalidate_rollup(self, project_id: str) -> None:
        """Invalidate rollup cache for a project. Called by event handlers."""
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is not None:
                proj.pop("_rollup_cache", None)
                self._save()

    def _resolve_artifact_path(self, mission: dict,
                                artifact_id: str) -> str | None:
        """Resolve artifact file path from mission data.

        D-145 §3: Server-side resolution, no caller-supplied paths.
        Checks mission artifacts list and stages_detail for artifact_id.
        """
        # Check top-level mission artifacts
        for art in mission.get("artifacts", []):
            if art.get("id") == artifact_id:
                return art.get("path") or art.get("output_path")

        # Check stages_detail artifacts
        for stage in mission.get("stages_detail", []):
            for art in stage.get("artifacts", []):
                if art.get("id") == artifact_id:
                    return art.get("path") or art.get("output_path")

        return None
