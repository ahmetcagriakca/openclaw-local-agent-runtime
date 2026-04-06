#!/usr/bin/env python3
"""
state-sync.py — Cross-file state consistency checker for Vezir Platform
Usage:
  python tools/state-sync.py           # Full sync check (legacy)
  python tools/state-sync.py --check   # Governed doc consistency (D-142)
  python tools/state-sync.py --fix     # (reserved, not yet implemented)

Governed document set (D-142):
  - docs/ai/handoffs/current.md
  - docs/ai/state/open-items.md
  - docs/ai/STATE.md
  - docs/ai/NEXT.md

Checks (--check mode):
  1. All 4 governed files exist
  2. Current sprint number consistent across files
  3. Last closed sprint consistent
  4. Current phase consistent
  5. Decision count consistent (DECISIONS.md vs STATE.md)

Exit codes:
  0 = consistent
  1 = inconsistencies found
"""

import sys
import re
import os
import argparse
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).parent.parent
DECISIONS_FILE  = REPO_ROOT / "docs" / "ai" / "DECISIONS.md"
STATE_FILE      = REPO_ROOT / "docs" / "ai" / "STATE.md"
CLAUDE_FILE     = REPO_ROOT / "CLAUDE.md"
NEXT_FILE       = REPO_ROOT / "docs" / "ai" / "NEXT.md"
HANDOFF_FILE    = REPO_ROOT / "docs" / "ai" / "handoffs" / "current.md"
OPEN_ITEMS_FILE = REPO_ROOT / "docs" / "ai" / "state" / "open-items.md"
SPRINTS_DIR     = REPO_ROOT / "docs" / "sprints"

GOVERNED_FILES = [HANDOFF_FILE, OPEN_ITEMS_FILE, STATE_FILE, NEXT_FILE]


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def extract_decision_counts_from_file(content: str) -> tuple[int | None, int | None]:
    """Extract frozen and superseded decision counts from governed doc.

    Returns (frozen_count, superseded_count).
    """
    frozen = None
    superseded = None

    # Pattern: "N frozen decisions + M superseded" or "N frozen + M superseded"
    m = re.search(r'(\d+)\s+frozen\s+(?:decisions?\s+)?\+\s*(\d+)\s+superseded', content, re.IGNORECASE)
    if m:
        frozen = int(m.group(1))
        superseded = int(m.group(2))
        if frozen < 1000:
            return frozen, superseded

    # Simpler: "N frozen decisions"
    m = re.search(r'(\d+)\s+frozen\s+decision', content, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if val < 1000:
            frozen = val

    return frozen, superseded


def count_decision_headers(content: str) -> int:
    """Count ### D-XXX headers in DECISIONS.md (all statuses)."""
    return len(re.findall(r'^###\s+D-\d+', content, re.MULTILINE))


def count_non_decision_headers(content: str) -> int:
    """Count reserved/reassigned entries that have ### D-XXX headers but are not real decisions."""
    return len(re.findall(r'^###\s+D-\d+.*[Rr]eserved', content, re.MULTILINE))


def extract_test_counts(content: str) -> dict[str, int]:
    counts = {}
    for label in ("backend", "frontend", "total"):
        m = re.search(rf'{label}[^:]*:\s*(\d+)', content, re.IGNORECASE)
        if m:
            counts[label] = int(m.group(1))
    m = re.search(r'(\d+)\s+passed', content)
    if m:
        counts["pytest_passed"] = int(m.group(1))
    return counts


def find_open_decisions(content: str) -> list[str]:
    return re.findall(r'\bOD-\d+\b', content)


def find_sprint_closure_states(sprints_dir: Path) -> dict[int, str]:
    """Read closure_status from each sprint README."""
    states = {}
    if not sprints_dir.exists():
        return states
    for sprint_dir in sorted(sprints_dir.iterdir()):
        if not sprint_dir.is_dir():
            continue
        m = re.search(r'sprint-(\d+)', sprint_dir.name)
        if not m:
            continue
        n = int(m.group(1))
        for readme_name in [f"S{n}-README.md", "README.md"]:
            readme = sprint_dir / readme_name
            if readme.exists():
                content = read(readme)
                cm = re.search(r'closure_status[:\s=]+(\w+)', content, re.IGNORECASE)
                if cm:
                    states[n] = cm.group(1).lower()
                break
    return states


# ── Governed doc field extractors (D-142) ────────────────────────────────────


def _strip_md_bold(text: str) -> str:
    """Remove markdown bold markers for easier regex matching."""
    return re.sub(r'\*\*', '', text)


def extract_last_closed_sprint(content: str) -> int | None:
    """Extract last closed sprint number from governed doc content."""
    clean = _strip_md_bold(content)

    # Pattern: "Last closed sprint: NN"
    m = re.search(r'[Ll]ast\s+closed\s+sprint[:\s]*(\d+)', clean)
    if m:
        return int(m.group(1))

    # Pattern: "S68 closed" or "Sprint 68 closed"
    matches = re.findall(r'[Ss](?:print\s*)?(\d+)\s+closed', clean)
    if matches:
        return max(int(x) for x in matches)

    return None


def extract_current_phase(content: str) -> int | None:
    """Extract current phase number from governed doc content."""
    clean = _strip_md_bold(content)

    # "Phase N active" or "Phase: N active"
    m = re.search(r'[Pp]hase[:\s]*(\d+)\s*active', clean)
    if m:
        return int(m.group(1))
    # "Active phase: Phase N"
    m = re.search(r'[Aa]ctive\s+phase[:\s]*[Pp]hase\s*(\d+)', clean)
    if m:
        return int(m.group(1))
    return None


def extract_next_sprint(content: str) -> int | None:
    """Extract the next sprint number from open-items or NEXT.md."""
    m = re.search(r'[Ss](\d+)\s+ready', content)
    if m:
        return int(m.group(1))
    m = re.search(r'[Nn]ext\s+[Ss]print[:\s]*\D*(\d+)', content)
    if m:
        return int(m.group(1))
    return None


# ── --check mode (D-142) ─────────────────────────────────────────────────────


def run_governed_check() -> int:
    """Run D-142 governed doc consistency check. Returns exit code."""
    issues: list[str] = []
    warnings: list[str] = []

    print("[state-sync --check] D-142 governed doc consistency check")
    print()

    # ── 1. All governed files must exist ──────────────────────────────────
    contents: dict[Path, str] = {}
    for gf in GOVERNED_FILES:
        rel = gf.relative_to(REPO_ROOT)
        c = read(gf)
        if not c:
            issues.append(f"MISSING governed file: {rel}")
        else:
            contents[gf] = c
            print(f"  OK  {rel}")

    if issues:
        # Can't do further checks with missing files
        print()
        for i in issues:
            print(f"  FAIL  {i}")
        print()
        print(f"[state-sync --check] FAIL ({len(issues)} issue(s))")
        return 1

    handoff = contents[HANDOFF_FILE]
    open_items = contents[OPEN_ITEMS_FILE]
    state = contents[STATE_FILE]
    nextmd = contents[NEXT_FILE]

    # ── 2. Last closed sprint consistency ─────────────────────────────────
    sprint_values: dict[str, int | None] = {}
    for label, content in [
        ("handoff/current.md", handoff),
        ("STATE.md", state),
    ]:
        sprint_values[label] = extract_last_closed_sprint(content)

    non_none_sprints = {k: v for k, v in sprint_values.items() if v is not None}
    if len(non_none_sprints) >= 2:
        vals = list(non_none_sprints.values())
        if len(set(vals)) > 1:
            detail = ", ".join(f"{k}={v}" for k, v in non_none_sprints.items())
            issues.append(f"SPRINT MISMATCH (last closed): {detail}")
        else:
            print(f"  OK  Last closed sprint: {vals[0]} (consistent)")
    elif non_none_sprints:
        v = list(non_none_sprints.items())[0]
        warnings.append(f"Last closed sprint found only in {v[0]}={v[1]}")
    else:
        warnings.append("Could not extract last closed sprint from any governed doc")

    # ── 3. Current phase consistency ──────────────────────────────────────
    phase_values: dict[str, int | None] = {}
    for label, content in [
        ("handoff/current.md", handoff),
        ("STATE.md", state),
    ]:
        phase_values[label] = extract_current_phase(content)

    non_none_phases = {k: v for k, v in phase_values.items() if v is not None}
    if len(non_none_phases) >= 2:
        vals = list(non_none_phases.values())
        if len(set(vals)) > 1:
            detail = ", ".join(f"{k}={v}" for k, v in non_none_phases.items())
            issues.append(f"PHASE MISMATCH: {detail}")
        else:
            print(f"  OK  Current phase: {vals[0]} (consistent)")
    elif non_none_phases:
        v = list(non_none_phases.items())[0]
        warnings.append(f"Current phase found only in {v[0]}={v[1]}")
    else:
        warnings.append("Could not extract current phase from any governed doc")

    # ── 4. NEXT.md phase consistency ──────────────────────────────────────
    next_phase = extract_current_phase(nextmd)
    state_phase = phase_values.get("STATE.md")
    if next_phase is not None and state_phase is not None:
        if next_phase != state_phase:
            issues.append(
                f"NEXT.md phase ({next_phase}) != STATE.md phase ({state_phase})"
            )
        else:
            print(f"  OK  NEXT.md phase matches STATE.md: {next_phase}")

    # ── 5. open-items next sprint vs last closed sprint ───────────────────
    oi_next = extract_next_sprint(open_items)
    last_closed = sprint_values.get("STATE.md") or sprint_values.get("handoff/current.md")
    if oi_next is not None and last_closed is not None:
        if oi_next <= last_closed:
            issues.append(
                f"open-items.md next sprint ({oi_next}) <= last closed ({last_closed}) — stale"
            )
        else:
            print(f"  OK  open-items next sprint ({oi_next}) > last closed ({last_closed})")

    # ── 6. Decision count consistency (STATE.md vs DECISIONS.md index) ───
    decisions_content = read(DECISIONS_FILE)
    if decisions_content:
        dec_frozen, dec_superseded = extract_decision_counts_from_file(decisions_content)
        state_frozen, state_superseded = extract_decision_counts_from_file(state)
        if dec_frozen is not None and state_frozen is not None:
            if dec_frozen != state_frozen or (dec_superseded or 0) != (state_superseded or 0):
                issues.append(
                    f"DECISION COUNT MISMATCH: DECISIONS.md says frozen={dec_frozen} "
                    f"superseded={dec_superseded or 0}, "
                    f"STATE.md says frozen={state_frozen} superseded={state_superseded or 0}"
                )
            else:
                print(f"  OK  Decision count: {dec_frozen} frozen + {dec_superseded or 0} superseded (consistent)")
        elif state_frozen is None:
            warnings.append("Could not extract decision count from STATE.md")

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    if warnings:
        for w in warnings:
            print(f"  WARN  {w}")
    if issues:
        for i in issues:
            print(f"  FAIL  {i}")
        print()
        print(f"[state-sync --check] FAIL ({len(issues)} issue(s), {len(warnings)} warning(s))")
        return 1
    else:
        print(f"[state-sync --check] PASS ({len(warnings)} warning(s))")
        return 0


# ── Legacy full sync mode ────────────────────────────────────────────────────


def run_legacy_sync() -> int:
    """Original state-sync checks. Returns exit code."""
    issues: list[str] = []
    warnings: list[str] = []

    print("[state-sync] Running consistency checks...")

    decisions_content = read(DECISIONS_FILE)
    state_content     = read(STATE_FILE)
    claude_content    = read(CLAUDE_FILE)
    next_content      = read(NEXT_FILE)

    # 1. Decision count consistency (compare claims across files)
    dec_frozen, dec_superseded = extract_decision_counts_from_file(decisions_content)
    if dec_frozen is not None:
        print(f"  DECISIONS.md claims: {dec_frozen} frozen + {dec_superseded or 0} superseded")

    for label, content, filepath in [
        ("STATE.md", state_content, STATE_FILE),
        ("CLAUDE.md", claude_content, CLAUDE_FILE),
    ]:
        if not content:
            warnings.append(f"  {label} not found at {filepath}")
            continue
        frozen, superseded = extract_decision_counts_from_file(content)
        if frozen is not None and dec_frozen is not None:
            if frozen != dec_frozen or (superseded or 0) != (dec_superseded or 0):
                issues.append(
                    f"  MISMATCH: {label} says frozen={frozen} superseded={superseded or 0}, "
                    f"DECISIONS.md says frozen={dec_frozen} superseded={dec_superseded or 0}"
                )
            else:
                print(f"  OK {label} decision count matches")
        elif frozen is None:
            warnings.append(f"  Could not extract decision count from {label}")

    # 2. Open decision references
    for label, content in [
        ("STATE.md", state_content),
        ("CLAUDE.md", claude_content),
        ("NEXT.md", next_content),
        ("DECISIONS.md", decisions_content),
    ]:
        od_refs = find_open_decisions(content)
        if od_refs:
            warnings.append(f"  Open decision refs in {label}: {', '.join(set(od_refs))}")
        else:
            print(f"  OK No OD-XX refs in {label}")

    # 3. Sprint closure state consistency
    sprint_states = find_sprint_closure_states(SPRINTS_DIR)
    if sprint_states:
        print(f"  Sprint closure states found: {sprint_states}")
        for sprint_n, status in sprint_states.items():
            if status not in ("closed", "not_started", "evidence_pending", "review_pending"):
                issues.append(f"  INVALID closure_status for Sprint {sprint_n}: '{status}'")
            sprint_pattern = rf"sprint[_\s-]*{sprint_n}[^\n]*{status}"
            if not re.search(sprint_pattern, state_content, re.IGNORECASE):
                warnings.append(
                    f"  Sprint {sprint_n} closure_status='{status}' may not be reflected in STATE.md"
                )

    # 4. Test count plausibility
    state_tests = extract_test_counts(state_content)
    claude_tests = extract_test_counts(claude_content)
    if state_tests and claude_tests:
        for key in ("backend", "total"):
            sv = state_tests.get(key)
            cv = claude_tests.get(key)
            if sv and cv and abs(sv - cv) > 5:
                issues.append(
                    f"  TEST COUNT MISMATCH ({key}): STATE.md={sv}, CLAUDE.md={cv} (delta={abs(sv-cv)})"
                )

    # 5. NEXT.md blocker check
    if next_content:
        for sprint_n, status in sprint_states.items():
            if status == "closed":
                blocker_pattern = rf"sprint[_\s-]*{sprint_n}[^\n]*blocker"
                if re.search(blocker_pattern, next_content, re.IGNORECASE):
                    warnings.append(
                        f"  Sprint {sprint_n} is closed but NEXT.md still references it as a blocker"
                    )

    # Summary
    print("")
    if issues:
        print(f"  {len(issues)} issue(s) found:")
        for issue in issues:
            print(issue)
    if warnings:
        print(f"  {len(warnings)} warning(s):")
        for w in warnings:
            print(w)
    if not issues and not warnings:
        print("  All consistency checks passed")

    print("")
    print(f"[state-sync] Result: {'INCONSISTENT' if issues else 'CONSISTENT'}")

    return 1 if issues else 0


def main():
    parser = argparse.ArgumentParser(description="Vezir state consistency checker")
    parser.add_argument("--check", action="store_true",
                        help="D-142 governed doc consistency check")
    parser.add_argument("--fix", action="store_true",
                        help="(reserved) auto-fix mode")
    args = parser.parse_args()

    if args.check:
        sys.exit(run_governed_check())
    else:
        sys.exit(run_legacy_sync())


if __name__ == "__main__":
    main()
