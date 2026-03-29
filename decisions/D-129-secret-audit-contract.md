# D-129: Secret Storage + Audit Integrity Contract

**ID:** D-129
**Status:** Frozen
**Phase:** 7 / Sprint 36
**Date:** 2026-03-29

---

## Secret Storage Contract

### Encryption
- Algorithm: AES-256-GCM (symmetric, authenticated encryption)
- Key source: `VEZIR_SECRET_KEY` environment variable
- Key format: base64-encoded 32-byte key
- Key validation at startup: decode base64, verify decoded length = 32 bytes

### Key Failure Behavior
- Missing `VEZIR_SECRET_KEY`: startup warning + read-only mode (deny all writes)
- Invalid base64: startup warning + read-only mode
- Decoded length != 32: startup warning + read-only mode
- Read-only mode: can read legacy plaintext if no encrypted file exists, cannot write new secrets

### Storage Paths
- Legacy plaintext source: `config/secrets.json`
- Encrypted target: `config/secrets.enc.json`

### Read Precedence
- `config/secrets.enc.json` is **authoritative** when present
- Fallback to `config/secrets.json` **only** when encrypted file is absent
- If encrypted file exists but key is missing/invalid or decrypt/auth-tag fails: do NOT fall back to plaintext — return read failure, log error, remain read-only

### Write Semantics
- Atomic write: temp file + fsync + `os.replace()` (per D-071)
- Never partial overwrite
- New writes go to `config/secrets.enc.json` only
- No writes to `config/secrets.json` in production

### Runtime Ownership
- `agent/services/secret_store.py` is the **single owner**
- Key validation happens at module init
- All secret reads/writes MUST route through `secret_store`
- No direct production writes to `config/secrets.json` outside tests/fixtures

### Migration
- New writes: encrypted only
- Legacy plaintext: readable (fallback when encrypted absent)
- No backfill in Sprint 36
- Rotation: not in Sprint 36 scope (deferred)

---

## Audit Integrity Contract

### Mechanism
- SHA-256 hash chain
- Each entry includes hash of previous entry (`prev_hash`)
- Entry's own hash (`entry_hash`) computed from payload + `prev_hash`

### Hash Computation
- Payload: canonical JSON with **sorted keys**, UTF-8 encoding
- `entry_hash` field is **excluded** from the hashed payload
- Hash input = `prev_hash` + canonical JSON of entry (without `entry_hash`)
- Hash algorithm: SHA-256, hex-encoded output

### Genesis
- First entry `prev_hash` = SHA-256 of empty string = `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

### Audit Log Format
- Path: `logs/audit/audit.jsonl` (append-only JSONL, one JSON object per line)
- Entry schema: `{"timestamp", "event", "actor", "detail", "prev_hash", "entry_hash"}`

### Runtime Ownership
- Single append owner: `agent/persistence/audit_integrity.py:append_entry()`
- No other component may write to the audit log directly

### Verification Surface
- CLI only in Sprint 36: `tools/verify-audit-chain.py`
- No API endpoint for verification in Sprint 36

### Output Contract
- Intact chain: `INTEGRITY_OK` + `entry_count` (stdout), exit code 0
- Tampered/broken chain: `INTEGRITY_FAIL` + `broken_entry_index` (stdout), exit code 1
- Malformed input: `INTEGRITY_FAIL` + error description (stdout), exit code 1

---

## Consequences

- Secrets are encrypted at rest with authenticated encryption
- Missing/invalid key degrades gracefully to read-only (no silent data loss)
- Audit log integrity is verifiable on demand
- Hash chain detects insertion, deletion, and modification of entries
- Both systems have single-owner runtime paths preventing bypass
