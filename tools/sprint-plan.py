#!/usr/bin/env python3
"""
sprint-plan.py — Sprint kickoff planning audit for Vezir Platform
Usage: python tools/sprint-plan.py <sprint_number> [--goal "X"] [--scope "Y"] [--strict]

Reads:  docs/ai/handoffs/current.md, docs/ai/state/open-items.md,
        docs/ai/STATE.md, DECISIONS.md, tools/sprint-policy.yml
Writes: docs/review-packets/S{N}-PLAN-PACKET.md
        docs/review-packets/S{N}-PLAN-AUDIT.json

Exit codes:
  0 = KICKOFF READY
  1 = KICKOFF BLOCKED
  2 = usage error
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT      = Path(__file__).parent.parent
HANDOFF_FILE   = REPO_ROOT / "docs" / "ai" / "handoffs" / "current.md"
OPEN_ITEMS     = REPO_ROOT / "docs" / "ai" / "state" / "open-items.md"
STATE_FILE     = REPO_ROOT / "docs" / "ai" / "STATE.md"
DECISIONS_FILE = REPO_ROOT / "docs" / "ai" / "DECISIONS.md"
NEXT_FILE      = REPO_ROOT / "docs" / "ai" / "NEXT.md"
POLICY_FILE    = REPO_ROOT / "tools" / "sprint-policy.yml"
SPRINTS_DIR    = REPO_ROOT / "docs" / "sprints"
OUT_DIR        = REPO_ROOT / "docs" / "review-packets"

# ── Helpers ───────────────────────────────────────────────────────────────────

def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""

def load_policy(n: int) -> dict:
    content = read(POLICY_FILE)
    policy = {
        "max_open_decisions": 2,
        "require_previous_sprint_closed": True,
        "require_mid_review_task": True,
        "require_final_review_task": True,
        "require_evidence_checklist": True,
        "require_acceptance_criteria": True,
        "require_exit_criteria": True,
    }
    block = re.search(rf'^\s+{n}:\s*\n((?:\s{{4,}}[^\n]+\n?)*)', content, re.MULTILINE)
    if block:
        b = block.group(1)
        for key in policy:
            m = re.search(rf'{key}:\s*(\d+|true|false)', b, re.IGNORECASE)
            if m:
                v = m.group(1)
                if v.isdigit():
                    policy[key] = int(v)
                else:
                    policy[key] = v.lower() == "true"
    return policy

def previous_sprint_closed(n: int) -> bool:
    if n <= 1:
        return True
    prev = n - 1
    # Check sprint README
    for name in [f"S{prev}-README.md", "README.md"]:
        p = SPRINTS_DIR / f"sprint-{prev}" / name
        if p.exists():
            m = re.search(r'closure_status\*?\*?[:\s=*]+(\w+)', read(p), re.IGNORECASE)
            if m:
                return m.group(1).lower() == "closed"
    # Fallback: check STATE.md
    state = read(STATE_FILE)
    return bool(re.search(rf'sprint[_\s-]*{prev}[^\n]*closed', state, re.IGNORECASE))

def count_open_decisions(content: str) -> int:
    return len(re.findall(r'\bOD-\d+\b', content))

def extract_frozen_decisions(content: str) -> list[str]:
    return re.findall(r'###\s+(D-\d+)', content)

def check_decision_frozen(d_id: str, decisions_content: str) -> bool:
    block = re.search(rf'##\s+{d_id}.*?\n(.*?)(?=\n##|\Z)', decisions_content, re.DOTALL)
    if not block:
        return False
    return bool(re.search(r'status.*frozen', block.group(1), re.IGNORECASE))

def extract_carry_forward(content: str) -> list[dict]:
    items = []
    in_section = False
    for line in content.splitlines():
        if re.search(r'carry.forward|open.items', line, re.IGNORECASE):
            in_section = True
            continue
        if in_section and line.startswith('#'):
            in_section = False
        if in_section and '|' in line and not line.startswith('|---'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2 and parts[0] not in ('Item', '#'):
                items.append({"item": parts[0], "source": parts[1] if len(parts) > 1 else ""})
    return items

def extract_open_blockers(content: str) -> list[str]:
    blockers = []
    in_section = False
    for line in content.splitlines():
        if re.search(r'active.blocker|open.blocker', line, re.IGNORECASE):
            in_section = True
            continue
        if in_section and line.startswith('#'):
            break
        if in_section and '|' in line and not line.startswith('|---'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if parts and parts[0] not in ('Item', '#', ''):
                blockers.append(parts[0])
    return blockers

# ── Main audit ────────────────────────────────────────────────────────────────

def audit_plan(n: int, goal: str = "", scope: str = "", strict: bool = False) -> dict:
    ts      = datetime.now(timezone.utc).isoformat()
    policy  = load_policy(n)

    handoff_content   = read(HANDOFF_FILE)
    open_items_content = read(OPEN_ITEMS)
    decisions_content = read(DECISIONS_FILE)
    next_content      = read(NEXT_FILE)
    state_content     = read(STATE_FILE)

    # Combine context for carry-forward / blocker extraction
    context = handoff_content + "\n" + open_items_content + "\n" + next_content

    checks = {}
    hold_reasons = []

    # 1. Goal
    checks["goal_present"] = bool(goal.strip())
    if not checks["goal_present"]:
        hold_reasons.append("Goal is empty. Pass --goal or populate current.md.")

    # 2. Scope
    checks["scope_present"] = bool(scope.strip())
    if not checks["scope_present"]:
        hold_reasons.append("Scope is empty. Pass --scope or populate current.md.")

    # 3. Previous sprint closed
    checks["previous_sprint_closed"] = previous_sprint_closed(n)
    if policy["require_previous_sprint_closed"] and not checks["previous_sprint_closed"]:
        hold_reasons.append(f"Sprint {n-1} is not closure_status=closed. Cannot open Sprint {n}.")

    # 4. Open blockers
    blockers = extract_open_blockers(context)
    checks["open_blocker_count"] = len(blockers)
    if blockers:
        hold_reasons.append(f"{len(blockers)} open blocker(s) in docs/ai/state/open-items.md must be resolved before kickoff.")

    # 5. Open decisions
    od_count = count_open_decisions(context + decisions_content)
    checks["open_decision_count"] = od_count
    max_od = policy["max_open_decisions"]
    if od_count > max_od:
        hold_reasons.append(f"{od_count} open decisions (OD-XX) exceed limit of {max_od}. Resolve or formally defer.")

    # 6. Required decisions (referenced in context but not verified frozen)
    d_refs = re.findall(r'\bD-(\d+)\b', context)
    d_refs = list(set(d_refs))
    required_decisions = []
    for d_num in sorted(d_refs, key=int):
        d_id = f"D-{d_num}"
        frozen = check_decision_frozen(d_id, decisions_content)
        required_decisions.append({"id": d_id, "frozen": frozen})
        if not frozen and strict:
            hold_reasons.append(f"{d_id} referenced in context but not confirmed frozen in DECISIONS.md.")
    checks["required_decisions"] = required_decisions

    # 7. Carry-forward
    carry_forward = extract_carry_forward(context)
    checks["carry_forward_count"] = len(carry_forward)

    # 8. Gate tasks (checked via policy flags — actual task list populated by template)
    checks["require_mid_review_task"]   = policy["require_mid_review_task"]
    checks["require_final_review_task"] = policy["require_final_review_task"]
    # These are HOLD at final review, not here — flag as reminder
    if policy["require_mid_review_task"]:
        hold_reasons.append("REMINDER: Ensure mid-review gate task is in task breakdown before implementation starts.")
    if policy["require_final_review_task"]:
        hold_reasons.append("REMINDER: Ensure final-review gate task is in task breakdown before implementation starts.")
    # Remove reminders from hold if goal/scope present (don't block on reminders)
    hold_reasons = [h for h in hold_reasons if not h.startswith("REMINDER:")]

    # 9. Kickoff verdict
    hard_blockers = [h for h in hold_reasons]
    checks["kickoff_verdict"] = "KICKOFF READY" if not hard_blockers else "KICKOFF BLOCKED"
    checks["hold_reasons"] = hard_blockers

    return {
        "sprint": n,
        "timestamp": ts,
        "goal": goal,
        "scope": scope,
        "policy": policy,
        "checks": checks,
        "carry_forward": carry_forward,
        "open_blockers": blockers,
        "verdict": checks["kickoff_verdict"],
    }

# ── Report generation ─────────────────────────────────────────────────────────

def generate_plan_packet(r: dict) -> str:
    n       = r["sprint"]
    ts      = r["timestamp"]
    verdict = r["verdict"]
    checks  = r["checks"]
    goal    = r["goal"] or "⚠️ NOT PROVIDED — pass --goal"
    scope   = r["scope"] or "⚠️ NOT PROVIDED — pass --scope"
    verdict_icon = "✅" if verdict == "KICKOFF READY" else "❌"

    def row(label, key, invert=False):
        val = checks.get(key)
        if isinstance(val, bool):
            ok = val if not invert else not val
            icon = "✅ PASS" if ok else "❌ HOLD"
        elif isinstance(val, int):
            ok = (val == 0) if not invert else (val > 0)
            icon = f"{'✅' if ok else '❌'} {val}"
        else:
            icon = str(val)
        return f"| {label} | {icon} |"

    carry_rows = ""
    for cf in r.get("carry_forward", []):
        carry_rows += f"| {cf['item']} | {cf['source']} | include / defer / drop |\n"
    if not carry_rows:
        carry_rows = "| *(none detected)* | | |\n"

    blocker_rows = ""
    for b in r.get("open_blockers", []):
        blocker_rows += f"- {b}\n"
    if not blocker_rows:
        blocker_rows = "*(none)*\n"

    hold_section = ""
    if checks.get("hold_reasons"):
        hold_section = "\n**Blockers:**\n"
        for i, h in enumerate(checks["hold_reasons"], 1):
            hold_section += f"{i}. {h}\n"

    dec_rows = ""
    for d in checks.get("required_decisions", []):
        icon = "✅" if d["frozen"] else "⚠️"
        dec_rows += f"| {d['id']} | {icon} {'frozen' if d['frozen'] else 'NOT FROZEN'} | — | {'PASS' if d['frozen'] else 'VERIFY'} |\n"
    if not dec_rows:
        dec_rows = "| *(none detected in context)* | | | |\n"

    return f"""# S{n}-PLAN-PACKET.md

**Sprint:** {n}
**Generated:** {ts}
**Verdict:** {verdict_icon} {verdict}
{hold_section}
---

## AUDIT SUMMARY

| Check | Result |
|-------|--------|
| Goal present | {'✅ PASS' if checks.get('goal_present') else '❌ HOLD'} |
| Scope present | {'✅ PASS' if checks.get('scope_present') else '❌ HOLD'} |
| Previous sprint closed | {'✅ PASS' if checks.get('previous_sprint_closed') else '❌ HOLD'} |
| Open blockers | {'✅ 0' if not checks.get('open_blocker_count') else f"❌ {checks['open_blocker_count']}"} |
| Open decisions (OD-XX) | {'✅ 0' if not checks.get('open_decision_count') else f"⚠️ {checks['open_decision_count']}"} |
| Mid-review gate task | ⚠️ Operator confirms in task breakdown |
| Final-review gate task | ⚠️ Operator confirms in task breakdown |
| Kickoff verdict | {verdict_icon} **{verdict}** |

---

## SPRINT INTENT

**Goal:** {goal}

**Scope:** {scope}

**Non-scope:** *(fill before kickoff gate)*

---

## INPUT CONTEXT

| Source | Status |
|--------|--------|
| `docs/ai/handoffs/current.md` | {'✅ found' if HANDOFF_FILE.exists() else '❌ missing'} |
| `docs/ai/state/open-items.md` | {'✅ found' if OPEN_ITEMS.exists() else '❌ missing'} |
| `docs/ai/DECISIONS.md` | {'✅ found' if DECISIONS_FILE.exists() else '❌ missing'} |
| `tools/sprint-policy.yml` | {'✅ found' if POLICY_FILE.exists() else '❌ missing'} |

---

## REQUIRED DECISIONS

| Decision | Status | Needed for | Verdict |
|----------|--------|------------|---------|
{dec_rows}
---

## CARRY-FORWARD INTAKE

| Item | Source | Proposed handling |
|------|--------|-------------------|
{carry_rows}
---

## OPEN BLOCKERS

{blocker_rows}

---

## DEPENDENCIES

- Internal: *(fill)*
- External: *(fill)*
- Tooling: *(fill)*
- Environment: *(fill)*

---

## BLOCKING RISKS

1. *(fill)*
2. *(fill)*
3. *(fill)*

---

## ACCEPTANCE CRITERIA

1. *(fill — must be testable)*
2. *(fill)*
3. *(fill)*

---

## EXIT CRITERIA

1. *(fill)*
2. *(fill)*

---

## EVIDENCE CHECKLIST

- [ ] pytest-output.txt
- [ ] vitest-output.txt
- [ ] tsc-output.txt
- [ ] lint-output.txt
- [ ] build-output.txt
- [ ] validator-output.txt
- [ ] review-summary.md
- [ ] file-manifest.txt
- [ ] sprint-specific extras *(add here)*

---

## TASK SKELETON

| Task | Title | Type | Gate |
|------|-------|------|------|
| {n}.1 | *(fill)* | implementation | — |
| {n}.M | Mid-review gate | review | mid |
| {n}.F | Final-review gate | review | final |

---

## REQUIRED GATES

- **Kickoff Gate:** must pass before implementation starts
- **Mid Review Gate:** embedded as task {n}.M — no second-half tasks before it passes
- **Final Review Gate:** embedded as task {n}.F — evidence bundle must be complete

---

## KICKOFF VERDICT

```
{verdict}
```
{hold_section}
---

*Generated by `tools/sprint-plan.py {n}` — {ts}*
"""

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/sprint-plan.py <sprint_number> [--goal 'X'] [--scope 'Y'] [--strict]")
        sys.exit(2)

    try:
        n = int(sys.argv[1])
    except ValueError:
        print(f"Error: sprint number must be integer, got '{sys.argv[1]}'")
        sys.exit(2)

    goal   = ""
    scope  = ""
    strict = "--strict" in sys.argv

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--goal" and i + 1 < len(args):
            goal = args[i + 1]; i += 2
        elif args[i] == "--scope" and i + 1 < len(args):
            scope = args[i + 1]; i += 2
        elif args[i].startswith("--goal="):
            goal = args[i][7:]; i += 1
        elif args[i].startswith("--scope="):
            scope = args[i][8:]; i += 1
        else:
            i += 1

    # Try to extract goal/scope from current.md if not passed
    if not goal or not scope:
        handoff = read(HANDOFF_FILE)
        if not goal:
            m = re.search(r'goal[:\s]+(.+)', handoff, re.IGNORECASE)
            if m:
                goal = m.group(1).strip()
        if not scope:
            m = re.search(r'scope[:\s]+(.+)', handoff, re.IGNORECASE)
            if m:
                scope = m.group(1).strip()

    print(f"[sprint-plan] Sprint {n} kickoff audit...")

    result  = audit_plan(n, goal, scope, strict)
    report  = generate_plan_packet(result)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    packet_file = OUT_DIR / f"S{n}-PLAN-PACKET.md"
    audit_file  = OUT_DIR / f"S{n}-PLAN-AUDIT.json"

    packet_file.write_text(report, encoding="utf-8")
    audit_file.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(f"[sprint-plan] Verdict: {result['verdict']}")
    if result["checks"].get("hold_reasons"):
        print(f"[sprint-plan] Blockers:")
        for h in result["checks"]["hold_reasons"]:
            print(f"  - {h}")
    print(f"[sprint-plan] Output: {packet_file.relative_to(REPO_ROOT)}")

    sys.exit(0 if result["verdict"] == "KICKOFF READY" else 1)

if __name__ == "__main__":
    main()
