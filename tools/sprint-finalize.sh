#!/usr/bin/env bash
# sprint-finalize.sh — Sprint closure finalization for Vezir Platform
#
# Usage:
#   ./tools/sprint-finalize.sh <sprint_number> [--model A|B] [--skip-tests]
#
# What it does:
#   1. Verifies evidence directory exists and files are non-empty
#   2. Runs sprint-audit.py to produce S{N}-REVIEW-PACKET.md
#   3. Prints the verdict and review packet path
#   4. Exits 0 if ELIGIBLE, 1 if NOT CLOSEABLE
#
# Output:
#   docs/review-packets/S{N}-REVIEW-PACKET.md   — operator review entry point
#   docs/review-packets/S{N}-AUDIT-RESULT.json  — machine-readable audit result
#
# After this runs, operator sends only S{N}-REVIEW-PACKET.md for review.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Args ──────────────────────────────────────────────────────────────────────

SPRINT=""
MODEL="B"
SKIP_TESTS=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)
            shift; MODEL="${1:-B}"; shift;;
        --model=*)
            MODEL="${1#--model=}"; shift;;
        --skip-tests)
            SKIP_TESTS=true; shift;;
        [0-9]*)
            SPRINT="$1"; shift;;
        *)
            shift;;
    esac
done

if [[ -z "$SPRINT" ]]; then
    echo "Usage: ./tools/sprint-finalize.sh <sprint_number> [--model A|B] [--skip-tests]"
    exit 2
fi

echo "════════════════════════════════════════════════════════════"
echo "  sprint-finalize.sh — Sprint $SPRINT (Model $MODEL)"
echo "  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "════════════════════════════════════════════════════════════"

PASS=0
FAIL=0

check_pass() { echo "  ✅ $1"; ((PASS++)) || true; }
check_fail() { echo "  ❌ $1"; ((FAIL++)) || true; }
check_warn() { echo "  ⚠️  $1"; }

# ── 1. Python availability ────────────────────────────────────────────────────

echo ""
echo "── Step 1: Environment check"
if command -v python3 &>/dev/null; then
    check_pass "python3 available: $(python3 --version 2>&1)"
else
    check_fail "python3 not found — required for sprint-audit.py"
    exit 1
fi

# ── 1b. Policy enforcement (fail-fast before all other checks) ────────────────

echo ""
echo "── Step 1b: Policy check (sprint-policy.yml)"

POLICY_FILE="$SCRIPT_DIR/sprint-policy.yml"
if [[ -f "$POLICY_FILE" ]]; then
    FORCED=$(python3 - <<PYEOF 2>/dev/null
import re, sys
content = open("$POLICY_FILE").read()
block = re.search(r'^\s+${SPRINT}:\s*\n((?:\s{4,}[^\n]+\n?)*)', content, re.MULTILINE)
if block:
    m = re.search(r'forced_model:\s*"([AB])"', block.group(1))
    if m: print(m.group(1))
PYEOF
    )
    if [[ -n "$FORCED" && "$FORCED" != "$MODEL" ]]; then
        REASON=$(python3 - <<PYEOF 2>/dev/null
import re
content = open("$POLICY_FILE").read()
block = re.search(r'^\s+${SPRINT}:\s*\n((?:\s{4,}[^\n]+\n?)*)', content, re.MULTILINE)
if block:
    m = re.search(r'reason:\s*"([^"]+)"', block.group(1))
    if m: print(m.group(1))
PYEOF
        )
        echo "  ❌ POLICY VIOLATION: Sprint $SPRINT requires --model $FORCED, you passed --model $MODEL"
        echo "     Reason: $REASON"
        echo "     Fix: ./tools/sprint-finalize.sh $SPRINT --model $FORCED"
        echo ""
        echo "  ❌ NOT CLOSEABLE — policy violation (exit 1)"
        exit 1
    elif [[ -n "$FORCED" ]]; then
        check_pass "Model $MODEL confirmed by sprint-policy.yml"
    else
        check_pass "No forced model for Sprint $SPRINT — Model $MODEL accepted"
    fi
else
    check_warn "sprint-policy.yml not found — no policy enforcement"
fi

# ── 2. Evidence directory ─────────────────────────────────────────────────────

echo ""
echo "── Step 2: Evidence directory"

EV_DIR=""
for tmpl in "evidence/sprint-${SPRINT}" "docs/sprints/sprint-${SPRINT}/evidence"; do
    CANDIDATE="$REPO_ROOT/$tmpl"
    if [[ -d "$CANDIDATE" ]]; then
        EV_DIR="$CANDIDATE"
        break
    fi
done

if [[ -z "$EV_DIR" ]]; then
    check_fail "Evidence directory not found (checked evidence/sprint-$SPRINT and docs/sprints/sprint-$SPRINT/evidence)"
    FAIL=$((FAIL + 1))
else
    check_pass "Evidence directory: $EV_DIR"
    FILE_COUNT=$(find "$EV_DIR" -maxdepth 2 -type f | wc -l | tr -d ' ')
    check_pass "Evidence file count: $FILE_COUNT"

    # Empty file check
    EMPTY_COUNT=0
    while IFS= read -r -d '' f; do
        if [[ ! -s "$f" ]]; then
            check_fail "Empty evidence file: $(basename "$f")"
            EMPTY_COUNT=$((EMPTY_COUNT + 1))
        fi
    done < <(find "$EV_DIR" -maxdepth 2 -type f -print0)

    if [[ "$EMPTY_COUNT" -eq 0 ]]; then
        check_pass "All evidence files non-empty"
    fi
fi

# ── 3. Sprint doc directory ───────────────────────────────────────────────────

echo ""
echo "── Step 3: Sprint doc directory"

SPRINT_DIR="$REPO_ROOT/docs/sprints/sprint-$SPRINT"
if [[ -d "$SPRINT_DIR" ]]; then
    check_pass "Sprint docs: $SPRINT_DIR"
else
    check_fail "Sprint doc directory missing: docs/sprints/sprint-$SPRINT"
fi

# ── 4. Canonical files ────────────────────────────────────────────────────────

echo ""
echo "── Step 4: Canonical files"

REQUIRED_CANONICAL=("S${SPRINT}-README.md" "S${SPRINT}-RETROSPECTIVE.md" "S${SPRINT}-CLOSURE-CONFIRMATION.md")
OPTIONAL_CANONICAL=("S${SPRINT}-CLOSURE-SUMMARY.md" "S${SPRINT}-EVIDENCE-AUDIT-RESULT.md")

for f in "${REQUIRED_CANONICAL[@]}"; do
    if [[ -f "$SPRINT_DIR/$f" ]]; then
        check_pass "Required canonical: $f"
    else
        check_fail "Missing required canonical: $f"
    fi
done

for f in "${OPTIONAL_CANONICAL[@]}"; do
    if [[ -f "$SPRINT_DIR/$f" ]]; then
        check_pass "Optional canonical: $f"
    else
        check_warn "Optional canonical absent: $f"
    fi
done

# ── 5. Retrospective check (never waivable) ───────────────────────────────────

echo ""
echo "── Step 5: Retrospective (never waivable)"

RETRO="$SPRINT_DIR/S${SPRINT}-RETROSPECTIVE.md"
if [[ -f "$RETRO" ]]; then
    RETRO_LINES=$(wc -l < "$RETRO")
    if [[ "$RETRO_LINES" -lt 10 ]]; then
        check_fail "Retrospective too short ($RETRO_LINES lines) — must be substantive"
    else
        check_pass "Retrospective present ($RETRO_LINES lines)"
    fi
else
    check_fail "RETROSPECTIVE MISSING — this is never waivable. Sprint cannot close."
fi

# ── 6. Stale language scan ────────────────────────────────────────────────────

echo ""
echo "── Step 6: Stale language scan"

STALE_TERMS=("CODE-COMPLETE" "COMPLETE" "fully validated" "sorunsuz")
STALE_FOUND=0

for term in "${STALE_TERMS[@]}"; do
    HITS=$(grep -r "$term" "$SPRINT_DIR" --include="*.md" -l 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$HITS" -gt 0 ]]; then
        check_warn "Stale term '$term' found in $HITS file(s)"
        STALE_FOUND=$((STALE_FOUND + 1))
    fi
done

if [[ "$STALE_FOUND" -eq 0 ]]; then
    check_pass "No stale language detected"
fi

# ── 7. Archive candidate check ────────────────────────────────────────────────

echo ""
echo "── Step 7: Archive candidates"

ARCHIVE_ISSUES=0
for f in $(find "$SPRINT_DIR" -name "*advance-plan*" -o -name "*ADVANCE-PLAN*" 2>/dev/null); do
    if grep -qi "HISTORICAL" "$f" 2>/dev/null; then
        check_pass "Advance plan annotated as historical: $(basename "$f")"
    else
        check_warn "Advance plan NOT annotated as historical: $(basename "$f") — add HISTORICAL marker"
        ARCHIVE_ISSUES=$((ARCHIVE_ISSUES + 1))
    fi
done

if [[ "$ARCHIVE_ISSUES" -eq 0 ]] && [[ -z "$(find "$SPRINT_DIR" -name "*advance-plan*" -o -name "*ADVANCE-PLAN*" 2>/dev/null)" ]]; then
    check_pass "No unmarked advance plans"
fi

# ── 8. Optional: test run ─────────────────────────────────────────────────────

if [[ "$SKIP_TESTS" == false ]]; then
    echo ""
    echo "── Step 8: Test baseline (quick check)"

    if command -v pytest &>/dev/null; then
        echo "  Running pytest --tb=no -q ..."
        if pytest --tb=no -q "$REPO_ROOT/agent/tests" 2>&1 | tail -3; then
            check_pass "pytest completed (check output above for failures)"
        else
            check_warn "pytest returned non-zero — verify test results"
        fi
    else
        check_warn "pytest not in PATH — skipping test run (use --skip-tests to suppress this)"
    fi
else
    echo ""
    echo "── Step 8: Test run skipped (--skip-tests)"
fi

# ── 9. Run sprint-audit.py ────────────────────────────────────────────────────

echo ""
echo "── Step 9: Running sprint-audit.py"

AUDIT_SCRIPT="$SCRIPT_DIR/sprint-audit.py"
if [[ ! -f "$AUDIT_SCRIPT" ]]; then
    check_fail "sprint-audit.py not found at $AUDIT_SCRIPT"
    FAIL=$((FAIL + 1))
else
    set +e
    AUDIT_OUTPUT=$(python3 "$AUDIT_SCRIPT" "$SPRINT" --model "$MODEL" 2>&1)
    AUDIT_EXIT=$?
    set -e

    echo "$AUDIT_OUTPUT"

    if [[ "$AUDIT_EXIT" -eq 0 ]]; then
        check_pass "sprint-audit.py: ELIGIBLE FOR CLOSURE REVIEW"
    else
        check_fail "sprint-audit.py: NOT CLOSEABLE (exit $AUDIT_EXIT)"
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  SUMMARY — Sprint $SPRINT"
echo "════════════════════════════════════════════════════════════"
echo "  Passed checks:  $PASS"
echo "  Failed checks:  $FAIL"
echo ""

PACKET="$REPO_ROOT/docs/review-packets/S${SPRINT}-REVIEW-PACKET.md"
if [[ -f "$PACKET" ]]; then
    echo "  📄 Review packet: docs/review-packets/S${SPRINT}-REVIEW-PACKET.md"
    echo ""
    echo "  → Send this single file for operator review."
    echo "  → Operator returns: PASS | HOLD | patch list"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
    echo "  ✅ ELIGIBLE FOR CLOSURE REVIEW"
    exit 0
else
    echo "  ❌ NOT CLOSEABLE — $FAIL check(s) failed"
    echo "     Fix blockers, then re-run: ./tools/sprint-finalize.sh $SPRINT"
    exit 1
fi
