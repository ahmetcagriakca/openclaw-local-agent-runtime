# Sprint 36 Kickoff — Encrypted Secrets + Audit Integrity

**Phase:** 7 | **Model:** A | **Class:** product
**Output root:** evidence/sprint-36/
**Predecessor:** Sprint 35 `closure_status=closed` (STATE.md line 92, commits e013d47/4f62b5a)

---

## Goal

Continue P1 security hardening: encrypt secrets at rest and add audit log tamper resistance. Decision-first approach. No new API endpoints.

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
  - Read precedence: try encrypted first, fall back to plaintext legacy
  - Write semantics: temp + fsync + `os.replace()` (atomic per D-071), never partial overwrite
  - Migration: new writes encrypted only, legacy readable, no backfill in S36
  - Rotation: not in S36 scope (deferred)
- **Audit integrity contract:**
  - Mechanism: SHA-256 hash chain
  - Verification surface: CLI only in S36 (`tools/verify-audit-chain.py`), no API endpoint
  - Hash payload: canonical JSON with sorted keys, UTF-8, `entry_hash` field excluded from hashed payload
  - Genesis `prev_hash`: SHA-256 of empty string (`e3b0c44298fc1c149afbf4c8996fb924...`)
  - Tamper detection output: `INTEGRITY_FAIL` + `broken_entry_index`
  - Intact chain output: `INTEGRITY_OK` + `entry_count`
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
  - Read precedence: encrypted first, legacy fallback
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
- **Depends on:** None (independent of 36.1)
- **Produced files:**
  - `agent/persistence/audit_integrity.py` — hash chain append, verify
  - `tools/verify-audit-chain.py` — CLI verification tool
  - `agent/tests/test_audit_integrity.py` — all acceptance criteria as tests
- **Acceptance criteria:**
  - CLI verify returns `INTEGRITY_OK` + `entry_count` on intact chain
  - Tampered entry returns `INTEGRITY_FAIL` + `broken_entry_index`
  - Hash = SHA-256 of canonical sorted-key JSON, UTF-8, `entry_hash` excluded
  - Genesis `prev_hash` = SHA-256 of empty string
- **Verification:** `cd agent && python -m pytest tests/test_audit_integrity.py -v 2>&1 | tail -5`
- **Failure-path verification:** `python -m pytest tests/test_audit_integrity.py -v -k tamper 2>&1 | tail -3`
- **Evidence:** `evidence/sprint-36/audit-tests-output.txt`

### G2 Final Review Gate (after 36.2)

- **Pass criteria:** all tests green, closure-check ELIGIBLE, D-129 frozen, B-006+B-008 closed
- **Verification:** `bash tools/sprint-closure-check.sh 36 2>&1 | tee evidence/sprint-36/closure-check-output.txt`
- **Evidence:** `docs/ai/reviews/S36-REVIEW.md`, `evidence/sprint-36/closure-check-output.txt`

### RETRO + CLOSURE

Per sprint-end protocol.

## Dependencies

- 36.1 depends on 36.0 (D-129)
- 36.2 is independent

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

`bash tools/generate-evidence-packet.sh 36 product`

Plus sprint-specific:
- `secret-tests-output.txt`
- `audit-tests-output.txt`
- `g1-review.md`
- `closure-check-output.txt`

## Implementation Notes

(updated during sprint)

## File Manifest

(updated during sprint)

## State

- `implementation_status=not_started`
- `closure_status=not_started`

Operator review requested.
