#!/usr/bin/env bash
# sprint-plan.sh — Sprint kickoff planning for Vezir Platform
#
# Usage:
#   ./tools/sprint-plan.sh <sprint_number> [--goal "X"] [--scope "Y"] [--strict]
#
# What it does:
#   1. Verifies previous sprint is closed
#   2. Checks open blockers and decisions
#   3. Runs sprint-plan.py to produce S{N}-PLAN-PACKET.md
#   4. Prints verdict: KICKOFF READY or KICKOFF BLOCKED
#
# Output:
#   docs/review-packets/S{N}-PLAN-PACKET.md   — operator review entry point
#   docs/review-packets/S{N}-PLAN-AUDIT.json  — machine-readable audit

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Args ──────────────────────────────────────────────────────────────────────

SPRINT=""
GOAL=""
SCOPE=""
STRICT=""

i=1
while [[ $i -le $# ]]; do
    arg="${!i}"
    case "$arg" in
        --goal)
            i=$((i+1)); GOAL="${!i}";;
        --scope)
            i=$((i+1)); SCOPE="${!i}";;
        --goal=*)
            GOAL="${arg#--goal=}";;
        --scope=*)
            SCOPE="${arg#--scope=}";;
        --strict)
            STRICT="--strict";;
        [0-9]*)
            SPRINT="$arg";;
    esac
    i=$((i+1))
done

if [[ -z "$SPRINT" ]]; then
    echo "Usage: ./tools/sprint-plan.sh <sprint_number> [--goal 'X'] [--scope 'Y'] [--strict]"
    exit 2
fi

echo "════════════════════════════════════════════════════════════"
echo "  sprint-plan.sh — Sprint $SPRINT Kickoff Audit"
echo "  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "════════════════════════════════════════════════════════════"

PASS=0; FAIL=0

check_pass() { echo "  ✅ $1"; ((PASS++)) || true; }
check_fail() { echo "  ❌ $1"; ((FAIL++)) || true; }
check_warn() { echo "  ⚠️  $1"; }

# ── 1. Python ─────────────────────────────────────────────────────────────────

echo ""
echo "── Step 1: Environment"
command -v python3 &>/dev/null && check_pass "python3: $(python3 --version 2>&1)" \
    || { check_fail "python3 not found"; exit 1; }

# ── 2. Context files ──────────────────────────────────────────────────────────

echo ""
echo "── Step 2: Context files"

HANDOFF="$REPO_ROOT/docs/ai/handoffs/current.md"
OPEN_ITEMS="$REPO_ROOT/docs/ai/state/open-items.md"

[[ -f "$HANDOFF" ]]    && check_pass "current.md found"    || check_warn "current.md missing — context will be thin"
[[ -f "$OPEN_ITEMS" ]] && check_pass "open-items.md found" || check_warn "open-items.md missing"

# ── 3. Previous sprint closure ────────────────────────────────────────────────

echo ""
echo "── Step 3: Previous sprint closure"

PREV=$((SPRINT - 1))
PREV_CLOSED=false

if [[ "$PREV" -ge 1 ]]; then
    PREV_README="$REPO_ROOT/docs/sprints/sprint-${PREV}/S${PREV}-README.md"
    if [[ -f "$PREV_README" ]]; then
    STATUS=$(grep -i "closure_status" "$PREV_README" 2>/dev/null | head -1 | sed 's/.*closure_status[*: =]*//i' | awk '{print $1}' | tr -d '*:' || true)
        if [[ "$STATUS" == "closed" ]]; then
            check_pass "Sprint $PREV: closure_status=closed"
            PREV_CLOSED=true
        else
            check_fail "Sprint $PREV: closure_status='$STATUS' — must be 'closed' before Sprint $SPRINT starts"
        fi
    else
        # Fallback: check STATE.md
        STATE="$REPO_ROOT/docs/ai/STATE.md"
        if [[ -f "$STATE" ]] && grep -qi "sprint.*${PREV}.*closed" "$STATE" 2>/dev/null; then
            check_pass "Sprint $PREV closed (from STATE.md)"
            PREV_CLOSED=true
        else
            check_warn "Sprint $PREV README not found — cannot verify closure"
        fi
    fi
else
    check_pass "No previous sprint to check"
    PREV_CLOSED=true
fi

# ── 4. Open blockers ──────────────────────────────────────────────────────────

echo ""
echo "── Step 4: Open blockers"

if [[ -f "$OPEN_ITEMS" ]]; then
    BLOCKER_COUNT=$(grep -c "^\|" "$OPEN_ITEMS" 2>/dev/null | head -1 || echo 0)
    # More precise: count non-header, non-separator rows in Active Blockers section
    IN_BLOCKER=false
    ACTUAL_BLOCKERS=0
    while IFS= read -r line; do
        if echo "$line" | grep -qi "active blocker"; then
            IN_BLOCKER=true; continue
        fi
        if $IN_BLOCKER && echo "$line" | grep -q "^#"; then
            break
        fi
        if $IN_BLOCKER && echo "$line" | grep -q "^\|" && ! echo "$line" | grep -q "^|---"; then
            if ! echo "$line" | grep -qi "^| #\|^| Item"; then
                ACTUAL_BLOCKERS=$((ACTUAL_BLOCKERS + 1))
            fi
        fi
    done < "$OPEN_ITEMS"

    if [[ "$ACTUAL_BLOCKERS" -eq 0 ]]; then
        check_pass "No active blockers in open-items.md"
    else
        check_fail "$ACTUAL_BLOCKERS active blocker(s) in open-items.md — must resolve before kickoff"
    fi
else
    check_warn "open-items.md not found — blocker check skipped"
fi

# ── 5. Open decisions ─────────────────────────────────────────────────────────

echo ""
echo "── Step 5: Open decisions (OD-XX)"

OD_COUNT=0
for f in "$HANDOFF" "$OPEN_ITEMS"; do
    if [[ -f "$f" ]]; then
        N=$(grep -oc 'OD-[0-9]' "$f" 2>/dev/null || true)
        N="${N:-0}"
        OD_COUNT=$((OD_COUNT + N))
    fi
done

if [[ "$OD_COUNT" -eq 0 ]]; then
    check_pass "No OD-XX open decision references"
elif [[ "$OD_COUNT" -le 2 ]]; then
    check_warn "$OD_COUNT OD-XX reference(s) — within limit of 2"
else
    check_fail "$OD_COUNT OD-XX references exceed limit of 2"
fi

# ── 6. Goal and scope ─────────────────────────────────────────────────────────

echo ""
echo "── Step 6: Goal and scope"

if [[ -n "$GOAL" ]]; then
    check_pass "Goal provided: '$GOAL'"
else
    # Try to extract from current.md
    if [[ -f "$HANDOFF" ]]; then
        EXTRACTED=$(grep -i "^.*goal.*:.*" "$HANDOFF" 2>/dev/null | head -1 | sed 's/.*goal.*://i' | xargs || true)
        [[ -n "$EXTRACTED" ]] && check_warn "Goal not passed via --goal. Extracted from current.md: '$EXTRACTED'" \
            || check_warn "Goal not provided. Pass --goal or populate current.md."
    else
        check_warn "Goal not provided. Pass --goal."
    fi
fi

if [[ -n "$SCOPE" ]]; then
    check_pass "Scope provided: '$SCOPE'"
else
    check_warn "Scope not provided. Pass --scope or populate current.md."
fi

# ── 7. Run sprint-plan.py ─────────────────────────────────────────────────────

echo ""
echo "── Step 7: Running sprint-plan.py"

PLAN_SCRIPT="$SCRIPT_DIR/sprint-plan.py"
if [[ ! -f "$PLAN_SCRIPT" ]]; then
    check_fail "sprint-plan.py not found at $PLAN_SCRIPT"
    exit 1
fi

PY_ARGS=("$SPRINT")
[[ -n "$GOAL" ]]   && PY_ARGS+=("--goal" "$GOAL")
[[ -n "$SCOPE" ]]  && PY_ARGS+=("--scope" "$SCOPE")
[[ -n "$STRICT" ]] && PY_ARGS+=("--strict")

set +e
PLAN_OUTPUT=$(python3 "$PLAN_SCRIPT" "${PY_ARGS[@]}" 2>&1)
PLAN_EXIT=$?
set -e

echo "$PLAN_OUTPUT"

if [[ "$PLAN_EXIT" -eq 0 ]]; then
    check_pass "sprint-plan.py: KICKOFF READY"
else
    check_fail "sprint-plan.py: KICKOFF BLOCKED"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  SUMMARY — Sprint $SPRINT Kickoff"
echo "════════════════════════════════════════════════════════════"
echo "  Passed: $PASS  |  Failed: $FAIL"
echo ""

PACKET="$REPO_ROOT/docs/review-packets/S${SPRINT}-PLAN-PACKET.md"
if [[ -f "$PACKET" ]]; then
    echo "  📄 Plan packet: docs/review-packets/S${SPRINT}-PLAN-PACKET.md"
    echo ""
    echo "  → Send this single file for kickoff gate review."
    echo "  → Reviewer returns: PASS | HOLD + patch list"
    echo "  → closure_status=closed is NEVER set by this tool."
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
    echo "  ✅ KICKOFF READY — eligible for kickoff gate review"
    exit 0
else
    echo "  ❌ KICKOFF BLOCKED — $FAIL check(s) failed"
    echo "     Fix blockers, then re-run: ./tools/sprint-plan.sh $SPRINT"
    exit 1
fi
