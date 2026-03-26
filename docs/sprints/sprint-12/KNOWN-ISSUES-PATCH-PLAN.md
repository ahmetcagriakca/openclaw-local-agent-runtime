# Known Issues Patch Plan — Vezir Platform

**Date:** 2026-03-26
**Sprint:** 13, Tasks 13.1-13.3
**Priority:** Fix after EventBus (13.0), before structural refactor

---

## Issue 1: Token Report ID Mismatch (High)

**Symptom:** UI panel shows "No report" even though controller saves JSON.
**Root cause:** Dashboard creates mission with placeholder ID. Controller uses internal ID. Report saved under controller ID → UI fetch by dashboard ID → 404.

**Fix:** Add `resolve_mission_id()` normalizer in mission_api.py that looks up controller ID from mission metadata matching dashboard_id field.

**Verify:** `curl localhost:8003/api/missions/<dashboard-id>/token-report | jq .status` → 200
**Evidence:** `evidence/sprint-13/token-report-id-fix.txt`

---

## Issue 2: WSL Directory Names (Medium)

**Symptom:** `/home/akca/.openclaw/`, `pgrep -fa openclaw` still use old name.
**Root cause:** Rebrand changed ~30 Windows files but WSL untouched.

**Fix (Option A — safe):**
1. `mv /home/akca/.openclaw /home/akca/.vezir`
2. `mv .vezir/openclaw.json .vezir/vezir.json`
3. `sed -i 's/openclaw/vezir/g' .vezir/vezir.json`
4. `ln -s /home/akca/.vezir /home/akca/.openclaw` (backward compat)
5. Update pgrep patterns in scripts
6. Keep `oc-` script prefixes (full rename = Phase 6)

**Verify:** `ls /home/akca/.vezir/vezir.json` exists, services still work
**Evidence:** `evidence/sprint-13/wsl-rename-evidence.txt`

---

## Issue 3: Uncontrolled Rework Count (Medium)

**Symptom:** Simple mission triggered 6 reworks. Wastes ~30K tokens.
**Root cause:** No complexity-based limit in controller.

**Fix (D-103):**

| Complexity | Max/Stage | Max/Mission |
|-----------|-----------|-------------|
| trivial | 1 | 2 |
| simple | 2 | 4 |
| medium | 3 | 8 |
| complex | 5 | 15 |

When limit reached: stage uses best available artifact, warning logged, report includes rework summary.

Post-EventBus: becomes `ReworkLimiter` handler on `stage.rework_requested` event.

**Verify:** Simple mission ≤ 4 total reworks. `grep "REWORK LIMIT" logs/`
**Evidence:** `evidence/sprint-13/rework-limiter-test.txt`

---

## Execution Order

```
13.0 (EventBus — BLOCKER)
  → 13.1 (token ID fix — quick win)
  → 13.2 (WSL rename — careful)
  → 13.3 (rework limiter — needs D-103 freeze)
  → Track 2+ continues...
```
