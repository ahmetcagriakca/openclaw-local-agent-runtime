# D-151 Apply Pack — Project-Scoped GitHub Communication Surface

Status: implementation-ready patch pack
Scope: tracked-file wiring that complements the already-added `D-151` decision doc and `agent/services/github_project_service.py`

## Identity contract (frozen)

Use this mapping everywhere in the GitHub surface:

- `user_id = ahmetcagriakca`
- `username = ahmetcagriakca`
- `display_name = Ahmet Çağrı AKCA`

Forbidden value:

- `TURKCELL\\TCAHMAKCA`

Do not write that value into `user_id`, `username`, `display_name`, `owner`, `actor`, `source_user_id`, docs, PR body, or any bound metadata.

---

## 1. Patch `agent/events/catalog.py`

Add 3 project GitHub event types before `PROJECT_ROLLUP_UPDATED`:

```python
    # ── Project GitHub surface (D-151) ───────────────────────────
    PROJECT_GITHUB_BOUND = "project.github_bound"
    PROJECT_GITHUB_SYNCED = "project.github_synced"
    PROJECT_GITHUB_COMMENT_PUBLISHED = "project.github_comment_published"
```

Also update the header text from `28 event types across 7 namespaces.` to `31 event types across 8 namespaces.`

---

## 2. Patch `agent/events/handlers/project_handler.py`

### Extend `PROJECT_EVENT_TYPES`

Add:

```python
    EventType.PROJECT_GITHUB_BOUND,
    EventType.PROJECT_GITHUB_SYNCED,
    EventType.PROJECT_GITHUB_COMMENT_PUBLISHED,
```

### Extend `SSE_BROADCAST_EVENTS`

Add:

```python
    EventType.PROJECT_GITHUB_BOUND,
    EventType.PROJECT_GITHUB_SYNCED,
    EventType.PROJECT_GITHUB_COMMENT_PUBLISHED,
```

### Add log branches

Insert before the `PROJECT_ROLLUP_UPDATED` branch:

```python
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
```

---

## 3. Patch `agent/persistence/project_store.py`

### Add constant

After `MISSION_QUIESCENT_STATUSES` add:

```python
MAX_GITHUB_ACTIVITY_ITEMS = 200
```

### Add helpers

After `generate_project_id()` add:

```python
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_repo_full_name(repo_full_name: str) -> str:
    repo = (repo_full_name or "").strip().strip("/")
    if repo.count("/") != 1:
        raise ProjectStoreError(f"Invalid repo_full_name: {repo_full_name}")
    return repo
```

### Add project GitHub persistence methods

Insert before `# ── Internal`:

```python
    def get_github(self, project_id: str) -> dict:
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")
            return {
                "binding": dict(proj.get("github")) if proj.get("github") else None,
                "activity": [dict(item) for item in proj.get("github_activity", [])],
                "last_sync_at": proj.get("github_last_sync_at"),
            }

    def bind_github(
        self,
        project_id: str,
        repo_full_name: str,
        *,
        issue_number: int | None = None,
        pr_number: int | None = None,
        bound_by: dict | None = None,
    ) -> dict:
        repo = _normalize_repo_full_name(repo_full_name)
        if issue_number is None and pr_number is None:
            raise ProjectStoreError("GitHub binding requires issue_number or pr_number")
        if issue_number is not None and pr_number is not None:
            raise ProjectStoreError("GitHub binding accepts only one of issue_number or pr_number")

        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            binding = {
                "provider": "github",
                "repo_full_name": repo,
                "issue_number": issue_number,
                "pr_number": pr_number,
                "thread_number": issue_number if issue_number is not None else pr_number,
                "bound_at": _now_iso(),
                "updated_at": _now_iso(),
                "bound_by": dict(bound_by or {}),
            }
            proj["github"] = binding
            proj["updated_at"] = binding["updated_at"]
            self._save()
            return dict(binding)

    def sync_github_activity(self, project_id: str, sync_result: dict) -> dict:
        repo = _normalize_repo_full_name(sync_result.get("repo_full_name", ""))
        activity = sync_result.get("activity") or []
        if not isinstance(activity, list):
            raise ProjectStoreError("GitHub sync result has invalid activity payload")

        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")

            binding = proj.get("github")
            if not binding:
                raise ProjectStoreError(f"Project {project_id} has no GitHub binding")
            if binding.get("repo_full_name") != repo:
                raise ProjectStoreError("GitHub sync repo does not match project binding")

            proj["github_activity"] = activity[-MAX_GITHUB_ACTIVITY_ITEMS:]
            proj["github_last_sync_at"] = sync_result.get("fetched_at") or _now_iso()
            binding["updated_at"] = proj["github_last_sync_at"]
            proj["updated_at"] = proj["github_last_sync_at"]
            self._save()
            return {
                "binding": dict(binding),
                "activity": [dict(item) for item in proj["github_activity"]],
                "last_sync_at": proj["github_last_sync_at"],
            }

    def append_github_activity(self, project_id: str, activity_entry: dict) -> dict:
        with self._lock:
            proj = self._projects.get(project_id)
            if proj is None:
                raise ProjectStoreError(f"Project not found: {project_id}")
            items = list(proj.get("github_activity", []))
            items.append(dict(activity_entry))
            proj["github_activity"] = items[-MAX_GITHUB_ACTIVITY_ITEMS:]
            proj["github_last_sync_at"] = activity_entry.get("created_at") or _now_iso()
            proj["updated_at"] = _now_iso()
            self._save()
            return dict(activity_entry)
```

---

## 4. Patch `agent/api/project_api.py`

### Add imports

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth.middleware import AuthenticatedUser, require_operator
from events.bus import Event
from events.catalog import EventType
from services.github_project_service import (
    GitHubProjectService,
    GitHubProjectServiceError,
)
```

### Add request models

```python
class BindGitHubRequest(BaseModel):
    repo_full_name: str
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None


class PublishGitHubCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=65536)
```

### Add actor helpers

```python
def _default_actor_identity() -> dict:
    return {
        "user_id": "ahmetcagriakca",
        "username": "ahmetcagriakca",
        "display_name": "Ahmet Çağrı AKCA",
        "provider": "github",
    }


def _actor_identity(user: AuthenticatedUser | None) -> dict:
    if user is None:
        return _default_actor_identity()

    username = (user.username or user.user_id or "ahmetcagriakca").strip()
    if not username:
        username = "ahmetcagriakca"

    display_name = (user.display_name or "").strip() or "Ahmet Çağrı AKCA"

    return {
        "user_id": (user.user_id or username).strip() or "ahmetcagriakca",
        "username": username,
        "display_name": display_name,
        "provider": (user.provider or "github").strip() or "github",
    }


def _emit_project_event(request: Request, event_type: str, data: dict) -> None:
    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus is None:
        return
    event_bus.emit(Event(type=event_type, data=data, source="api.project_api"))
```

### Extend project detail response

Add:

```python
    github_state = store.get_github(project_id)
```

and return:

```python
            "github": github_state,
```

### Add endpoints

Append after the artifact endpoints:

```python
@router.get("/{project_id}/github")
async def get_project_github(project_id: str):
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"meta": _meta(), "data": store.get_github(project_id)}


@router.post("/{project_id}/github/bind", status_code=201)
async def bind_project_github(
    project_id: str,
    req: BindGitHubRequest,
    request: Request,
    operator: AuthenticatedUser | None = Depends(require_operator),
):
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    actor = _actor_identity(operator)
    try:
        binding = store.bind_github(
            project_id,
            req.repo_full_name,
            issue_number=req.issue_number,
            pr_number=req.pr_number,
            bound_by=actor,
        )
    except ProjectStoreError as e:
        raise HTTPException(status_code=422, detail=str(e))

    _emit_project_event(
        request,
        EventType.PROJECT_GITHUB_BOUND,
        {
            "project_id": project_id,
            "repo_full_name": binding["repo_full_name"],
            "thread_number": binding["thread_number"],
            "issue_number": binding.get("issue_number"),
            "pr_number": binding.get("pr_number"),
            "actor": actor["username"],
            "display_name": actor["display_name"],
        },
    )
    return {"meta": _meta(), "data": binding}


@router.post("/{project_id}/github/sync")
async def sync_project_github(
    project_id: str,
    request: Request,
    operator: AuthenticatedUser | None = Depends(require_operator),
):
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    github_state = store.get_github(project_id)
    binding = github_state.get("binding")
    if not binding:
        raise HTTPException(status_code=409, detail="Project has no GitHub binding")

    service = GitHubProjectService()
    try:
        sync_result = service.sync_binding(binding)
        snapshot = store.sync_github_activity(project_id, sync_result)
    except GitHubProjectServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ProjectStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))

    actor = _actor_identity(operator)
    _emit_project_event(
        request,
        EventType.PROJECT_GITHUB_SYNCED,
        {
            "project_id": project_id,
            "repo_full_name": binding["repo_full_name"],
            "thread_number": binding["thread_number"],
            "activity_count": len(snapshot["activity"]),
            "fetched_at": snapshot["last_sync_at"],
            "actor": actor["username"],
            "display_name": actor["display_name"],
        },
    )
    return {"meta": _meta(), "data": snapshot}


@router.post("/{project_id}/github/comment", status_code=201)
async def publish_project_github_comment(
    project_id: str,
    req: PublishGitHubCommentRequest,
    request: Request,
    operator: AuthenticatedUser | None = Depends(require_operator),
):
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    github_state = store.get_github(project_id)
    binding = github_state.get("binding")
    if not binding:
        raise HTTPException(status_code=409, detail="Project has no GitHub binding")

    thread_number = binding.get("issue_number") or binding.get("pr_number")
    if thread_number is None:
        raise HTTPException(status_code=409, detail="GitHub binding has no thread number")

    service = GitHubProjectService()
    actor = _actor_identity(operator)

    try:
        remote_comment = service.post_issue_comment(
            binding["repo_full_name"],
            int(thread_number),
            req.body,
        )
    except GitHubProjectServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    activity_entry = {
        "activity_id": f"issue_comment:{remote_comment['id']}",
        "kind": "issue_comment",
        "direction": "outbound",
        "repo_full_name": binding["repo_full_name"],
        "thread_number": int(thread_number),
        "author": actor["username"],
        "display_name": actor["display_name"],
        "body": remote_comment.get("body") or req.body.strip(),
        "created_at": remote_comment.get("created_at"),
        "updated_at": remote_comment.get("updated_at"),
        "html_url": remote_comment.get("html_url"),
        "comment_id": remote_comment.get("id"),
    }
    store.append_github_activity(project_id, activity_entry)

    _emit_project_event(
        request,
        EventType.PROJECT_GITHUB_COMMENT_PUBLISHED,
        {
            "project_id": project_id,
            "repo_full_name": binding["repo_full_name"],
            "thread_number": int(thread_number),
            "comment_id": remote_comment.get("id"),
            "actor": actor["username"],
            "display_name": actor["display_name"],
            "html_url": remote_comment.get("html_url"),
        },
    )
    return {"meta": _meta(), "data": activity_entry}
```

---

## 5. Validation

Run after patching:

```bash
cd agent
python -m pytest tests/ -q
python -m py_compile api/project_api.py persistence/project_store.py events/catalog.py events/handlers/project_handler.py services/github_project_service.py
```

Manual API checks:

```bash
# bind
curl -X POST http://127.0.0.1:8003/api/v1/projects/<project_id>/github/bind \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"repo_full_name":"ahmetcagriakca/vezir","issue_number":1}'

# sync
curl -X POST http://127.0.0.1:8003/api/v1/projects/<project_id>/github/sync \
  -H 'Authorization: Bearer <token>'

# comment
curl -X POST http://127.0.0.1:8003/api/v1/projects/<project_id>/github/comment \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <token>' \
  -d '{"body":"D-151 connectivity check"}'
```

---

## 6. Outcome

When this apply pack is executed, Vezir keeps its current architectural base intact:

- GitHub is project-scoped, not execution owner
- Mission FSM remains untouched
- EventBus + SSE stay canonical for project surface notifications
- No file handoff drift is required for issue/PR thread communication
