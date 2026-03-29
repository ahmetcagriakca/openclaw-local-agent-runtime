# Sprint 37 Kickoff — Transport Encryption + Chatbridge Repair

**Phase:** 7 | **Model:** A | **Class:** product
**Output root:** evidence/sprint-37/
**Predecessor:** Sprint 36 `closure_status=closed` (STATE.md, commit 8be3368)

---

## Goal

Close the last P1 security item (B-011 transport encryption) and fix the chatbridge selector drift that has been blocking automated GPT communication since S34.

## Scope

**In scope:**
- D-130 freeze (transport encryption contract)
- TLS enforcement for API server
- Chatbridge sendButton selector fix
- Tests, gates, retrospective, closure packet

**Out of scope:**
- Certificate authority / Let's Encrypt integration
- Mutual TLS / client certificates
- Product features (B-101-B-104)
- Telegram bridge fix (separate blocker, deferred)

## Sequence

37.0 -> 37.1 -> G1 -> 37.2 -> G2 -> RETRO -> CLOSURE

## Tasks

### 37.0 Freeze D-130: Transport encryption contract

- **Owner:** Claude Code
- **Transport contract:**
  - API server (`127.0.0.1:8003`) supports TLS via self-signed cert for dev
  - TLS version: TLS 1.2+ only (reject < 1.2)
  - Cert/key source: `config/tls/server.pem` + `config/tls/server-key.pem`
  - Missing cert at startup: serve HTTP with warning log (graceful degradation, not hard fail)
  - Cert generation: `tools/generate-dev-cert.sh` creates self-signed cert
  - No production CA integration in S37 (deferred)
  - HSTS header when TLS active
- **Acceptance:** `decisions/D-130-transport-encryption.md` committed on main
- **Verification:** `cat decisions/D-130-transport-encryption.md | head -20`
- **Artifacts:** `decisions/D-130-transport-encryption.md`

### 37.1 Transport encryption (B-011, #152)

- **Owner:** Claude Code
- **Depends on:** 37.0 (D-130 frozen)
- **Produced files:**
  - `tools/generate-dev-cert.sh` — self-signed cert generator
  - `agent/api/server.py` updates — TLS support via uvicorn ssl params
  - `agent/tests/test_transport_encryption.py` — TLS tests
- **Acceptance criteria:**
  - Server starts with TLS when cert present
  - Server starts without TLS (HTTP) when cert absent, with warning
  - TLS 1.2+ enforced (reject SSLv3, TLS 1.0, TLS 1.1)
  - HSTS header present in HTTPS responses
  - Self-signed cert generation tool works
- **Verification:** `cd agent && python -m pytest tests/test_transport_encryption.py -v 2>&1 | tail -5`
- **Failure-path verification:** `python -m pytest tests/test_transport_encryption.py -v -k missing_cert 2>&1 | tail -3`
- **Evidence:** `evidence/sprint-37/transport-tests-output.txt`

### G1 Mid Review Gate (after 37.1)

- **Inputs:** D-130 frozen, transport tests pass
- **Pass criteria:** D-130 committed, `test_transport_encryption.py` all PASS, missing-cert degradation verified
- **Evidence:** `evidence/sprint-37/g1-review.md`

### 37.2 Chatbridge selector repair

- **Owner:** Claude Code
- **Depends on:** None (independent)
- **Produced files:**
  - `C:/Users/AKCA/chatbridge/lib/selectors.js` or equivalent config update
- **Acceptance criteria:**
  - `node C:/Users/AKCA/chatbridge/bridge.js --health gpt` returns healthy with all selectors valid
  - `node C:/Users/AKCA/chatbridge/bridge.js --target gpt --new-chat --message "ping"` sends and receives response
- **Verification:** `node C:/Users/AKCA/chatbridge/bridge.js --health gpt 2>&1 | head -3`
- **Evidence:** `evidence/sprint-37/chatbridge-health-output.txt`

### G2 Final Review Gate (after 37.2)

- **Pass criteria:** all tests green, closure-check ELIGIBLE, D-130 frozen, B-011 closed, chatbridge healthy
- **Verification:** `bash tools/sprint-closure-check.sh 37 2>&1 | tee evidence/sprint-37/closure-check-output.txt`
- **Evidence:** `docs/ai/reviews/S37-REVIEW.md`, `evidence/sprint-37/closure-check-output.txt`

### RETRO

- **Owner:** Claude Code
- **Produced:** `docs/sprint37/SPRINT-37-RETRO.md`
- **Acceptance:** Retro committed with at least one actionable output
- **Verification:** `cat docs/sprint37/SPRINT-37-RETRO.md | head -20`
- **Evidence:** `docs/sprint37/SPRINT-37-RETRO.md`

### CLOSURE

- **Owner:** Operator (GPT) — Claude Code prepares artifacts only
- **Claude Code actions:** update handoff, sync evidence, set `implementation_status=done` and `closure_status=review_pending`, close issues, close milestone, run board validator, regen backlog, push
- **Operator action:** set `closure_status=closed` (operator-only)
- **Verification:** STATE.md reflects `review_pending` after evidence completion
- **Evidence:** commit on main with full closure checklist executed

## Dependencies

- 37.1 depends on 37.0 (D-130 frozen)
- 37.2 is independent (can run in parallel with 37.1 after 37.0)

## Blocking Risks

- TLS cert generation may need platform-specific handling (OpenSSL on Windows)
- Chatbridge selector may require inspecting current ChatGPT DOM

## Exit Criteria

- D-130 frozen and committed
- `test_transport_encryption.py` all PASS
- Chatbridge health check: all selectors valid
- Evidence packet complete under `evidence/sprint-37/`
- `bash tools/sprint-closure-check.sh 37` returns `ELIGIBLE FOR CLOSURE REVIEW`
- Issues closed, milestone closed, board valid, backlog regenerated, all pushed

## Evidence Checklist

### Canonical product evidence (D-127 manifest)

`bash tools/generate-evidence-packet.sh 37 product`

All mandatory files per `tools/canonical-evidence-manifest-product.txt`.
Missing raw output saved as NO EVIDENCE, not omitted.

### Sprint-specific evidence

- `transport-tests-output.txt`
- `chatbridge-health-output.txt`
- `g1-review.md`
- `closure-check-output.txt`

## Implementation Notes

- **37.0 planned:** Freeze D-130; no code before decision commit.
- **37.1 planned:** Add TLS params to uvicorn startup, cert generator script, tests for TLS/no-TLS/HSTS.
- **37.2 planned:** Inspect ChatGPT DOM for current send button selector, update chatbridge config.

## File Manifest

| Path | Action | Task | Reason |
|------|--------|------|--------|
| `decisions/D-130-transport-encryption.md` | create | 37.0 | Decision freeze |
| `tools/generate-dev-cert.sh` | create | 37.1 | Self-signed cert generator |
| `agent/api/server.py` | modify | 37.1 | TLS support |
| `agent/tests/test_transport_encryption.py` | create | 37.1 | Transport tests |
| `chatbridge selectors config` | modify | 37.2 | Selector fix |
| `docs/ai/reviews/S37-REVIEW.md` | create | G2 | Final review |
| `docs/sprint37/SPRINT-37-RETRO.md` | create | RETRO | Retrospective |

## State

- `implementation_status=not_started`
- `closure_status=not_started`

Operator review requested.
