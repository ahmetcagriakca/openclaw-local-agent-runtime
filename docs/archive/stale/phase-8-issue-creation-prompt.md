# Phase 8 Backlog — GitHub Issue Creation

Phase 8 backlog v3 GPT review PASS aldı. Tüm backlog item'ları GitHub issue olarak oluştur.

## Kurallar

1. Her issue `[B-NNN] Title` formatında olsun
2. Label: `backlog` + domain label (`governance`, `architecture`, `security`, `devex`, `operations`)
3. Priority label: `priority:P0`, `priority:P1`, `priority:P2`, `priority:P3`
4. Her issue body'de: Problem, Aksiyon, Acceptance Criteria, Evidence Checklist, Sprint hedefi
5. Issue oluşturduktan sonra BACKLOG.md'yi `python tools/generate-backlog.py` ile regenerate et
6. Commit: "Phase 8: Create backlog issues B-134..B-147"

## Issue Listesi

### Issue 1: [B-134] Approval FSM Controller Wiring
- **Labels:** `backlog`, `governance`, `priority:P0`
- **Sprint target:** S62
- **Body:**

```
## Problem
D-138 approval timeout=deny + escalation FSM frozen (S61) ama controller.py enforce etmiyor.
WAITING_APPROVAL state'te expire/deny → FAILED transition yok. Fail-closed ihlali.

## Aksiyon
- Controller stage loop'a approval state poll: `_check_approval_state()`
- Expire → FAILED (reason: "approval_expired")
- Deny → FAILED (reason: "approval_denied")  
- Approve → RUNNING (reason: "approval_granted")
- Escalation: no mission FSM transition — approval-layer only (approval_record.status → ESCALATED)
- EventBus: APPROVAL_EXPIRED, APPROVAL_DENIED, APPROVAL_ESCALATED events
- Frontend: ESCALATED badge in approval inbox

## Acceptance Criteria
- [ ] Expire → FAILED tested with event + audit trail
- [ ] Deny → FAILED tested with event + audit trail
- [ ] Approve → RUNNING tested
- [ ] Escalation: mission stays WAITING_APPROVAL, approval_record.status = ESCALATED, event emitted
- [ ] No FSM self-transition on escalation
- [ ] Expired approval reuse → 409
- [ ] Audit trail: actor + timestamp for every approval state change
- [ ] Frontend ESCALATED badge visible

## Evidence
pytest-output.txt, vitest-output.txt, tsc-output.txt, lint-output.txt, closure-check-output.txt, grep-evidence.txt

## References
- D-138 (Approval Timeout + Escalation FSM)
- D-121 (Approval Gate Contract)
- S61 retro carry-forward
```

### Issue 2: [B-135] Decision Drift Full Scan + Cleanup
- **Labels:** `backlog`, `governance`, `priority:P1`
- **Sprint target:** S62
- **Body:**

```
## Problem
Decision drift tespiti fixed-list ile yapılıyor. Script-based tam audit gerekli.
D-098 ve D-082 stale — repo gerçekliğini yansıtmıyor.

## Aksiyon
- `tools/verify-decision-drift.py` script oluştur
  - DECISIONS.md parse → her decision status + referenced files
  - Referenced file yoksa veya content uyuşmazsa → DRIFT flag
  - CI/workflow cross-check
  - Exit non-zero on drift
- D-098: status → superseded (Playwright E2E implemented S39)
- D-082: status → superseded (openapi-typescript replaced manual types S48+)
- Output: drift-report.md

## Acceptance Criteria
- [ ] Script exit 0 after cleanup
- [ ] drift-report.md committed
- [ ] D-098, D-082 status updated in DECISIONS.md
- [ ] Script reusable for future drift scans

## Evidence
drift-report.md, pytest-output.txt (script test), lint-output.txt
```

### Issue 3: [B-136] Auth Session Quarantine + Actor Chain Verification
- **Labels:** `backlog`, `governance`, `security`, `priority:P1`
- **Sprint target:** S62
- **Body:**

```
## Problem
session.py global singleton — API katmanı kullanmıyor (dead code) ama quarantine edilmeli.
Actor chain continuity (auth → audit → policy) verification eksik.

## Aksiyon
- session.py → DEPRECATED docstring banner
- get_session() → deprecation warning log
- Actor chain verification:
  - All mutation endpoints: require_operator dependency
  - Audit trail: decided_by, source_user present
  - D-134 precedence: auth > header > config fallback tested
  - Policy context actor propagation tested

## Acceptance Criteria
- [ ] grep evidence: all mutation endpoints use require_operator
- [ ] Actor context in audit trail for every mutation
- [ ] D-134 3-tier precedence tests exist and pass
- [ ] session.py DEPRECATED marker added
- [ ] 0 new callers of get_session() in agent/api/

## Evidence
grep-evidence.txt, pytest-output.txt, lint-output.txt, file-manifest.txt
```

### Issue 4: [B-137] Controller Decomposition Boundary Freeze
- **Labels:** `backlog`, `architecture`, `priority:P1`
- **Sprint target:** S63
- **Body:**

```
## Problem
controller.py: 2082 satır, 25 metod, 13+ sorumluluk. Change blast radius çok yüksek.
Extraction öncesi boundary freeze gerekli.

## Aksiyon
- D-139 freeze: Controller Decomposition Boundary
- Boundary haritası:
  - Orchestration core (kalır): state transitions, stage dispatch, gate invocation
  - MissionPersistenceAdapter: save/load, atomic write
  - StageRecoveryEngine: retry, DLQ, circuit breaker, backoff, poison pill
  - ApprovalStateManager: approval lifecycle, timeout enforcement
  - MissionSummaryPublisher: event emission, SSE, token reporting
  - SignalAdapter: pause/resume/cancel
- Current method → future service mapping table
- Design-only, no code change

## Acceptance Criteria
- [ ] D-139 frozen with boundary diagram
- [ ] responsibility-map.md committed
- [ ] Method → service mapping table committed
- [ ] No code change

## Evidence
D-139 decision record, responsibility-map.md, review-summary.md
```

### Issue 5: [B-138] Budget Enforcement Ownership Design
- **Labels:** `backlog`, `architecture`, `governance`, `priority:P1`
- **Sprint target:** S63
- **Body:**

```
## Problem
Per-mission cost budget D-133 policy engine'de rule olarak tanımlı ama enforcement ownership belirsiz.

## Aksiyon
- Owner decision: policy engine evaluates, controller tracks tokens
- Budget data flow: controller tracks → policy engine evaluates → deny/allow
- Document in D-139 boundary map
- Design-only, no implementation

## Acceptance Criteria
- [ ] Budget enforcement ownership documented in D-139
- [ ] Data flow diagram committed
- [ ] No implementation

## Evidence
D-139 boundary map update, review-summary.md
```

### Issue 6: [B-139] Controller Extraction — Phase 1
- **Labels:** `backlog`, `architecture`, `priority:P1`
- **Sprint target:** S64
- **Body:**

```
## Problem
Controller hotspot — D-139 boundary'lerine göre ilk extraction.

## Aksiyon
- Extract MissionPersistenceAdapter (save/load, atomic write)
- Extract StageRecoveryEngine (retry, DLQ, circuit breaker, backoff)
- Controller delegation: service interface üzerinden çağrı
- Behavioral refactor — semantic change yok

## Acceptance Criteria
- [ ] Tüm mevcut testler green (behavioral refactor)
- [ ] No contract drift — API response değişmez
- [ ] Controller LOC azalma ölçülür (metrik, hedef değil)
- [ ] Diff evidence: extracted methods → new service
- [ ] Controller testleri orchestration-only scope'a daralmış

## Evidence
pytest-output.txt, tsc-output.txt, lint-output.txt, closure-check-output.txt, diff-evidence.txt, review-summary.md, file-manifest.txt

## Dependencies
- D-139 (controller boundary freeze)
```

### Issue 7: [B-140] Hard Per-Mission Budget Enforcement
- **Labels:** `backlog`, `governance`, `priority:P0`
- **Sprint target:** S64
- **Body:**

```
## Problem
Token budget visibility var ama runtime enforcement yok. Dashboard görür, runtime engelleyemez.

## Aksiyon
- Controller: _update_mission_budget() — cumulative token count
- Policy engine rule: config/policies/budget-enforcement.yaml
- 80% → alert (Telegram)
- 100% → deny new stages → FAILED "budget_exceeded"
- Per-mission max_token_budget (optional, default: no limit)

## Acceptance Criteria
- [ ] Budget accumulation tested across stages
- [ ] 80% alert tested
- [ ] 100% deny → FAILED tested
- [ ] No limit = no enforcement (backward compat)
- [ ] Policy rule loaded and evaluated correctly

## Evidence
pytest-output.txt, lint-output.txt, closure-check-output.txt, grep-evidence.txt, review-summary.md, file-manifest.txt

## Dependencies
- B-138 (budget ownership design)
- D-133 (policy engine contract)
```

### Issue 8: [B-141] Mission Startup Recovery
- **Labels:** `backlog`, `architecture`, `priority:P1`
- **Sprint target:** S65
- **Body:**

```
## Problem
System restart sonrası non-terminal mission'lar orphaned kalıyor.

## Recovery Matrix
| State at Crash | Approval State | Mission Recovery | Reason |
|---|---|---|---|
| RUNNING | N/A | → FAILED | orphaned_by_restart |
| WAITING_APPROVAL | PENDING | approval→EXPIRED, mission→FAILED | restart_expired_approval |
| WAITING_APPROVAL | ESCALATED | approval→EXPIRED, mission→FAILED | restart_expired_escalated_approval |
| PAUSED | N/A | preserve (stay PAUSED) | Operator explicitly paused |
| PLANNING | N/A | → FAILED | orphaned_by_restart |
| COMPLETED/FAILED/TIMED_OUT | N/A | no mutation | Terminal |

Fail-closed: tüm non-terminal, non-paused → fail. restartable flag freeze edilmeden auto-resume yok.

## Acceptance Criteria
- [ ] Her recovery matrix satırı ayrı test
- [ ] PAUSED preserved
- [ ] Terminal states untouched
- [ ] Approval status ve mission status ayrı mutated
- [ ] Alert emitted on orphaned detection
- [ ] Audit trail per recovery action

## Evidence
pytest-output.txt, lint-output.txt, closure-check-output.txt, grep-evidence.txt, review-summary.md, file-manifest.txt
```

### Issue 9: [B-142] Plugin Mutation Auth Boundary
- **Labels:** `backlog`, `security`, `priority:P1`
- **Sprint target:** S65
- **Body:**

```
## Problem
Plugin API mutation endpoint'lerinde auth enforcement tutarlılığı verify edilmemiş.

## Aksiyon
- All plugin mutation endpoints: require_operator dependency verify/add
- Plugin install/enable: trust_status check (unknown=warning, untrusted=deny)
- Auth test suite

## Acceptance Criteria
- [ ] All 4 write endpoints use require_operator
- [ ] trust_status enforcement tested
- [ ] No auth on mutation → 401
- [ ] Viewer on mutation → 403
- [ ] Operator → 200

## Evidence
pytest-output.txt, grep-evidence.txt, review-summary.md, file-manifest.txt
```

### Issue 10: [B-143] Persistence Boundary ADR
- **Labels:** `backlog`, `architecture`, `priority:P2`
- **Sprint target:** S66
- **Body:**

```
## Problem
File-store scaling boundary implicit. Plugin, scheduler, tenant, replay büyüdükçe kırılma noktası.

## Aksiyon
- D-140 freeze: Persistence Boundary Contract
- Hot state / audit log / artifact store ayrımı
- Scaling signals: validation method (measure contention, latency, file count)
- No numeric thresholds in decision — observation-driven trigger

## Acceptance Criteria
- [ ] D-140 frozen
- [ ] Validation method documented
- [ ] No hardcoded numeric thresholds

## Evidence
D-140 decision record, review-summary.md
```

### Issue 11: [B-144] Tool Reversibility Metadata Extension
- **Labels:** `backlog`, `governance`, `priority:P2`
- **Sprint target:** S66
- **Body:**

```
## Problem
Tool governance metadata'da reversibility bilgisi yok, policy engine kör kararlar veriyor.

## Fields
| Field | Type | Values |
|---|---|---|
| reversibility | enum | none / compensating / full |
| idempotent | bool | true / false |
| side_effect_scope | enum | local / external / irreversible |

## Aksiyon
- Tool catalog'a 3 yeni governance field
- validate_catalog_governance() update
- Policy rule: side_effect_scope=irreversible + risk=high → escalate
- 24 tool metadata güncelleme

## Acceptance Criteria
- [ ] validate_catalog_governance() 0 errors with new fields
- [ ] All 24 tools have reversibility metadata
- [ ] Policy rule evaluates correctly
- [ ] Startup validation passes (D-057)

## Evidence
pytest-output.txt, lint-output.txt, grep-evidence.txt, review-summary.md, file-manifest.txt
```

### Issue 12: [B-145] Enforcement Chain Documentation
- **Labels:** `backlog`, `devex`, `priority:P2`
- **Sprint target:** S67
- **Body:**

```
## Problem
Layered enforcement (Tool Gateway → Working Set → Risk Engine → Policy Engine → EventBus) var ama unified dokümanı yok.

## Aksiyon
- docs/shared/ENFORCEMENT-CHAIN.md
- Sequence: request → auth → Tool Gateway → Working Set → Risk Engine → Policy Engine → execute → audit
- Her layer fail behavior: deny / escalate / log / halt
- Cross-reference from GOVERNANCE.md

## Acceptance Criteria
- [ ] Document committed
- [ ] GOVERNANCE.md cross-reference added
- [ ] All enforcement layers listed with fail behavior

## Evidence
review-summary.md, file-manifest.txt
```

### Issue 13: [B-146] Mission Replay CLI Tool
- **Labels:** `backlog`, `devex`, `priority:P2`
- **Sprint target:** S67
- **Body:**

```
## Problem
Event verileri var (audit trail, transition log, policy telemetry) ama unified replay yok.

## Aksiyon
- tools/replay-mission.py <mission_id>
- Sources: audit-trail.jsonl + mission JSON transition_log + policy-telemetry.jsonl
- Output: chronological unified timeline (JSONL or human-readable table)

## Acceptance Criteria
- [ ] CLI tool runs against test mission data
- [ ] All 3 sources merged chronologically
- [ ] Output includes timestamp, actor, action, result per event

## Evidence
review-summary.md, file-manifest.txt, replay-output-sample.txt
```

### Issue 14: [B-147] Patch/Review/Apply/Revert Contract Design
- **Labels:** `backlog`, `architecture`, `priority:P3`
- **Sprint target:** S68
- **Body:**

```
## Problem
Claude Code-like convergence için explicit patch artifact + review/apply/revert loop gerekli.

## Aksiyon
- D-141 freeze: Patch/Review/Apply/Revert Contract
- Design-only, implementation deferred
- Patch artifact schema: {patch_id, target_files[], diff, author, review_status, applied_at}
- Review states: proposed → reviewed → approved → applied | reverted
- Operator approval required for apply
- Revert = new patch (not undo)

## Acceptance Criteria
- [ ] D-141 frozen
- [ ] Schema documented
- [ ] Review state machine documented
- [ ] No implementation

## Dependencies
- D-137 (bridge trust contract, ✅ done)
- D-139 (controller decomposition boundary)

## Evidence
D-141 decision record, review-summary.md
```

## Son Adımlar

1. Tüm issue'ları oluşturduktan sonra: `python tools/generate-backlog.py`
2. BACKLOG.md regenerate
3. Commit: "Phase 8: Create backlog issues B-134..B-147"
4. Push to main
