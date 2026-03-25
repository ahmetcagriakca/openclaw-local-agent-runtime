# Copilot Instructions — OpenClaw Local Agent Runtime

## 1. Language and Style
- Turkish conversation, English technical terms (sprint, commit, schema freeze, circuit breaker, capability manifest, stale, degraded).
- Short, direct, action-oriented sentences.
- No praise, no filler, no motivational tone.
- Do not say "you can" or "if you want." Do the work or state why it is blocked.

## 2. Core Working Rules
- Iterative workflow: design → review → revise → freeze.
- Every iteration produces a concrete output: document, decision record, patch plan, prototype, code, or test. No chat-only responses when an artifact is expected.
- Blocking fixes first. No parallel tracks until the blocker is resolved.
- Her sprint sonunda yapılan tüm çalışmalar (kod, doküman, evidence) git commit + push yapılmalıdır. Sprint, push yapılmadan kapatılmış sayılmaz.

## 3. Source Hierarchy
When sources conflict, follow this precedence (highest first):

1. Real code in the repo
2. Test results, logs, runtime evidence
3. Frozen decisions (D-XXX)
4. Sprint plans and design docs
5. GPT / Claude cross-review comments
6. Assumptions

Rules:
- Do not ignore cross-review comments. Do not treat them as truth without verification.
- Verify claims against code, tests, logs, or explicit docs.
- Do not write "complete," "sealed," or "resolved" without evidence.
- Source precedence within runtime: `state.json` > `mission.json` (status), `summary` > `telemetry` (forensics).

## 4. Decision Standard
Every freezable architectural decision uses `D-XXX` format.

Each decision includes:
- ID, Title, Status (proposed | accepted | frozen | deprecated)
- Context, Decision, Trade-off
- Impacted files/components
- Validation method
- Rollback / reversal condition

No architecture changes without a recorded decision.

## 5. Sprint / Task Standard
Every sprint or task includes:
- Goal, Scope, Dependencies, Blocking risks
- Acceptance criteria, Exit criteria
- Verification commands, Expected evidence
- Produced artifacts/files

No vague tasks. No "to be clarified later" placeholders.

## 6. Uncertainty Rule
Two valid options when something is unclear:
1. Resolve it now.
2. Mark it as `OPEN DECISION` with: Problem, Why open, Data needed, Owner, Next step, Deadline.

No open decision without a next action.

## 7. Architecture Principles
- Sequence: read-only → live → mutation.
- Unknown ≠ zero. Missing ≠ healthy.
- Unavailable data never rendered as 0, empty, pass, or green.
- Explicit detection over heuristics.
- Capability detection via `config/capabilities.json`, not heuristics.
- Atomic writes: temp → fsync → `os.replace()`. No raw `json.dump` to file.
- Trade-offs named: "This improves X but weakens Y."

## 8. UI / Mission Control Principles
- People believe what they see. Poor or missing visualization is negative.
- UI explicitly distinguishes: known-zero, unknown, not_reached, stale, partial, degraded.
- Silent absence forbidden. Every page has explicit empty/loading/error states.
- Every data block shows freshness / timestamp / data quality.
- No fake live behavior. Live indicators tied to real events.

## 9. Repo and Code Change Rule
- Inspect existing files and flow before proposing changes.
- Strengthen existing structure, do not replace with "clean rewrite."
- Resolve file ownership, source precedence, or migration boundaries first.
- Design from normalized contract, not mock data.
- Do not treat UI mock structure as backend truth.

## 10. Testing and Verification Rule
- Every change includes verification commands and expected output.
- No test → write `TEST MISSING`.
- No evidence → write `NO EVIDENCE`.
- Unverified work is not finished.

## 11. Completion Rule
A task is "done" only if ALL are true:
- Decision record updated (if applicable)
- Documentation updated
- Task/sprint plan updated
- Code or prototype produced
- Verification command provided
- At least one observable evidence exists
- Git commit + push completed

Missing any → label `partial` or `draft`, not `done`.

## 12. Default Response Structure
Unless task requires different format:
1. Clear judgment
2. Blocking issues
3. Non-blocking notes
4. Recommended action order
5. Files to create/change
6. Verification

End with paste-ready output when useful.

## 13. Do Not
- Repeat the same summary multiple times.
- Add cosmetic praise or filler.
- Leave placeholders or "to be clarified later."
- Make unsupported claims.
- Invent fields that contradict repo reality.
- Treat UI mock as backend truth.
- Hide technical debt behind "decide later."
- Claim "done" without verification evidence.
- Use Node.js 14 for frontend (requires Node.js 20+ for Vite 6).
- Write to files without `atomic_write_json()`.

## 14. Key Reference Docs
- `CLAUDE.md` — project state, architecture, build commands, phase progress
- `docs/ai/STATE.md` — current system state
- `docs/ai/DECISIONS.md` — frozen decisions
- `docs/ai/NEXT.md` — roadmap
- `docs/ai/PROTOCOL.md` — sprint + freeze protocols
- `SESSION-HANDOFF.md` — latest sprint handoff