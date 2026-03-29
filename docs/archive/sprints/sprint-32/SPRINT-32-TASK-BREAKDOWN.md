# Sprint 32 — Task Breakdown

**Sprint:** 32
**Phase:** 7
**Title:** API Throttling + Mutation Idempotency
**Model:** A

**Goal:** Harden API security with per-endpoint throttling (B-005) and full mutation idempotency keys (B-012).

---

## Track 1

**32.1 — API per-endpoint throttling (B-005)**

Add request throttling to prevent abuse and burst pressure.

**Repo scope:** `agent/api/`
**Branch:** `sprint-32/t32.1-throttling`
**Backlog ref:** #154

**Contract:**
- Scope: all API endpoints (GET + POST)
- Limit dimensions: per-IP, configurable per route
- Default: 100 req/min for GET, 20 req/min for POST mutations
- Storage: in-memory (process-local, reset on restart)
- Response: HTTP 429 with `Retry-After` header
- Exclusions: health endpoint exempt

**Implementation:**
1. Create `agent/api/throttle.py` — sliding window counter middleware
2. Configure limits per route in middleware setup
3. Return 429 + Retry-After header on limit breach
4. Health endpoint excluded
5. Add throttle tests

**Acceptance:**
1. Burst requests beyond limit get 429
2. Retry-After header present in 429 response
3. Health endpoint always accessible
4. Tests pass

**Verification:**
```bash
cd agent && python -m pytest tests/test_throttle.py -v
```

---

**32.2 — Mutation idempotency keys (B-012)**

Add idempotency key support for all mutation endpoints to prevent duplicate execution.

**Repo scope:** `agent/api/`
**Branch:** `sprint-32/t32.2-idempotency`
**Backlog ref:** #153

**Contract:**
- Applies to: all POST/PUT/DELETE mutation endpoints only
- Key transport: `Idempotency-Key` request header
- Key scope: per API key (if auth enabled) or per IP
- Duplicate request with same key: return cached response (no re-execution)
- Key mismatch (same key, different body): 422 error
- TTL: 24 hours, in-memory store
- No key provided: request executes normally (backward compatible)

**Implementation:**
1. Create `agent/api/idempotency.py` — key store + middleware
2. On mutation request with Idempotency-Key: check store, return cached or execute + cache
3. On duplicate key with different body: 422 Unprocessable
4. TTL cleanup: purge keys older than 24h
5. Add idempotency tests

**Acceptance:**
1. Same key + same request = cached response (no re-execution)
2. Same key + different body = 422
3. No key = normal execution (backward compatible)
4. Expired key = treat as new request
5. Tests pass

**Verification:**
```bash
cd agent && python -m pytest tests/test_idempotency.py -v
```

---

## Gates

**32.G1 — Mid Review Gate** (after 32.1)
**32.G2 — Final Review Gate** (after 32.2)
**32.RETRO — Retrospective**
**32.CLOSURE — Sprint Closure**

---

## Anti-Scope-Creep

- No UI work
- No policy engine refactor
- No GET/read-only idempotency
- No distributed workflow redesign
