# D-134: Source User Identity Resolution Contract

**Phase:** Sprint 55
**Status:** Frozen
**Date:** 2026-04-04
**Author:** Claude Code (Opus)

---

## Context

Mission creation uses a hardcoded `sourceUserId`. As the platform moves toward multi-user support (D-117), the identity source must be dynamic and secure. The resolver must handle three tiers: authenticated sessions, explicit headers, and config fallback.

## Decision

Mission creation `sourceUserId` is resolved via 3-tier precedence:

1. **Authenticated session/token identity** — highest priority, always trusted
2. **`X-Source-User` request header** — accepted only from trusted origins (localhost/internal per D-070)
3. **`config.default_user` fallback** — lowest priority, backward compatible with current behavior

**Fail-closed:** If no source resolves, request is rejected with HTTP 401 Unauthorized.

## Trade-offs

| Option | Pros | Cons |
|--------|------|------|
| Auth-only (no header/fallback) | Simplest, most secure | Breaks backward compat, requires full auth deployment |
| Header-only | Easy integration | Spoofable from untrusted origins |
| **3-tier with trusted-origin gate** | Backward compat + secure + flexible | Slightly more complex resolver |

## Impacted Files/Components

- `agent/api/mission_create_api.py` — resolver chain implementation
- `agent/auth/session.py` — auth context provider
- `agent/tests/test_source_user.py` — contract tests

## Validation Method

- Unit tests for all 3 resolution tiers
- Fail-closed test: no resolution → 401
- Trusted origin validation test: header rejected from non-localhost
- Backward compatibility: existing tests pass with config fallback

## Rollback Condition

Revert to hardcoded `sourceUserId` if resolver introduces auth regression. Rollback = single file revert of `mission_create_api.py`.

## Related Decisions

- D-117: Multi-User Auth Contract (foundation)
- D-070: DNS rebinding protection (trusted origin gate)
- D-087: SSE Auth — Localhost-Only
