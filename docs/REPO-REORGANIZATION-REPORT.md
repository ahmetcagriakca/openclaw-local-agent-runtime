# Repo Reorganization Report

**Date:** 2026-03-23
**Scope:** Monorepo structural reorganization — no behavioral changes
**Branch:** main (ready for initial commit)

---

## Summary

Reorganized `C:\Users\AKCA\oc` from a flat working directory into a push-ready monorepo structure. All 14 tasks completed successfully. No runtime logic, bridge logic, or action behavior was modified.

---

## Task Results

### Task 1: Directory Creation — DONE

| Directory | Status |
|-----------|--------|
| `wsl/` | Created |
| `config/` | Created |
| `docs/ai/` | Already existed |
| `docs/architecture/` | Created |
| `docs/phase-reports/` | Created |
| `docs/tasks/` | Created |

---

### Task 2: Docs Reorganization — DONE

Moved 27 markdown files from flat `docs/` into 3 subdirectories.

**docs/architecture/ (5 files)**

| File | Source |
|------|--------|
| ARCHITECTURE.md | Main architecture document |
| BOOTSTRAP-IDEMPOTENCY-CONFIG-CANONICAL.md | Canonical design doc |
| NAMING-GUI-SEMANTICS-CANONICAL.md | Canonical design doc |
| RETRY-TASK-CANONICAL.md | Canonical design doc |
| SUPERVISOR-RESTART-RECOVERY-CANONICAL.md | Canonical design doc |

**docs/phase-reports/ (7 files)**

| File | Pattern Match |
|------|---------------|
| PHASE-1.5-BRIDGE-CONTRACT-FREEZE.md | PHASE-1.5-* |
| PHASE-1.5-D-SECURITY-BASELINE-FREEZE.md | PHASE-1.5-* / SECURITY-BASELINE |
| PHASE-1.5-E-BRIDGE-IMPLEMENTATION-REPORT.md | PHASE-1.5-* / IMPLEMENTATION-REPORT |
| PHASE-1.5-F-EXIT-VERIFICATION-REPORT.md | PHASE-1.5-* / EXIT-VERIFICATION |
| PHASE-1.5-FINAL-CLOSURE-REPORT.md | PHASE-1.5-* / FINAL-CLOSURE |
| PHASE-TG1-TELEGRAM-CALLER-BOOTSTRAP-REPORT.md | PHASE-TG* / TELEGRAM-CALLER |
| PHASE-TG1R-OPENCLAW-WIRING-REPORT.md | PHASE-TG* / OPENCLAW-WIRING |

**docs/tasks/ (15 files)**

| File | Pattern Match |
|------|---------------|
| TASK-F1.1-REPORT.md | TASK-F1.* |
| TASK-F1.2-CLEANUP-REPORT.md | TASK-F1.* |
| TASK-F1.2-REPORT.md | TASK-F1.* |
| TASK-F1.3-CLEANUP-REPORT.md | TASK-F1.* |
| TASK-F1.3-REPORT.md | TASK-F1.* |
| TASK-F1.4-BEHAVIOR-REPORT.md | TASK-F1.* |
| TASK-F1.4-CLEANUP-REPORT.md | TASK-F1.* |
| TASK-F1.4-REPORT.md | TASK-F1.* |
| TASK-F1.4-SYNC-REPORT.md | TASK-F1.* |
| TASK-F1.5-HARDENING-REPORT.md | TASK-F1.* |
| TASK-F1.5-REPORT.md | TASK-F1.* |
| TASK-TDR-0-REPORT.md | TASK-TDR-* |
| TASK1-GPT-RESPONSE.md | TASK1-* |
| TASK1-gap-analysis.md | TASK1-* |
| TASK1-worker-fail-recovery.md | TASK1-* |

**Note:** `operating-model-freeze-v1.md` was not found on disk. No unmatched files remained in docs/ root.

---

### Task 3: WSL Wrapper Copy — DONE

Copied 5 scripts from `Ubuntu-E:/home/akca/bin/` to `C:\Users\AKCA\oc\wsl\`.

| File | Size | Verified |
|------|------|----------|
| oc-bridge-call | 340 B | Non-zero |
| oc-bridge-cancel | 654 B | Non-zero |
| oc-bridge-health | 474 B | Non-zero |
| oc-bridge-status | 661 B | Non-zero |
| oc-bridge-submit | 887 B | Non-zero |

Method: `wsl -d Ubuntu-E -- cat //home/akca/bin/<file>` (double-slash to bypass MSYS path translation in Git Bash).

---

### Task 4: Bin Verification — DONE

Both required scripts confirmed present:
- `bin/start-wmcp-server.ps1` — present
- `bin/register-wmcp-task.ps1` — present

**Total: 24 scripts** in `bin/` (exceeds ~20 expectation).

<details>
<summary>Full bin/ listing</summary>

```
oc-healthcheck.ps1
oc-list-actions-json.ps1
oc-list-actions.ps1
oc-log-rotate.ps1
oc-reboot-validate.ps1
oc-run-action.ps1
oc-run-file.ps1
oc-runtime-startup-preflight.ps1
oc-runtime-watchdog.ps1
oc-task-cancel.ps1
oc-task-common.ps1
oc-task-enqueue.ps1
oc-task-get.ps1
oc-task-health.ps1
oc-task-list.ps1
oc-task-output.ps1
oc-task-repair.ps1
oc-task-retry.ps1
oc-task-runner.ps1
oc-task-worker.ps1
oc-validate-manifest.ps1
register-wmcp-task.ps1
start-wmcp-server.ps1
wmcp-call.ps1
```

</details>

---

### Task 5: AI State Files — DONE

| File | Status |
|------|--------|
| docs/ai/STATE.md | Overwritten with canonical content |
| docs/ai/DECISIONS.md | Overwritten with canonical content (D-001 through D-020) |
| docs/ai/BACKLOG.md | Overwritten with canonical content (B-001 through B-028) |
| docs/ai/NEXT.md | Overwritten with canonical content |
| docs/ai/PROTOCOL.md | Overwritten with canonical content |

Previous versions existed from an earlier session and were replaced with the task-specified content.

---

### Task 6: Config Template — DONE

Created `config/env.example` with 3 environment variable placeholders:
- `OC_TELEGRAM_BOT_TOKEN`
- `OC_BRIDGE_AUDIT_LOG` (commented, optional)
- `OC_MCP_BASE_URL` (commented, optional)

---

### Task 7: Allowlist Template — DONE

Created `bridge/allowlist.example.json` with placeholder user ID.

---

### Task 8: Gitignore — DONE (with fix)

Created `.gitignore` with all specified rules.

**Fix applied during execution:** Changed `tasks/` and `results/` to `/tasks/` and `/results/` (root-anchored). Without the leading slash, gitignore was also excluding `docs/tasks/` and `defs/tasks/` — subdirectories that must be committed.

Final `.gitignore` excludes:
- Runtime state: `logs/`, `bridge/logs/`, `/queue/`, `/tasks/`, `/results/`
- Secrets: `bridge/allowlist.json`, `config/.env`, `*.env`, `*.env.*`, `.openclaw/`
- IDE: `.claude/`, `.vscode/`, `*.code-workspace`
- OS: `Thumbs.db`, `Desktop.ini`, `.DS_Store`
- Backups: `*.bak`, `*.bak-*`
- Bootstrap: `oc-task-runtime-bootstrap-v3.4.ps1`
- Legacy: `olds/`

---

### Task 9: README — DONE

Created `README.md` with:
- Architecture diagram (caller path)
- Repository structure map (updated for new layout)
- Quick start (3-step)
- Phase table

---

### Task 10: Superseded File Cleanup — DONE

- **Deleted:** `telegram/oc-telegram-bot.py` (superseded by OpenClaw path, D-019)
- **No .bak files** found in `telegram/`
- **Remaining in telegram/ (10 files):**

| File | Type |
|------|------|
| oc-bridge-call.sh | Bridge wrapper (shell) |
| oc-bridge-cancel.sh | Bridge wrapper (shell) |
| oc-bridge-health.sh | Bridge wrapper (shell) |
| oc-bridge-status.sh | Bridge wrapper (shell) |
| oc-bridge-submit.sh | Bridge wrapper (shell) |
| install-wsl-wrappers.py | Installer utility |
| debug-submit.py | Debug utility |
| test-submit-native.py | Test utility |
| test-wsl-bridge.sh | Test script |
| test-args.json | Test data |

---

### Task 11: Olds Removal — DONE

`olds/` directory does not exist — already removed in Phase 1.5-B.

---

### Task 12: Git Init and Stage — DONE

- Repo already initialized — renamed branch `master` to `main`
- `git add .` — **93 files staged**
- CRLF warnings present (expected on Windows, non-blocking)

---

### Task 13: Sensitive File Audit — DONE

Scanned all 93 staged files against the exclusion list:

| Check | Result |
|-------|--------|
| bridge/allowlist.json | Not staged (gitignored) |
| *.env with values | Not staged (gitignored) |
| logs/ | Not staged (gitignored) |
| bridge/logs/ | Not staged (gitignored) |
| queue/ | Not staged (gitignored) |
| tasks/ | Not staged (gitignored) |
| results/ | Not staged (gitignored) |
| .claude/ | Not staged (gitignored) |
| .openclaw/ | Not staged (gitignored) |
| oc-task-runtime-bootstrap-v3.4.ps1 | Not staged (gitignored) |
| *.bak files | Not staged (gitignored) |

**Zero sensitive files in staging.**

---

### Task 14: Final Directory Tree

```
oc/                              (repo root)
├── .gitignore
├── README.md
├── actions/                     (16 files)
│   ├── cancel-task.ps1
│   ├── enqueue-task.ps1
│   ├── get-task-artifacts.ps1
│   ├── get-task-events.ps1
│   ├── get-task-output.ps1
│   ├── get-task.ps1
│   ├── list-tasks.ps1
│   ├── manifest.json
│   ├── notepad-test.ps1
│   ├── open-app.ps1
│   ├── retry-task.ps1
│   ├── task-healthcheck.ps1
│   ├── wait-task.ps1
│   └── write-file.ps1
├── bin/                         (24 scripts)
│   ├── oc-healthcheck.ps1
│   ├── oc-list-actions-json.ps1
│   ├── oc-list-actions.ps1
│   ├── oc-log-rotate.ps1
│   ├── oc-reboot-validate.ps1
│   ├── oc-run-action.ps1
│   ├── oc-run-file.ps1
│   ├── oc-runtime-startup-preflight.ps1
│   ├── oc-runtime-watchdog.ps1
│   ├── oc-task-cancel.ps1
│   ├── oc-task-common.ps1
│   ├── oc-task-enqueue.ps1
│   ├── oc-task-get.ps1
│   ├── oc-task-health.ps1
│   ├── oc-task-list.ps1
│   ├── oc-task-output.ps1
│   ├── oc-task-repair.ps1
│   ├── oc-task-retry.ps1
│   ├── oc-task-runner.ps1
│   ├── oc-task-worker.ps1
│   ├── oc-validate-manifest.ps1
│   ├── register-wmcp-task.ps1
│   ├── start-wmcp-server.ps1
│   └── wmcp-call.ps1
├── bridge/                      (3 files staged)
│   ├── allowlist.example.json
│   ├── oc-bridge.ps1
│   └── test-bridge.ps1
├── config/                      (1 file)
│   └── env.example
├── defs/tasks/                  (2 files)
│   ├── create_note.json
│   └── notepad_then_ready.json
├── docs/
│   ├── ai/                      (5 files)
│   │   ├── BACKLOG.md
│   │   ├── DECISIONS.md
│   │   ├── NEXT.md
│   │   ├── PROTOCOL.md
│   │   └── STATE.md
│   ├── architecture/            (5 files)
│   │   ├── ARCHITECTURE.md
│   │   ├── BOOTSTRAP-IDEMPOTENCY-CONFIG-CANONICAL.md
│   │   ├── NAMING-GUI-SEMANTICS-CANONICAL.md
│   │   ├── RETRY-TASK-CANONICAL.md
│   │   └── SUPERVISOR-RESTART-RECOVERY-CANONICAL.md
│   ├── phase-reports/           (7 files)
│   │   ├── PHASE-1.5-BRIDGE-CONTRACT-FREEZE.md
│   │   ├── PHASE-1.5-D-SECURITY-BASELINE-FREEZE.md
│   │   ├── PHASE-1.5-E-BRIDGE-IMPLEMENTATION-REPORT.md
│   │   ├── PHASE-1.5-F-EXIT-VERIFICATION-REPORT.md
│   │   ├── PHASE-1.5-FINAL-CLOSURE-REPORT.md
│   │   ├── PHASE-TG1-TELEGRAM-CALLER-BOOTSTRAP-REPORT.md
│   │   └── PHASE-TG1R-OPENCLAW-WIRING-REPORT.md
│   └── tasks/                   (15 files)
│       ├── TASK-F1.1-REPORT.md
│       ├── TASK-F1.2-CLEANUP-REPORT.md
│       ├── TASK-F1.2-REPORT.md
│       ├── TASK-F1.3-CLEANUP-REPORT.md
│       ├── TASK-F1.3-REPORT.md
│       ├── TASK-F1.4-BEHAVIOR-REPORT.md
│       ├── TASK-F1.4-CLEANUP-REPORT.md
│       ├── TASK-F1.4-REPORT.md
│       ├── TASK-F1.4-SYNC-REPORT.md
│       ├── TASK-F1.5-HARDENING-REPORT.md
│       ├── TASK-F1.5-REPORT.md
│       ├── TASK-TDR-0-REPORT.md
│       ├── TASK1-GPT-RESPONSE.md
│       ├── TASK1-gap-analysis.md
│       └── TASK1-worker-fail-recovery.md
├── telegram/                    (10 files)
│   ├── debug-submit.py
│   ├── install-wsl-wrappers.py
│   ├── oc-bridge-call.sh
│   ├── oc-bridge-cancel.sh
│   ├── oc-bridge-health.sh
│   ├── oc-bridge-status.sh
│   ├── oc-bridge-submit.sh
│   ├── test-args.json
│   ├── test-submit-native.py
│   └── test-wsl-bridge.sh
└── wsl/                         (5 files)
    ├── oc-bridge-call
    ├── oc-bridge-cancel
    ├── oc-bridge-health
    ├── oc-bridge-status
    └── oc-bridge-submit
```

**Total staged: 93 files | Sensitive files staged: 0**

---

## Issues Found and Resolved

| # | Issue | Resolution |
|---|-------|------------|
| 1 | `.gitignore` rule `tasks/` was excluding `docs/tasks/` and `defs/tasks/` | Changed to `/tasks/` (root-anchored). Same fix for `/results/`. |
| 2 | WSL path translation in Git Bash (`/home/` → `C:/Program Files/Git/home/`) | Used `//home/` double-slash prefix to bypass MSYS translation. |
| 3 | `defs/tasks/*.json` not picked up by initial `git add .` | Caused by issue #1. Resolved after gitignore fix. |

## Gaps / Operator Action Required

| # | Item | Action |
|---|------|--------|
| 1 | `operating-model-freeze-v1.md` not found | Confirm if this document exists elsewhere or was never created. |
| 2 | This report file (`docs/REPO-REORGANIZATION-REPORT.md`) | Needs `git add` before commit if desired in repo. |

---

## Next Step

Repo is staged on branch `main` with 93 files. Awaiting operator command to commit and push.

```powershell
git commit -m "Initial commit: Phase 1.5 sealed runtime + bridge + telegram"
```
