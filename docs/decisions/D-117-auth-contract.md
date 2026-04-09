# D-117: Multi-User Auth Implementation Contract

**Phase:** 6 (Sprint 27)
**Status:** Frozen
**Date:** 2026-03-28
**Supersedes:** D-108 (single-operator foundation)

---

## Decision

Token-based multi-user authentication with two roles: **operator** (full access) and **viewer** (read-only). API key authentication for MVP — no OAuth/SSO in this sprint.

## Auth Model

### Roles

| Role | Read | Mutations | Admin |
|------|------|-----------|-------|
| `viewer` | All GET endpoints | Denied (401) | No |
| `operator` | All GET endpoints | All POST/PUT/DELETE | No |
| (unauthenticated) | All GET endpoints | Denied (401) | No |

### Key Design Choices

1. **Read endpoints remain public** — no auth required for GET. Consistency with current behavior.
2. **API key auth** — `Authorization: Bearer <api-key>` header. Keys stored in `config/auth.json`.
3. **No user store/database** — file-based key registry (consistent with Vezir's file persistence model).
4. **Per-request session** — replace global Session singleton with request-scoped context.

### Auth Flow

```
Request → HostValidation → CSRF (POST) → AuthMiddleware → Handler
                                              ↓
                                    GET: pass through (no auth needed)
                                    POST/PUT/DELETE: require valid API key
                                              ↓
                                    Valid key → inject user context
                                    Invalid/missing → 401 Unauthorized
```

### Config File: `config/auth.json`

```json
{
  "keys": [
    {
      "key": "vz_...",
      "name": "akca-operator",
      "role": "operator",
      "created": "2026-03-28T00:00:00Z"
    },
    {
      "key": "vz_...",
      "name": "dashboard-viewer",
      "role": "viewer",
      "created": "2026-03-28T00:00:00Z"
    }
  ]
}
```

### Impacted Files

| File | Change |
|------|--------|
| `agent/auth/session.py` | Replace global singleton with request-scoped model |
| `agent/auth/middleware.py` | **NEW** — auth middleware (key validation, role check) |
| `agent/auth/keys.py` | **NEW** — key registry (load/validate from auth.json) |
| `agent/api/server.py` | Add auth middleware to chain |
| `agent/api/mission_mutation_api.py` | Add `Depends(require_operator)` |
| `agent/api/approval_mutation_api.py` | Add `Depends(require_operator)` |
| `agent/api/mission_create_api.py` | Add `Depends(require_operator)` |
| `agent/api/alerts_api.py` | Add `Depends(require_operator)` |
| `agent/api/signal_api.py` | Add `Depends(require_operator)` |
| `config/auth.json` | **NEW** — API key registry |
| `frontend/src/auth/` | **NEW** — login, context, route guard |

### Protected Endpoints (11 mutations)

All POST/PUT/DELETE endpoints require `operator` role:
- Mission: cancel, retry, pause, resume, skip-stage, create
- Approval: approve, reject
- Alerts: create rule, update rule
- Signal: delete

### Backward Compatibility

- GET endpoints: **no change** (remain public)
- POST endpoints without auth: **401** (breaking change for unauthenticated callers)
- Telegram bot: must include API key in requests
- `config/auth.json` absent: **all mutations denied** (fail-closed)

### Migration

1. Create `config/auth.json` with initial operator key
2. Add auth middleware to server
3. Update frontend to include API key in mutation requests
4. Update Telegram bot to include API key (if used)

### Security Properties

- Keys are stored in `config/auth.json` (gitignored)
- Keys prefixed with `vz_` for easy identification
- No key in response bodies
- Fail-closed: missing config = deny all mutations
- Audit trail: mutations log authenticated operator name

---

## Amendment: S84 — SSO/RBAC Extension (2026-04-09)

**Sprint:** 84 | **Status:** Frozen (amended)

### Extension Summary

D-117 extended to support OAuth2/OIDC SSO alongside existing API key auth:

1. **Third role: `admin`** — full permissions including user/role/system management
2. **OAuth2/OIDC provider** — GitHub OAuth + generic OIDC support
3. **JWT session tokens** — access (1h) + refresh (7d), HS256 signed
4. **Middleware dual-path** — validates both API keys (vz_ prefix) and JWT tokens
5. **Frontend auth guard** — ProtectedRoute with role-based access check

### Updated Role Matrix

| Role | Read | Mutations | Admin | SSO |
|------|------|-----------|-------|-----|
| `viewer` | All GET | Denied (403) | No | Yes |
| `operator` | All GET | All POST/PUT/DELETE | No | Yes |
| `admin` | All GET | All POST/PUT/DELETE | Yes (user/role/system) | Yes |
| (unauthenticated) | All GET | Denied (401) | No | — |

### Feature Flags

| Flag | Default | Effect |
|------|---------|--------|
| `VEZIR_AUTH_BYPASS=1` | unset | Bypass all auth (dev mode) |
| `VEZIR_SSO_ENABLED=0` | unset | Disable OAuth endpoints |

### New Files

| File | Purpose |
|------|---------|
| `agent/auth/oauth_provider.py` | OAuth2 provider abstraction |
| `agent/auth/jwt_tokens.py` | JWT token creation/validation |
| `agent/auth/rbac.py` | Role/permission matrix + mapping |
| `agent/api/auth_api.py` | 6 auth endpoints |
| `frontend/src/auth/ProtectedRoute.tsx` | Route guard |

### Backward Compatibility

- Existing API keys continue to work unchanged
- `VEZIR_AUTH_BYPASS=1` still bypasses all auth
- GET endpoints remain public (no auth required)
- Carry-forward items D-104/D-108 resolved by this amendment
