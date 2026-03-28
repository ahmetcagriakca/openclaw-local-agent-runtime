# D-119: Mission Template Lifecycle Contract

**Phase:** 7 (Sprint 30)
**Status:** Frozen
**Date:** 2026-03-28

---

## Decision

File-based mission templates with JSON schema, CRUD API, parameter validation, and run-from-template execution.

## Template Schema

```json
{
  "id": "tmpl_uuid",
  "name": "Code Review Automation",
  "description": "Automated code review with specialist analysis",
  "version": "1.0.0",
  "author": "akca",
  "status": "published",
  "parameters": [
    {
      "name": "repo_url",
      "type": "string",
      "required": true,
      "description": "Repository URL to review"
    },
    {
      "name": "branch",
      "type": "string",
      "required": false,
      "default": "main"
    }
  ],
  "mission_config": {
    "goal_template": "Review code in {repo_url} on branch {branch}",
    "specialist": "analyst",
    "provider": "gpt-4o",
    "max_stages": 5,
    "timeout_minutes": 30
  },
  "created_at": "2026-03-28T00:00:00Z",
  "updated_at": "2026-03-28T00:00:00Z"
}
```

## API Contract

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/templates | List all templates |
| GET | /api/v1/templates/{id} | Get template detail |
| POST | /api/v1/templates | Create template (operator) |
| PUT | /api/v1/templates/{id} | Update template (operator) |
| DELETE | /api/v1/templates/{id} | Delete template (operator) |
| POST | /api/v1/templates/{id}/run | Run mission from template |

## Lifecycle

```
draft → published → archived
         ↓
       running (mission created)
```

- `draft`: editable, not runnable
- `published`: runnable, editable (creates new version)
- `archived`: not runnable, read-only

## Storage

File-based: `config/templates/{id}.json` (consistent with Vezir persistence model)

## Parameter Validation

- Required parameters must be provided at run time
- Type checking: string, number, boolean, array
- Default values applied for missing optional parameters
- Goal template string interpolation: `{param_name}` syntax
