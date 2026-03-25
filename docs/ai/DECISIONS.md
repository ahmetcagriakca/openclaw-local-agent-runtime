# Architectural Decisions

**Last updated:** 2026-03-25

All decisions below are frozen unless marked otherwise. Reopening requires explicit phase gate approval + operator sign-off.

---

## Phase 1 / 1.5 Decisions (D-001 → D-020)

---

## D-001: Single Execution Owner = oc runtime

**Phase:** 1.5-A | **Status:** Frozen

oc runtime is the only component that may queue, execute, retry, cancel, or report health on tasks.

---

## D-002: Terminology — orchestration vs conversation flow

**Phase:** 1.5-A | **Status:** Frozen

"Orchestration" = task execution orchestration, sole owner: oc runtime. OpenClaw = conversation flow, intent extraction, approval UX, result narration. Bridge = adapter / trust boundary, never an orchestrator.

---

## D-003: Worker model — ephemeral -RunOnce

**Phase:** 1.5-A | **Status:** Frozen

Each invocation claims pending tickets, processes them, exits. Persistent poll loop superseded.

---

## D-004: Bridge = stateless translation + auth gate

**Phase:** 1.5-A | **Status:** Frozen

No persistent state. One request = one API call = one response. Exception: terminal polling may use two sequential calls (get + output).

---

## D-005: External surface is task-centric

**Phase:** 1.5-A | **Status:** Frozen

Bridge contract uses task names and task IDs. No intent vocabulary at Bridge boundary.

---

## D-006: Raw action invocation forbidden externally

**Phase:** 1.5-A | **Status:** Frozen

oc-run-action.ps1 forbidden as external integration path. Runner is the only legitimate caller.

---

## D-007: Polling-only for Phase 1.5

**Phase:** 1.5-A | **Status:** Frozen

No callbacks, notifications, or webhooks. OpenClaw owns poll timing.

---

## D-008: Stuck task policy — fail-closed + dead-letter + no auto-retry

**Phase:** 1.5-A | **Status:** Frozen

Stuck tasks fail, write lastError, move to dead-letter. No auto-retry anywhere.

---

## D-009: Duplicate task creation accepted in Phase 1.5

**Phase:** 1.5-A | **Status:** Frozen

requestId is audit/correlation only, not dedupe.

---

## D-010: Retry not exposed externally in Phase 1.5

**Phase:** 1.5-C | **Status:** Frozen

retry_task is operator-only. User retry = new submit_task.

---

## D-011: External Bridge operations (Phase 1.5)

**Phase:** 1.5-C | **Status:** Frozen

Four operations: submit_task, get_task_status, cancel_task, get_health.

---

## D-012: Approval model — definition-level preapproval

**Phase:** 1.5-C | **Status:** Frozen

Runtime enforces approvalPolicy at task definition level. No policyContext. Bridge transports approvalStatus for audit only. Pending = rejected by Bridge.

---

## D-013: Allowlist fail-closed startup

**Phase:** 1.5-D | **Status:** Frozen

Missing/empty/unparseable allowlist = Bridge refuses to start (exit 2).

---

## D-014: Five-step validation order

**Phase:** 1.5-D | **Status:** Frozen

Structural → Operation → Allowlist → Field-level → Approval pre-validation. First failure stops.

---

## D-015: Operator exception — local/manual/admin-only

**Phase:** 1.5-A | **Status:** Frozen

Not part of Bridge external contract. Must not become shadow integration path.

---

## D-016: Health response sanitized

**Phase:** 1.5-D | **Status:** Frozen

Only health field (ok/degraded/error) plus wrapper fields. All runtime internals stripped.

---

## D-017: Minimum audit — 10 fields per request

**Phase:** 1.5-D | **Status:** Frozen

timestamp, requestId, source, sourceUserId, operation, taskName, approvalStatus, outcome, errorCode, runtimeTaskId.

---

## D-018: Bridge physical form — stateless single-invocation script

**Phase:** 1.5-E | **Status:** Frozen

bridge/oc-bridge.ps1, invoked once per request, produces response, exits.

---

## D-019: Canonical caller path — OpenClaw via WSL wrappers

**Phase:** TG-1R | **Status:** Frozen

OpenClaw Telegram → WSL wrappers → oc-bridge-call → pwsh.exe bridge/oc-bridge.ps1 → runtime.

---

## D-020: Project identity

**Phase:** Post-1.5 | **Status:** Active

Project: OpenClaw Local Agent Runtime. Repo: openclaw-local-agent-runtime.

---

## Phase 4 Decisions (D-021 → D-058)

> **GAP:** D-021→D-058 (38 karar) Phase 4 Agent System sprint'lerinde (6A–6D) alındı.
> Bu kararlar repo'daki CLAUDE.md ve session notlarında referans ediliyor ancak
> DECISIONS.md'ye henüz eklenmemiş.
>
> **Kapsam:** 9 governed roles, 10 skill contracts, 3 quality gates, 2 feedback loops,
> 10-state mission state machine, artifact extraction, approval service.
>
> **Aksiyon:** Repo'daki Phase 4 session handoff veya CLAUDE.md'den D-021→D-058
> detayları çıkarılıp bu dosyaya eklenecek. Ayrı task olarak planlanmış.
>
> **Owner:** AKCA
> **Deadline:** Sprint 8 kickoff öncesi

---

## Phase 5 Decisions (D-059 → D-076)

---

## D-059: Read-only first, Controller sole executor

**Phase:** 5 (design) | **Status:** Frozen

Phase 5A–5B read-only. Mission Controller remains the sole executor — UI observes, never mutates mission state directly. Mutation (intervention, approval) gated behind feature flags in Phase 5C.

---

## D-060: Polling → SSE, No WebSocket

**Phase:** 5B (Sprint 10) | **Status:** Frozen

Frontend starts with 2s polling (Sprint 9), upgrades to SSE (Sprint 10). WebSocket explicitly rejected — SSE is simpler, sufficient for one-directional server→client push, and natively supports Last-Event-ID replay.

---

## D-061: FastAPI from day 1

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

FastAPI + Uvicorn for all phases. No Flask, no custom HTTP. Decision is irreversible — all API work builds on this stack.

Trade-off: Heavier initial setup vs. consistent foundation. async-native from start.

---

## D-062: Intervention via atomic file signal

**Phase:** 5C (Sprint 11) | **Status:** Frozen

UI writes intervention request as atomic JSON file. Controller polls for intervention signals between stages. No direct process communication.

Trade-off: Higher latency (poll interval) vs. crash-safe, no IPC complexity.

---

## D-063: Approval via service layer

**Phase:** 5C (Sprint 11) | **Status:** Frozen

Current strict-ID approval service sunsets in Phase 5C. New approval flow: UI → API → ApprovalService → atomic file → Controller reads. Structured request/response contract.

Trade-off: Migration effort vs. clean contract for future multi-approver support.

---

## D-064: Port assignment — API 8003, React 3000

**Phase:** 5A (Sprint 8) | **Status:** Frozen

Mission Control API on port 8003, React dev server on 3000. Env override supported. No conflict with existing WMCP (8001) and legacy dashboard (8002).

---

## D-065: Normalized API — MissionNormalizer

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

API does not expose raw files. MissionNormalizer reads multiple sources (state.json, mission JSON, telemetry JSONL, summary), applies precedence rules, caches result, returns normalized response.

Precedence: state > mission (for status), summary > telemetry (for forensics).

---

## D-066: Legacy dashboard lives until 5D

**Phase:** 5D (Sprint 12) | **Status:** Frozen

Legacy health dashboard on port 8002 runs in parallel until Sprint 12 evaluation. No premature removal.

---

## D-067: Schema frozen after 5A-1, additive-only

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

API response schemas freeze at Sprint 8 exit. Post-freeze: additive fields only, no removal, no type change. Versioned as /api/v1/.

---

## D-068: Unknown ≠ zero, 6 data states

**Phase:** 5A–5B (Sprint 8–9) | **Status:** Frozen

Every response has a DataQuality indicator with one of 6 states: fresh, partial, stale, degraded, unknown, not_reached. UI must distinguish all six. Rendering unknown as zero, empty, pass, or green is forbidden.

Priority when multiple conditions: degraded > stale > partial > fresh.

Impacted: All API responses, all UI components, all normalizer logic.

---

## D-069: No control without acknowledgement

**Phase:** 5C (Sprint 11) | **Status:** Frozen

Every mutation request follows lifecycle: requested → accepted → applied | rejected | timed_out. No fire-and-forget commands.

---

## D-070: DNS rebinding protection

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

FastAPI validates Host header. Explicit CORS config. Server binds to 127.0.0.1 only. Rejects requests with unexpected Host or Origin headers.

---

## D-071: Atomic file writes system-wide

**Phase:** 4.5-C → 5 (Sprint 7+) | **Status:** Frozen

All JSON file writes use atomic pattern: write to temp file → fsync → os.replace(). No partial writes. Applied to capabilities.json, state files, intervention signals, all API-written files.

---

## D-072: Per-source circuit breaker + per-panel error boundary

**Phase:** 5A (Sprint 8–9) | **Status:** Frozen

Backend: per-source circuit breaker (state file, mission file, telemetry). If one source fails, others still serve. Frontend: per-panel React error boundary — one panel crash doesn't take down the page.

---

## D-073: Log rotation — 10MB / 5 files / 14 days

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

API logs: 10MB max per file, keep 5 rotated files, 14-day retention. Consistent with existing runtime log rotation policy.

---

## D-074: Startup sequence + ownership matrix

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

Explicit startup order: config load → file system validation → cache warm → normalizer init → API serve. Each subsystem has a single owner — no shared writes to the same file.

---

## D-075: All state on ext4, cross-OS via API

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

All persistent state files live on ext4 (WSL2 filesystem). Windows access exclusively through API (port 8003). No direct NTFS↔ext4 file sharing for state. File owner/target FS matrix tracked and reviewed at Sprint 8 kickoff.

---

## D-076: SSE event ID = {source}:{offset}

**Phase:** 5B (Sprint 10) | **Status:** Frozen

Event ID format: {source_file}:{byte_offset} (JSONL) or {source_file}:{mtime_ms} (JSON). Restart-safe via Last-Event-ID. Monotonic. Dedupe by same source:offset → skip.

Example: `policy-telemetry.jsonl:48231`, `mission-abc123.json:1711288380`

---

## Phase 4.5-C / Sprint 7 Decisions (D-077, D-078)

---

## D-077: Sprint-End Documentation Policy

**Phase:** 4.5-C (Sprint 7) | **Status:** Frozen

Context: Sprint kapanışlarında döküman güncellemeleri atlanıyor veya tutarsız yapılıyor. SESSION-HANDOFF, STATE.md, DECISIONS.md gibi dosyalar stale kalıyor.

Decision: Her sprint kapanışında zorunlu döküman güncellemesi. `tools/validate_sprint_docs.py` script'i ile enforce edilir. Validation pass olmadan sprint "done" sayılmaz.

Zorunlu dökümanlar: STATE.md, NEXT.md, DECISIONS.md, BACKLOG.md, SESSION-HANDOFF.md, capabilities.json, sprint plan doc. Koşullu: phase report, ops docs.

Validation kontrolleri: freshness (stale tarih), required sections, capability autoGenerated flag, open checkboxes, test count regression.

Trade-off: Sprint kapanış süresi artar (~15 dk) vs. döküman tutarlılığı ve session handoff kalitesi garanti altına alınır.

Enforce: `python tools/validate_sprint_docs.py --sprint N` → exit 0 gerekli.

Rollback: Script devre dışı bırakılabilir ama policy kuralları elle uygulanmaya devam eder.

---

## D-078: Sprint 7 E2E Partial Pass Waiver

**Phase:** 4.5-C → 5A-1 | **Status:** Frozen

Context: Sprint 7 E2E 2/4 pass. T-OT-3: LLM kalitesi (Sprint 7 scope dışı). T-OT-4: `_save_mission()` non-atomic write crash (pre-existing bug, Sprint 8 BF olarak planlandı).

Decision: Sprint 7 E2E partial pass kabul edilir. Sprint 7 code değişiklikleri (denyForensics, agentUsed, gateResults) başarılı mission'larda doğrulandı. Her iki fail Sprint 7 scope'u dışında.

Trade-off: E2E %50 ile Sprint 8'e geçiş. Risk kabul edilir çünkü fail root cause'ları Sprint 7 code'unda değil.

Rollback: Fail root cause'u Sprint 7'de olduğu kanıtlanırsa Sprint 8 durdurulur.

---

## Phase 5 Freeze Addendum (Sprint 7→8 arası)

> 4 blocking fix'in yazılı closure'ı `docs/ai/PHASE-5-FREEZE-ADDENDUM.md` dosyasında.
> Sprint 8 bu belge FROZEN olmadan başlamaz.
>
> | BF | Konu | Referans |
> |---|------|----------|
> | BF-1 | Response freshness semantics | Freeze Addendum Section 1 |
> | BF-2 | Startup ownership matrix | Freeze Addendum Section 2 |
> | BF-3 | Migration boundary inventory (D-075) | Freeze Addendum Section 3 |
> | BF-4 | Source precedence table (D-065) | Freeze Addendum Section 4 |
