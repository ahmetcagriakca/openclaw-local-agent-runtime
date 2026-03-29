# Sprint 36 Kickoff — Encrypted Secrets + Audit Integrity

**Phase:** 7 | **Model:** A | **Class:** product
**Output root:** evidence/sprint-36/

---

## Goal

Continue P1 security hardening: encrypt secrets at rest and add audit log tamper resistance. Decision-first approach per established protocol.

## Sequence

36.0 -> 36.1 -> G1 -> 36.2 -> G2 -> RETRO -> CLOSURE

## Tasks

### 36.0 Freeze D-129: Secret storage + audit integrity contract

- **Secret storage contract:**
  - Encryption: AES-256-GCM (symmetric, authenticated)
  - Key source: `VEZIR_SECRET_KEY` environment variable (single source, no passphrase flow in S36)
  - Missing key at startup: read-only mode (can read unencrypted legacy, cannot write new secrets)
  - Storage location: `config/secrets.enc.json`
  - Migration: new writes encrypted, legacy plaintext readable, no backfill in S36
  - Rotation: not in S36 scope (deferred)
- **Audit integrity contract:**
  - Mechanism: SHA-256 hash chain (each entry includes hash of previous entry)
  - Tamper detection: verify chain integrity on demand
  - Missing/corrupted entry: chain broken = integrity FAIL
  - No HMAC (simpler, no key dependency between audit and secrets)
- **Owner:** Claude Code
- **Acceptance:** `cat decisions/D-129-secret-audit-contract.md | head -20`
- **Artifacts:** `decisions/D-129-secret-audit-contract.md`

### 36.1 Encrypted secret storage (B-006, #151)

- Implement per D-129 secret storage contract
- AES-256-GCM encryption/decryption
- Key from `VEZIR_SECRET_KEY` env var
- Missing key: read-only mode, log warning
- Store: `config/secrets.enc.json`
- Legacy plaintext readable, new writes encrypted
- **Owner:** Claude Code
- **Depends on:** 36.0 (D-129 frozen)
- **Acceptance:** `cd agent && python -m pytest tests/ -v -k secret 2>&1 | tail -3`
- **Verification:** `cd agent && python -m pytest tests/ -v -k secret 2>&1 | tail -5`
- **Evidence:** `evidence/sprint-36/secret-tests-output.txt`
- **Artifacts:** `agent/services/secret_store.py`, tests

### G1 Mid Review Gate (after 36.1)

- **Inputs:** D-129 frozen, secret store tests pass
- **Pass criteria:** D-129 committed, pytest -k secret all PASS, missing-key graceful degradation verified
- **Evidence:** `evidence/sprint-36/g1-review.md`

### 36.2 Audit log tamper resistance (B-008, #155)

- Implement per D-129 audit integrity contract
- SHA-256 hash chain on structured audit log entries
- Verify chain integrity on demand (CLI or API)
- Chain break detection with entry index
- **Owner:** Claude Code
- **Depends on:** None (independent of 36.1)
- **Acceptance:** `cd agent && python -m pytest tests/ -v -k audit_integrity 2>&1 | tail -3`
- **Verification:** `cd agent && python -m pytest tests/ -v -k audit_integrity 2>&1 | tail -5`
- **Evidence:** `evidence/sprint-36/audit-tests-output.txt`
- **Artifacts:** `agent/persistence/audit_integrity.py`, tests

### G2 Final Review Gate (after 36.2)

- **Pass criteria:** all tests green, closure-check ELIGIBLE, D-129 frozen, B-006+B-008 closed
- **Evidence:** `docs/ai/reviews/S36-REVIEW.md`

### RETRO + CLOSURE

Per sprint-end protocol.

## Dependencies

- 36.1 depends on 36.0 (D-129)
- 36.2 is independent

## Blocking Risks

None identified. Both tasks are internal security hardening.

## Exit Criteria

- D-129 frozen
- B-006 (encrypted secrets) + B-008 (audit integrity) closed with tests
- closure-check ELIGIBLE

## Evidence Checklist

`bash tools/generate-evidence-packet.sh 36 product`

Plus sprint-specific:
- `secret-tests-output.txt`
- `audit-tests-output.txt`
- `g1-review.md`

## Implementation Notes

(updated during sprint)

## File Manifest

(updated during sprint)

## State

- `implementation_status=not_started`
- `closure_status=not_started`

Operator review requested.
