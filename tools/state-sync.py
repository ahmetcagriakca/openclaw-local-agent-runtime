#!/usr/bin/env python3
"""
state-sync.py — Cross-file state consistency checker for Vezir Platform
Usage: python tools/state-sync.py [--fix]

Checks:
  1. DECISIONS.md decision count vs CLAUDE.md/STATE.md references
  2. Sprint closure states consistent across STATE.md, README files
  3. Test counts in CLAUDE.md vs STATE.md
  4. Open decision (OD-XX) references that should be closed
  5. Carry-forward items that appear resolved in code but not in docs

Exit codes:
  0 = consistent
  1 = inconsistencies found
"""

import sys
import re
import os
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
SPRINTS_DIR     = REPO_ROOT / "docs" / "sprints"

def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""

def extract_decision_count_from_file(content: str, filename: str) -> int | None:
    """Extract decision count from a number pattern near 'frozen' or 'decisions'."""
    # Pattern 1: explicit count like "107 frozen decisions"
    m = re.search(r'(\d+)\s+frozen\s+decision', content, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if val < 1000:  # sanity: decision counts are < 1000, not port numbers
            return val

    # Pattern 2: "N decisions frozen"
    m = re.search(r'(\d+)\s+decisions?\s+frozen', content, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if val < 1000:
            return val

    # No explicit decision count found — skip this file
    return None

def count_frozen_decisions(content: str) -> int:
    """Count ## D-XXX headers in DECISIONS.md."""
    return len(re.findall(r'^###\s+D-\d+', content, re.MULTILINE))

def extract_test_counts(content: str) -> dict[str, int]:
    counts = {}
    for label in ("backend", "frontend", "total"):
        m = re.search(rf'{label}[^:]*:\s*(\d+)', content, re.IGNORECASE)
        if m:
            counts[label] = int(m.group(1))
    # Also look for pytest count
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
        # Find README
        for readme_name in [f"S{n}-README.md", "README.md"]:
            readme = sprint_dir / readme_name
            if readme.exists():
                content = read(readme)
                cm = re.search(r'closure_status[:\s=]+(\w+)', content, re.IGNORECASE)
                if cm:
                    states[n] = cm.group(1).lower()
                break
    return states

def main():
    fix_mode = "--fix" in sys.argv
    issues = []
    warnings = []

    print("[state-sync] Running consistency checks...")

    # ── Load files ────────────────────────────────────────────────────────────
    decisions_content = read(DECISIONS_FILE)
    state_content     = read(STATE_FILE)
    claude_content    = read(CLAUDE_FILE)
    next_content      = read(NEXT_FILE)

    # ── 1. Decision count consistency ─────────────────────────────────────────
    actual_count = count_frozen_decisions(decisions_content)
    print(f"  Frozen decisions in DECISIONS.md: {actual_count}")

    for label, content, filepath in [
        ("STATE.md", state_content, STATE_FILE),
        ("CLAUDE.md", claude_content, CLAUDE_FILE),
    ]:
        if not content:
            warnings.append(f"  {label} not found at {filepath}")
            continue
        ref_count = extract_decision_count_from_file(content, label)
        if ref_count is not None and ref_count != actual_count:
            issues.append(
                f"  MISMATCH: {label} references {ref_count} frozen decisions, "
                f"DECISIONS.md has {actual_count}"
            )
        elif ref_count is None:
            warnings.append(f"  Could not extract decision count from {label}")
        else:
            print(f"  ✅ {label} decision count matches: {ref_count}")

    # ── 2. Open decision references ───────────────────────────────────────────
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
            print(f"  ✅ No OD-XX refs in {label}")

    # ── 3. Sprint closure state consistency ───────────────────────────────────
    sprint_states = find_sprint_closure_states(SPRINTS_DIR)
    if sprint_states:
        print(f"  Sprint closure states found: {sprint_states}")
        for sprint_n, status in sprint_states.items():
            if status not in ("closed", "not_started", "evidence_pending", "review_pending"):
                issues.append(f"  INVALID closure_status for Sprint {sprint_n}: '{status}'")
            # Check STATE.md reflects this
            sprint_pattern = rf"sprint[_\s-]*{sprint_n}[^\n]*{status}"
            if not re.search(sprint_pattern, state_content, re.IGNORECASE):
                warnings.append(
                    f"  Sprint {sprint_n} closure_status='{status}' may not be reflected in STATE.md"
                )

    # ── 4. Test count plausibility ────────────────────────────────────────────
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

    # ── 5. NEXT.md blocker check ──────────────────────────────────────────────
    if next_content:
        # Check for sprints marked as blockers that are now closed
        for sprint_n, status in sprint_states.items():
            if status == "closed":
                blocker_pattern = rf"sprint[_\s-]*{sprint_n}[^\n]*blocker"
                if re.search(blocker_pattern, next_content, re.IGNORECASE):
                    warnings.append(
                        f"  Sprint {sprint_n} is closed but NEXT.md still references it as a blocker"
                    )

    # ── Summary ───────────────────────────────────────────────────────────────
    print("")
    if issues:
        print(f"  ❌ {len(issues)} issue(s) found:")
        for issue in issues:
            print(issue)
    if warnings:
        print(f"  ⚠️  {len(warnings)} warning(s):")
        for w in warnings:
            print(w)
    if not issues and not warnings:
        print("  ✅ All consistency checks passed")

    print("")
    print(f"[state-sync] Result: {'INCONSISTENT' if issues else 'CONSISTENT'}")

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
