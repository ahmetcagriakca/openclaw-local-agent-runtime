#!/usr/bin/env python3
"""
tools/doc_drift_check.py — Documentation drift checker for closure pipeline.

Checks:
  1. DECISIONS.md heading completeness (all D-XXX headings accounted for)
  2. Decision count consistency (DECISIONS.md vs STATE.md claim)
  3. Test count consistency (actual pytest/vitest counts vs STATE.md & CLAUDE.md claims)

Usage:
  python tools/doc_drift_check.py [--skip-tests]

Exit code: number of failures (0 = all pass).
"""

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECISIONS_MD = os.path.join(REPO_ROOT, "docs", "ai", "DECISIONS.md")
STATE_MD = os.path.join(REPO_ROOT, "docs", "ai", "STATE.md")
CLAUDE_MD = os.path.join(REPO_ROOT, "CLAUDE.md")

fail_count = 0


def log(msg: str) -> None:
    print(msg)


def pass_check(msg: str) -> None:
    log(f"  PASS: {msg}")


def fail_check(msg: str) -> None:
    global fail_count
    fail_count += 1
    log(f"  FAIL: {msg}")


def warn_check(msg: str) -> None:
    log(f"  WARN: {msg}")


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Check 1: DECISIONS.md heading completeness ──────────────────────

def check_decision_headings():
    """Verify every D-XXX mentioned in DECISIONS.md has a ### heading,
    and find gaps in the sequence."""
    log("[1] DECISIONS.md heading completeness")

    text = read_file(DECISIONS_MD)

    # Extract all D-XXX from ### headings
    heading_ids = set()
    for m in re.finditer(r"^### (D-\d{3})", text, re.MULTILINE):
        heading_ids.add(m.group(1))

    if not heading_ids:
        fail_check("No D-XXX headings found in DECISIONS.md")
        return

    # Determine range
    nums = sorted(int(d.split("-")[1]) for d in heading_ids)
    max_id = nums[-1]
    min_id = nums[0]

    # Known skips (D-126 is explicitly skipped per the file)
    known_skips = set()
    if re.search(r"D-126.*skipped|skipped.*D-126", text, re.IGNORECASE):
        known_skips.add(126)

    # Check for gaps
    missing = []
    for i in range(min_id, max_id + 1):
        if i in known_skips:
            continue
        d_id = f"D-{i:03d}"
        if d_id not in heading_ids:
            missing.append(d_id)

    if missing:
        fail_check(f"Missing headings in D-{min_id:03d}..D-{max_id:03d}: {', '.join(missing)}")
    else:
        skip_note = f" (known skips: {', '.join(f'D-{s:03d}' for s in sorted(known_skips))})" if known_skips else ""
        pass_check(f"{len(heading_ids)} headings found, D-{min_id:03d}..D-{max_id:03d} complete{skip_note}")


# ── Check 2: Decision count consistency ──────────────────────────────

def check_decision_count_vs_state():
    """Compare actual D-XXX heading count against STATE.md's claim."""
    log("[2] Decision count: DECISIONS.md vs STATE.md")

    decisions_text = read_file(DECISIONS_MD)
    state_text = read_file(STATE_MD)

    # Count actual headings
    actual_headings = re.findall(r"^### D-\d{3}", decisions_text, re.MULTILINE)
    actual_count = len(actual_headings)

    # Parse STATE.md claim — look for "N frozen decisions" or "N frozen + M superseded"
    state_match = re.search(r"(\d+)\s+frozen\s+(?:decisions\s*\+\s*(\d+)\s+superseded|\+\s*(\d+)\s+superseded|decisions)", state_text)
    if not state_match:
        warn_check("Could not find 'N frozen decisions' claim in STATE.md")
        return

    frozen_count = int(state_match.group(1))
    superseded_count = int(state_match.group(2) or state_match.group(3) or 0)

    # Count deferred decisions (headings with Status: Deferred)
    deferred_count = len(re.findall(r"Status:\s*Deferred", decisions_text, re.IGNORECASE))

    # Total claimed = frozen + superseded + deferred
    claimed_total = frozen_count + superseded_count + deferred_count

    if actual_count == claimed_total:
        pass_check(f"STATE.md total ({frozen_count} frozen + {superseded_count} superseded + {deferred_count} deferred = {claimed_total}) matches DECISIONS.md headings ({actual_count})")
    elif actual_count == frozen_count:
        pass_check(f"STATE.md claims {frozen_count} frozen decisions, DECISIONS.md has {actual_count} headings")
    else:
        fail_check(f"STATE.md claims {frozen_count} frozen + {superseded_count} superseded + {deferred_count} deferred = {claimed_total}, but DECISIONS.md has {actual_count} headings")

    # Also check the D-XXX range claim in STATE.md
    range_match = re.search(r"D-001.*?D-(\d{3})", state_text)
    if range_match:
        claimed_max = int(range_match.group(1))
        heading_ids_list = re.findall(r"^### D-(\d{3})", decisions_text, re.MULTILINE)
        actual_nums = sorted(int(n) for n in heading_ids_list)
        actual_max = max(actual_nums) if actual_nums else 0
        if actual_max == claimed_max:
            pass_check(f"STATE.md range claim D-001..D-{claimed_max:03d} matches actual max D-{actual_max:03d}")
        else:
            fail_check(f"STATE.md claims range up to D-{claimed_max:03d}, but actual max heading is D-{actual_max:03d}")


# ── Check 3: Test count consistency ──────────────────────────────────

def get_actual_backend_count() -> int | None:
    """Run pytest --co -q to get collected test count."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--co", "-q"],
            capture_output=True, text=True, timeout=60,
            cwd=os.path.join(REPO_ROOT, "agent"),
        )
        # Last line like "618 tests collected"
        for line in result.stdout.strip().splitlines()[::-1]:
            m = re.search(r"(\d+)\s+test", line)
            if m:
                return int(m.group(1))
    except Exception as e:
        warn_check(f"Could not run pytest: {e}")
    return None


def get_actual_frontend_count() -> int | None:
    """Run vitest list to count frontend tests."""
    try:
        result = subprocess.run(
            ["npx", "vitest", "list"],
            capture_output=True, text=True, timeout=60,
            cwd=os.path.join(REPO_ROOT, "frontend"),
            shell=True,
        )
        # Count non-empty lines (each line is a test)
        lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
        if lines:
            return len(lines)
    except Exception as e:
        warn_check(f"Could not run vitest: {e}")
    return None


def extract_test_claims(text: str, source_name: str) -> dict:
    """Extract backend/frontend test count claims from a doc."""
    claims = {}
    # Patterns like "618 tests" or "Backend (618 tests)" or "618 tests, 0 fail"
    backend_m = re.search(r"[Bb]ackend.*?(\d{2,})\s+tests", text)
    if backend_m:
        claims["backend"] = int(backend_m.group(1))

    frontend_m = re.search(r"[Ff]rontend.*?(\d{2,})\s+tests", text)
    if frontend_m:
        claims["frontend"] = int(frontend_m.group(1))

    return claims


def check_test_counts(skip_tests: bool = False):
    """Compare actual test counts against STATE.md and CLAUDE.md claims."""
    log("[3] Test count consistency")

    state_text = read_file(STATE_MD)
    claude_text = read_file(CLAUDE_MD)

    # Get the latest claims from STATE.md (last row of test evidence table)
    # Find all rows with test counts, take the last one
    state_rows = re.findall(r"\|\s*Sprint\s+\d+\s*\|\s*(\d+)\s+tests.*?\|\s*(\d+)\s+tests", state_text)
    if state_rows:
        last_row = state_rows[-1]
        state_backend = int(last_row[0])
        state_frontend = int(last_row[1])
    else:
        warn_check("Could not parse test evidence table from STATE.md")
        state_backend = state_frontend = None

    # CLAUDE.md claims
    claude_claims = extract_test_claims(claude_text, "CLAUDE.md")
    claude_backend = claude_claims.get("backend")
    claude_frontend = claude_claims.get("frontend")

    # Cross-check STATE.md vs CLAUDE.md first (no test run needed)
    if state_backend is not None and claude_backend is not None:
        if state_backend == claude_backend:
            pass_check(f"Backend count: STATE.md ({state_backend}) == CLAUDE.md ({claude_backend})")
        else:
            fail_check(f"Backend count mismatch: STATE.md says {state_backend}, CLAUDE.md says {claude_backend}")

    if state_frontend is not None and claude_frontend is not None:
        if state_frontend == claude_frontend:
            pass_check(f"Frontend count: STATE.md ({state_frontend}) == CLAUDE.md ({claude_frontend})")
        else:
            fail_check(f"Frontend count mismatch: STATE.md says {state_frontend}, CLAUDE.md says {claude_frontend}")

    if skip_tests:
        log("  (--skip-tests: skipping actual test collection)")
        return

    # Run actual counts
    actual_backend = get_actual_backend_count()
    actual_frontend = get_actual_frontend_count()

    if actual_backend is not None:
        claimed = state_backend or claude_backend
        if claimed is not None:
            if actual_backend >= claimed:
                pass_check(f"Actual backend tests ({actual_backend}) >= documented ({claimed})")
            else:
                fail_check(f"Actual backend tests ({actual_backend}) < documented ({claimed}) — docs claim more tests than exist")
        else:
            log(f"  INFO: Actual backend tests: {actual_backend} (no doc claim to compare)")
    else:
        warn_check("Could not determine actual backend test count")

    if actual_frontend is not None:
        claimed = state_frontend or claude_frontend
        if claimed is not None:
            if actual_frontend >= claimed:
                pass_check(f"Actual frontend tests ({actual_frontend}) >= documented ({claimed})")
            else:
                fail_check(f"Actual frontend tests ({actual_frontend}) < documented ({claimed}) — docs claim more tests than exist")
        else:
            log(f"  INFO: Actual frontend tests: {actual_frontend} (no doc claim to compare)")
    else:
        warn_check("Could not determine actual frontend test count")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    skip_tests = "--skip-tests" in sys.argv

    log("=" * 60)
    log("Documentation Drift Check")
    log("=" * 60)
    log("")

    check_decision_headings()
    log("")
    check_decision_count_vs_state()
    log("")
    check_test_counts(skip_tests=skip_tests)
    log("")

    log("=" * 60)
    if fail_count == 0:
        log("RESULT: ALL CHECKS PASSED")
    else:
        log(f"RESULT: {fail_count} CHECK(S) FAILED")
    log("=" * 60)

    sys.exit(fail_count)


if __name__ == "__main__":
    main()
