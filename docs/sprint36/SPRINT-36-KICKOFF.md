# Sprint 36 Kickoff — Encrypted Secrets + Audit Integrity

**Phase:** 7 | **Model:** A | **Class:** product
**Output root:** evidence/sprint-36/
**Predecessor:** Sprint 35 `closure_status=closed` (STATE.md line 92, commits e013d47/4f62b5a)

---

## Goal

Continue P1 security hardening: encrypt secrets at rest and add audit log tamper resistance. Decision-first approach. No new API endpoints.

## Scope

**In scope:**
- D-129 freeze (secret storage + audit integrity contract)
- Encrypted secret storage implementation + tests
- Audit hash-chain append/verify CLI + tests
- Gates, retrospective, closure packet

**Out of scope:**
- Key rotation
- API endpoint for audit verification
- Plaintext backfill migration
- Non-CLI audit verification surface
- Transport encryption (B-011, deferred)

## Sequence

36.0 -> 36.1 -> G1 -> 36.2 -> G2 -> RETRO -> CLOSURE

## Tasks

### 36.0 Freeze D-129: Secret storage + audit integrity contract

- **Owner:** Claude Code
- **Secret storage contract:**
  - Encryption: AES-256-GCM (symmetric, authenticated)
  - Key: `VEZIR_SECRET_KEY` env var, base64-encoded 32-byte key
  - Key validation at startup: decode base64, verify length=32 bytes
  - Invalid/malformed key: startup warning + read-only mode (deny all writes)
  - Missing key: read-only mode (read legacy plaintext, deny new writes, log warning)
  - Legacy source: `config/secrets.json` (plaintext, current repo)
  - Encrypted target: `config/secrets.enc.json`
  - Read precedence: `config/secrets.enc.json` is authoritative when present. Fallback to `config/secrets.json` only when encrypted file is absent. If encrypted file exists but key is missing/invalid or decrypt fails: do NOT fall back to plaintext — return read failure, log error, remain read-only
  - Write semantics: temp + fsync + `os.replace()` (atomic per D-071), never partial overwrite
  - Migration: new writes encrypted only, legacy readable, no backfill in S36
  - Rotation: not in S36 scope (deferred)
  - Runtime ownership: `agent/services/secret_store.py` is the single owner. Key validation at module init. All secret reads/writes must route through `secret_store`. No direct production writes to `config/secrets.json` outside tests/fixtures
- **Audit integrity contract:**
  - Mechanism: SHA-256 hash chain
  - Verification surface: CLI only in S36 (`tools/verify-audit-chain.py`), no API endpoint
  - Hash payload: canonical JSON with sorted keys, UTF-8, `entry_hash` field excluded from hashed payload
  - Genesis `prev_hash`: SHA-256 of empty string (`e3b0c44298fc1c149afbf4c8996fb924...`)
  - Tamper detection output: `INTEGRITY_FAIL` + `broken_entry_index`
  - Intact chain output: `INTEGRITY_OK` + `entry_count`
  - Audit log path: `logs/audit/audit.jsonl` (append-only JSONL, one JSON object per line)
  - Entry schema: `{"timestamp", "event", "actor", "detail", "prev_hash", "entry_hash"}`
  - Single runtime append owner: `agent/persistence/audit_integrity.py:append_entry()`
  - CLI exit codes: exit 0 on `INTEGRITY_OK`, exit 1 on `INTEGRITY_FAIL` or malformed input
- **Acceptance:** `decisions/D-129-secret-audit-contract.md` committed on main
- **Verification:** `cat decisions/D-129-secret-audit-contract.md | head -20`
- **Artifacts:** `decisions/D-129-secret-audit-contract.md`

### 36.1 Encrypted secret storage (B-006, #151)

- **Owner:** Claude Code
- **Depends on:** 36.0 (D-129 frozen)
- **Produced files:**
  - `agent/services/secret_store.py` — encrypt/decrypt, read/write, key validation
  - `agent/tests/test_secret_store.py` — all acceptance criteria as tests
- **Acceptance criteria:**
  - Encrypted write goes only to `config/secrets.enc.json`
  - Plaintext legacy read from `config/secrets.json` works
  - Missing `VEZIR_SECRET_KEY` → read-only mode, writes denied, warning logged
  - Invalid base64 key → startup warning + read-only mode
  - Decoded key length != 32 → startup warning + read-only mode
  - Atomic write path: temp + fsync + `os.replace()`
  - Read precedence: encrypted authoritative, legacy fallback only when encrypted absent
  - Encrypted exists + key invalid/missing: read failure, NOT silent fallback to plaintext
- **Verification:** `cd agent && python -m pytest tests/test_secret_store.py -v 2>&1 | tail -5`
- **Failure-path verification:**
  - `python -m pytest tests/test_secret_store.py -v -k invalid_key 2>&1 | tail -3`
  - `python -m pytest tests/test_secret_store.py -v -k missing_key 2>&1 | tail -3`
- **Evidence:** `evidence/sprint-36/secret-tests-output.txt`

### G1 Mid Review Gate (after 36.1)

- **Inputs:** D-129 frozen, secret store tests pass
- **Pass criteria:** D-129 committed, `test_secret_store.py` all PASS, missing-key read-only verified, invalid-key read-only verified
- **Evidence:** `evidence/sprint-36/g1-review.md`

### 36.2 Audit log tamper resistance (B-008, #155)

- **Owner:** Claude Code
- **Depends on:** 36.0 (D-129 frozen); independent of 36.1
- **Produced files:**
  - `agent/persistence/audit_integrity.py` — hash chain append, verify
  - `tools/verify-audit-chain.py` — CLI verification tool
  - `agent/tests/test_audit_integrity.py` — all acceptance criteria as tests
- **Acceptance criteria:**
  - CLI verify returns `INTEGRITY_OK` + `entry_count` on intact chain
  - Tampered entry returns `INTEGRITY_FAIL` + `broken_entry_index`
  - Hash = SHA-256 of canonical sorted-key JSON, UTF-8, `entry_hash` excluded
  - Genesis `prev_hash` = SHA-256 of empty string
  - CLI exit 0 on INTEGRITY_OK, exit 1 on INTEGRITY_FAIL
  - Tests include exit-code verification, not only stdout text
- **Verification:** `cd agent && python -m pytest tests/test_audit_integrity.py -v 2>&1 | tail -5`
- **Failure-path verification:** `python -m pytest tests/test_audit_integrity.py -v -k tamper 2>&1 | tail -3`
- **Evidence:** `evidence/sprint-36/audit-tests-output.txt`

### G2 Final Review Gate (after 36.2)

- **Pass criteria:** all tests green, closure-check ELIGIBLE, D-129 frozen, B-006+B-008 closed
- **Verification:** `bash tools/sprint-closure-check.sh 36 2>&1 | tee evidence/sprint-36/closure-check-output.txt`
- **Evidence:** `docs/ai/reviews/S36-REVIEW.md`, `evidence/sprint-36/closure-check-output.txt`

### RETRO

- **Owner:** Claude Code
- **Produced:** `docs/sprint36/SPRINT-36-RETRO.md`
- **Acceptance:** Retro file committed with at least one actionable output (new decision, task patch, process gate patch, validator fix, or decision debt task)
- **Verification:** `cat docs/sprint36/SPRINT-36-RETRO.md | head -20`
- **Evidence:** `docs/sprint36/SPRINT-36-RETRO.md`

### CLOSURE

- **Owner:** Operator (GPT) — Claude Code prepares artifacts only
- **Claude Code actions:** update handoff, sync evidence references, set `implementation_status=done` and `closure_status=review_pending` in STATE.md
- **Operator action:** set `closure_status=closed` (operator-only per governance rules)
- **Verification:** `docs/ai/STATE.md` reflects `implementation_status=done` and `closure_status=review_pending` after evidence + review completion; operator sets closed separately
- **Evidence:** commit on main with handoff/state sync for review; operator closure commit/state transition handled separately

## Dependencies

- 36.1 depends on 36.0 (D-129)
- 36.2 depends on 36.0 (D-129 frozen); independent of 36.1 implementation

## Blocking Risks

- Startup mode regression if key validation order wrong → test missing/invalid key paths explicitly
- Legacy/encrypted precedence confusion → D-129 freezes read order: encrypted first, legacy fallback
- Canonical JSON drift in audit hash → D-129 freezes sorted keys + UTF-8 + excluded fields

## Exit Criteria

- D-129 frozen and committed
- `test_secret_store.py` all PASS (including failure paths)
- `test_audit_integrity.py` all PASS (including tamper detection)
- Evidence packet complete under `evidence/sprint-36/`
- `bash tools/sprint-closure-check.sh 36` returns `ELIGIBLE FOR CLOSURE REVIEW`

## Evidence Checklist

### Canonical product evidence (D-127 manifest)

Generated by `bash tools/generate-evidence-packet.sh 36 product`:

| File | Source |
|------|--------|
| `pytest-output.txt` | `cd agent && python -m pytest tests/ -v` |
| `vitest-output.txt` | `cd frontend && npx vitest run` |
| `tsc-output.txt` | `cd frontend && npx tsc --noEmit` |
| `lint-output.txt` | `cd frontend && npm run lint` |
| `build-output.txt` | `cd frontend && npm run build` |
| `validator-output.txt` | `python tools/project-validator.py` |
| `validator-tests.txt` | `python -m pytest tests/test_project_validator.py -v` |
| `playwright-output.txt` | `npx playwright test --reporter=list` |
| `e2e-output.txt` | Playwright raw output |
| `grep-evidence.txt` | Contract grep checks |
| `live-checks.txt` | curl health + SSE + host attack |
| `lighthouse.txt` | Accessibility/performance (or NO EVIDENCE if not applicable) |
| `mutation-drill.txt` | Mutation drill (or NO EVIDENCE if not applicable) |
| `contract-evidence.txt` | Contract evidence |
| `review-summary.md` | Copy of `docs/ai/reviews/S36-REVIEW.md` |
| `file-manifest.txt` | `ls -la evidence/sprint-36/` |
| `sprint-class.txt` | "product" |
| `closure-check-output.txt` | `bash tools/sprint-closure-check.sh 36` |

Missing raw output must be saved as NO EVIDENCE, not omitted.

### Sprint-specific evidence

- `secret-tests-output.txt` — `python -m pytest tests/test_secret_store.py -v`
- `audit-tests-output.txt` — `python -m pytest tests/test_audit_integrity.py -v`
- `g1-review.md` — G1 mid review artifact

## Implementation Notes

- **36.0 planned:** Freeze D-129; no code before decision commit on main.
- **36.1 planned:** Implement `agent/services/secret_store.py`, route all reads/writes through owner, add failure-path tests for invalid/missing key and encrypted-exists-but-undecryptable.
- **36.2 planned:** Implement hash-chain append/verify in `agent/persistence/audit_integrity.py` + CLI `tools/verify-audit-chain.py`, add exit-code tests.

## File Manifest

| Path | Action | Task | Reason |
|------|--------|------|--------|
| `decisions/D-129-secret-audit-contract.md` | create | 36.0 | Decision freeze |
| `agent/services/secret_store.py` | create | 36.1 | Encrypted secret storage |
| `agent/tests/test_secret_store.py` | create | 36.1 | Secret store tests |
| `agent/persistence/audit_integrity.py` | create | 36.2 | Hash chain append/verify |
| `tools/verify-audit-chain.py` | create | 36.2 | CLI verification |
| `agent/tests/test_audit_integrity.py` | create | 36.2 | Audit integrity tests |
| `docs/ai/reviews/S36-REVIEW.md` | create | G2 | Final review |
| `docs/sprint36/SPRINT-36-RETRO.md` | create | RETRO | Retrospective |

## State

- `implementation_status=not_started`
- `closure_status=not_started`

Operator review requested.
