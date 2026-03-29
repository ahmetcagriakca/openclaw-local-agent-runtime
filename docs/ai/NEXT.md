# Next Steps — Vezir Platform

**Last updated:** 2026-03-29
**Current:** Phase 7 active. Sprint 36 closed. Sprint 37 kickoff pending.

---

## Sprint 37 — Transport Encryption + Chatbridge Repair (KICKOFF PENDING)

**Model:** A (implementation) | **Class:** Product
**Scope:** TLS enforcement for API server (B-011), chatbridge selector repair
**Decision:** D-130 frozen (transport encryption contract)
**GPT verdict:** HOLD — awaiting fixes before PASS
**Kickoff doc:** `docs/sprint37/SPRINT-37-KICKOFF.md`

## Sprint 36 — Encrypted Secrets + Audit Integrity (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** AES-256-GCM secret store (B-006), SHA-256 hash chain audit (B-008)
**Decision:** D-129 frozen
**Review:** PASS — `docs/ai/reviews/S36-REVIEW.md`
**Tests:** +24 new (13 secret + 11 audit)

## Sprint 35 — Security Hardening Baseline (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** Task risk classification (B-003), filesystem confinement (B-004)
**Decision:** D-128 frozen
**Review:** PASS — `docs/ai/reviews/S35-REVIEW.md`

## Sprint 34 — Closure Tooling Hardening (CLOSED)

**Model:** A (implementation) | **Class:** Governance
**Scope:** Sprint closure class taxonomy, class-aware evidence manifests
**Decision:** D-127 frozen
**Review:** PASS — `docs/ai/reviews/S34-REVIEW.md`

## Sprint 33 — Project V2 Contract Hardening (CLOSED)

**Model:** A (implementation) | **Class:** Governance
**Scope:** Project V2 item contract, legacy normalization, closure state sync
**Decisions:** D-123, D-124, D-125 frozen
**Review:** PASS — `docs/ai/reviews/S33-REVIEW.md`

## Carry-Forward

| Item | Source | Status |
|------|--------|--------|
| Chatbridge selector drift | S34+ | In S37 scope |
| Telegram bridge fix | S33+ | Deferred |
| Transport encryption (B-011) | Backlog | In S37 scope |

## Decision Debt

- D-001→D-130: 130 frozen (D-126 skipped)
- D-111→D-114: missing formal record files under `docs/decisions/`
- D-021→D-058 extraction (AKCA-assigned, non-blocking)
