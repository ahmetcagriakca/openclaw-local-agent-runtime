# D-141: Patch/Review/Apply/Revert Contract

**Phase:** Sprint 68 (Phase 8C) | **Status:** Frozen | **Date:** 2026-04-06

## Context

Vezir's mission lifecycle produces code mutations as stage outputs. Currently there is no formal artifact representing a proposed code change, no structured review loop, and no revert mechanism. For Claude Code-like convergence — where an AI agent proposes changes, a reviewer evaluates them, and an operator applies or reverts — Vezir needs an explicit patch artifact with a governed lifecycle.

This decision defines the contract for patch artifacts: their schema, review state machine, operator control rules, and integration points with existing Vezir subsystems.

## Decision

### Patch Artifact Schema

Every proposed code mutation is captured as a **patch artifact** — a self-contained, auditable record of what will change, who proposed it, and what happened to it.

```json
{
  "patch_id": "patch_uuid",
  "mission_id": "mission_uuid",
  "author": "developer-role",
  "created_at": "ISO-8601",
  "target_files": ["path/to/file1.py", "path/to/file2.py"],
  "diff": "unified diff content",
  "description": "what this patch does",
  "review_status": "proposed",
  "risk_assessment": {
    "files_touched": 2,
    "lines_changed": 45,
    "has_irreversible_side_effects": false,
    "estimated_blast_radius": "low"
  },
  "base_revision": "git commit SHA or null",
  "target_file_hashes": {
    "path/to/file1.py": "SHA-256 hash of file content before patch",
    "path/to/file2.py": "SHA-256 hash of file content before patch"
  },
  "applied_at": null,
  "reverted_at": null,
  "revert_patch_id": null
}
```

**Field semantics:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `patch_id` | UUID string | Yes | Unique identifier, generated at creation |
| `mission_id` | UUID string | Yes | Parent mission that produced this patch |
| `author` | string | Yes | Role name from Role Registry (D-102) that authored the patch |
| `created_at` | ISO-8601 | Yes | Creation timestamp |
| `target_files` | string[] | Yes | List of file paths this patch modifies |
| `diff` | string | Yes | Unified diff content (standard `diff -u` format) |
| `description` | string | Yes | Human-readable description of what the patch does |
| `review_status` | enum | Yes | Current state in the review state machine |
| `risk_assessment` | object | Yes | Structured risk metadata |
| `risk_assessment.files_touched` | int | Yes | Number of files modified |
| `risk_assessment.lines_changed` | int | Yes | Total lines added + removed |
| `risk_assessment.has_irreversible_side_effects` | bool | Yes | Whether patch has side effects beyond file changes |
| `risk_assessment.estimated_blast_radius` | enum | Yes | `"low"` / `"medium"` / `"high"` / `"critical"` |
| `base_revision` | string \| null | Yes | Git commit SHA at patch creation time. Null if not under git control |
| `target_file_hashes` | object | Yes | Map of target file paths to SHA-256 content hashes at patch creation time. Used as precondition for apply |
| `applied_at` | ISO-8601 \| null | Yes | Timestamp when patch was applied, null if not yet applied |
| `reverted_at` | ISO-8601 \| null | Yes | Timestamp when patch was reverted, null if not reverted |
| `revert_patch_id` | UUID \| null | Yes | ID of the revert patch, null if not reverted |

### Review State Machine

Patch review follows a 5-state finite state machine with 6 valid transitions:

```
proposed → reviewed → approved → applied
              ↓                      ↓
           rejected              reverted
```

**States:**

| State | Description | Terminal? |
|-------|-------------|-----------|
| `proposed` | Patch created, awaiting reviewer assignment | No |
| `reviewed` | Reviewer assigned and assessed, verdict pending | No |
| `approved` | Reviewer issued PASS verdict, ready for apply | No |
| `rejected` | Reviewer issued FAIL verdict with reason | Yes |
| `applied` | Patch applied to codebase by operator | No (revertible) |
| `reverted` | Applied patch was reverted by operator | Yes |

**Transition Rules:**

| Transition | Trigger | Required Role | Postcondition |
|-----------|---------|---------------|---------------|
| `proposed → reviewed` | Reviewer assigns + initial assessment | Any reviewer role | Reviewer identity recorded |
| `reviewed → approved` | Reviewer issues PASS verdict | Any reviewer role | Approval timestamp + reviewer recorded |
| `reviewed → rejected` | Reviewer issues FAIL verdict | Any reviewer role | Rejection reason required (non-empty string) |
| `approved → applied` | Operator applies patch to codebase | Operator only (D-117) | `applied_at` set, files modified |
| `applied → reverted` | Operator applies revert | Operator only (D-117) | `reverted_at` set, `revert_patch_id` set |
| `proposed → approved` | Operator bypass (shortcut) | Operator only (D-117) | Skips review phase |

**Invalid transitions** (any not listed above): fail-closed — the transition is rejected and logged to audit trail.

### Operator Control Rules

The operator (D-117 auth model) has elevated privileges in the patch lifecycle:

1. **Apply requires operator role.** No agent or automated process may apply a patch without operator authorization. This is the hard gate between "AI proposes" and "code changes."

2. **Revert requires operator role.** Revert is a destructive action. Only the operator may initiate it.

3. **Operator bypass.** The operator may transition `proposed → approved` directly, skipping the review phase. This enables fast-path for trivial patches or operator-authored changes.

4. **Revert = new patch.** A revert does NOT undo or delete the original patch. Instead, it creates a new patch with the inverted diff. This preserves full audit trail — every mutation is recorded, never erased. The original patch's `revert_patch_id` links to the revert patch.

5. **Rejection is terminal.** A rejected patch cannot be re-reviewed or re-proposed. If the underlying change is still desired, a new patch must be created. This prevents unbounded review cycling.

### Anti-Drift Preconditions

Patches carry deterministic preconditions that prevent apply against drifted file state:

1. **`target_file_hashes`** — At patch creation time, the SHA-256 hash of each target file's content is recorded. Before apply, the current file content is hashed and compared. If any hash mismatches, apply is **rejected** (fail-closed) with a `PRECONDITION_FAILED` error. The operator must create a new patch against the current file state.

2. **`base_revision`** — The git commit SHA at patch creation time. This is informational (not enforced at apply time) but provides traceability for when the patch was authored relative to the repo timeline.

3. **Apply precondition failure** — When `target_file_hashes` do not match current file content:
   - Transition `approved → applied` is blocked
   - Patch remains in `approved` state (not rejected — the review is still valid)
   - Error includes: which files drifted, expected vs actual hashes
   - Operator may create a new patch with updated diff against current state

4. **Revert precondition** — Revert creates a new patch whose `target_file_hashes` are the post-apply file hashes (i.e., the state the files are in after the original patch was applied). This ensures the revert only executes against the expected post-patch state, not against further-drifted files. If the files have been modified after the original patch was applied (by another patch or manual edit), the revert's precondition check will fail-closed, requiring manual intervention.

### Integration Points

D-141 connects to six existing Vezir subsystems:

| Subsystem | Decision | Integration |
|-----------|----------|-------------|
| **JSON File Store** | D-106 | Patch artifacts persisted as JSON files. Patch store = new category under D-140 persistence boundary (hot state — read-write, contention-sensitive, atomic writes) |
| **EventBus** | D-014 | Patch lifecycle transitions emit events: `patch.proposed`, `patch.reviewed`, `patch.approved`, `patch.rejected`, `patch.applied`, `patch.reverted` |
| **Audit Trail** | D-129 | All patch transitions logged to audit trail. Patch apply/revert are auditable mutations with hash-chain integrity |
| **Working Set Enforcer** | D-053 | `target_files` validated against mission working set. Patches targeting files outside working set are rejected at creation |
| **Risk Engine** | D-128 | `risk_assessment` fields feed into Risk Engine evaluation. High blast radius patches may trigger additional approval requirements |
| **Policy Engine** | D-133 | Apply decision evaluated by Policy Engine. Policies can gate apply on risk level, file patterns, or role constraints |

### Architectural Implications

#### 1. Mission Lifecycle Integration

Patch artifact fits into the mission lifecycle as the output of the `develop` stage:

```
mission stages → develop stage output → patch artifact → review → apply
```

The develop stage (or any code-producing stage) generates a patch artifact instead of directly modifying files. This decouples "AI generated code" from "code landed in codebase" — the patch is the bridge, and the operator controls when it crosses.

#### 2. Patch Store Placement

Under D-140 persistence boundary, patch store is **hot state**:
- Read-write (patches are created, then transitioned through states)
- Atomic writes required (patch state transitions must be atomic)
- Contention-sensitive (multiple missions may produce patches concurrently)
- Storage: `logs/patches/patch-{patch_id}.json` (one file per patch, avoids single-file contention)

#### 3. Quality Gate Interaction

G2 (code review gate) maps naturally to the patch review phase:
- G2 PASS = `reviewed → approved` transition
- G2 FAIL = `reviewed → rejected` transition
- This makes G2 a concrete checkpoint in the patch state machine rather than an abstract governance gate

#### 4. Controller Decomposition Impact

Per D-139 (controller decomposition boundary), patch handling is a candidate for a new service boundary:
- **PatchService** — owns patch CRUD, state transitions, validation
- Controller delegates patch operations to PatchService
- PatchService enforces transition rules and emits EventBus events
- This aligns with D-139's principle of extracting bounded responsibilities from the monolithic controller

### What D-141 Does NOT Cover (Explicitly Deferred)

The following capabilities are explicitly out of scope for D-141 and deferred to future decisions:

1. **Automatic diff generation from LLM output** — How to extract structured diffs from LLM responses is an implementation concern, not a contract concern.
2. **IDE/editor integration** — How patches are displayed or interacted with in editors is a UX concern.
3. **Git commit automation** — Whether/how applied patches become git commits is orthogonal to the patch lifecycle.
4. **Merge conflict resolution** — What happens when two patches target overlapping files is a runtime concern requiring implementation experience.
5. **Multi-patch dependency ordering** — Ordering and sequencing of related patches requires a task graph model (future D-144 candidate).
6. **Patch versioning/amendment** — Whether a patch can be amended in-place vs. requiring a new patch. Current decision: new patch required (rejection is terminal).

## Consequences

- Every code mutation flows through a governed, auditable pipeline
- Operator retains explicit control over what lands in the codebase
- Revert-as-new-patch ensures complete audit trail with no data loss
- Working set enforcement prevents scope creep at the patch level
- Risk engine integration enables graduated approval based on blast radius
- G2 quality gate gets concrete implementation as patch review transition
- Controller decomposition gets a clear new service boundary (PatchService)

## References

- D-014: EventBus architecture
- D-053: Working Set Enforcer
- D-106: JSON file persistence
- D-117: Operator auth model
- D-128: Risk Engine
- D-129: Audit trail integrity
- D-133: Policy Engine
- D-139: Controller decomposition boundary
- D-140: Persistence boundary contract
