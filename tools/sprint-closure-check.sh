#!/bin/bash
# tools/sprint-closure-check.sh
# Sprint closure evidence generator
# Usage: bash tools/sprint-closure-check.sh <sprint_number>
# Output: evidence/sprint-{N}/closure-check-output.txt (produced by script)
#         evidence/sprint-{N}/contract-evidence.txt (produced by script)
# Verifies: mutation-drill.txt, e2e-output.txt, lighthouse.txt (produced by sprint work)
# Result: "ELIGIBLE FOR CLOSURE REVIEW" or "NOT CLOSEABLE"

set -euo pipefail

SPRINT=${1:?"Usage: $0 <sprint_number>"}
EVIDENCE_DIR="evidence/sprint-$SPRINT"
MAIN_OUTPUT="$EVIDENCE_DIR/closure-check-output.txt"
CONTRACT_OUTPUT="$EVIDENCE_DIR/contract-evidence.txt"
FAIL_COUNT=0

# Decision-driven config — update when D-068 amendment is resolved
EXPECTED_DATAQUALITY_STATES=6  # D-079 amendment: fresh,partial,stale,degraded,unknown,not_reached

mkdir -p "$EVIDENCE_DIR"

log() { echo "[$(date -Iseconds)] $1" | tee -a "$MAIN_OUTPUT"; }
pass() { log "✅ PASS: $1"; }
fail() { log "❌ FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# Clear previous output
> "$MAIN_OUTPUT"
> "$CONTRACT_OUTPUT"

log "=== Sprint $SPRINT Closure Check ==="
log "Date: $(date -Iseconds)"
log ""

# ─── BACKEND TESTS ───────────────────────────────────────────
log "--- Backend Tests ---"
cd agent
if python -m pytest tests/ -v 2>&1 | tee -a "../$MAIN_OUTPUT"; then
    BACKEND_COUNT=$(python -m pytest tests/ --co -q 2>/dev/null | tail -1 | grep -oP '\d+')
    log "Backend test count (collected): $BACKEND_COUNT"
    pass "Backend tests: $BACKEND_COUNT collected"
else
    fail "Backend tests failed"
    BACKEND_COUNT=0
fi
cd ..

log ""

# ─── FRONTEND TESTS ──────────────────────────────────────────
log "--- Frontend Tests ---"
cd frontend
if npx vitest run 2>&1 | tee -a "../$MAIN_OUTPUT"; then
    FRONTEND_COUNT=$(npx vitest list 2>/dev/null | wc -l)
    log "Frontend test count (collected): $FRONTEND_COUNT"
    pass "Frontend tests: $FRONTEND_COUNT collected"
else
    fail "Frontend tests failed"
    FRONTEND_COUNT=0
fi

log ""

# ─── TYPESCRIPT ───────────────────────────────────────────────
log "--- TypeScript Check ---"
if npx tsc --noEmit 2>&1 | tee -a "../$MAIN_OUTPUT"; then
    pass "TypeScript: 0 errors"
else
    fail "TypeScript errors found"
fi

log ""

# ─── LINT ─────────────────────────────────────────────────────
log "--- Lint Check ---"
if npm run lint 2>&1 | tee -a "../$MAIN_OUTPUT"; then
    pass "Lint: 0 errors"
else
    fail "Lint errors found"
fi

log ""

# ─── BUILD ────────────────────────────────────────────────────
log "--- Production Build ---"
if npm run build 2>&1 | tee -a "../$MAIN_OUTPUT"; then
    pass "Production build successful"
else
    fail "Production build failed"
fi
cd ..

log ""

# ─── VALIDATOR ────────────────────────────────────────────────
log "--- Sprint Doc Validator ---"
if python tools/validate_sprint_docs.py --sprint "$SPRINT" 2>&1 | tee -a "$MAIN_OUTPUT"; then
    pass "Validator: all checks passed"
else
    fail "Validator failed"
fi

log ""

# ─── CONTRACT EVIDENCE ────────────────────────────────────────
log "--- Contract Evidence ---"
{
    echo "=== Contract Evidence for Sprint $SPRINT ==="
    echo "Date: $(date -Iseconds)"
    echo ""

    # MANDATORY checks — NOT FOUND = FAIL
    check_grep() {
        local label="$1" pattern="$2" target="$3"
        echo "--- $label ---"
        if [ -d "$target" ]; then
            if grep -rnE "$pattern" "$target" 2>/dev/null; then
                echo "FOUND ✅"
            else
                echo "NOT FOUND ❌ — MANDATORY CHECK FAILED"
                FAIL_COUNT=$((FAIL_COUNT + 1))
            fi
        else
            if grep -nE "$pattern" "$target" 2>/dev/null; then
                echo "FOUND ✅"
            else
                echo "NOT FOUND ❌ — MANDATORY CHECK FAILED"
                FAIL_COUNT=$((FAIL_COUNT + 1))
            fi
        fi
        echo ""
    }

    check_grep "DataQuality states (D-079, expected $EXPECTED_DATAQUALITY_STATES)" "fresh\|partial\|stale\|degraded\|unknown\|not_reached" "frontend/src/types/api.ts"
    check_grep "CapabilityStatus tri-state (available/unavailable/unknown)" "available\|unavailable\|unknown" "frontend/src/types/api.ts"
    check_grep "ErrorBoundary usage" "ErrorBoundary" "frontend/src/App.tsx"

    # Sprint 10+ SSE mandatory checks
    if [ "$SPRINT" -ge 10 ]; then
        check_grep "SSE hooks" "useSSE\|SSEContext" "frontend/src/hooks/SSEContext.tsx"
        check_grep "ConnectionIndicator" "ConnectionIndicator" "frontend/src/components/ConnectionIndicator.tsx"
        check_grep "FileWatcher class" "class FileWatcher" "agent/api/file_watcher.py"
        check_grep "SSEManager class" "class SSEManager" "agent/api/sse_manager.py"
    fi

    # Sprint 11+ mutation mandatory checks
    if [ "$SPRINT" -ge 11 ]; then
        check_grep "Atomic request artifact" "request.*artifact\|signal.*file\|atomic.*write" "agent/api/"
        check_grep "CSRF middleware" "SameSite\|Origin.*check\|csrf" "agent/api/"
        check_grep "MutationResponse contract" "requestId.*lifecycleState\|lifecycleState\|requestedAt" "agent/api/schemas.py"
        check_grep "Mutation audit fields" "tabId\|sessionId" "agent/api/"
        check_grep "Mutation SSE events" "mutation_applied\|mutation_requested\|mutation_accepted" "agent/api/"

        echo "--- Bridge rule: no direct method call in API layer ---"
        if grep -rn "def approve\|def reject\|def cancel_mission\|def retry_mission" agent/api/ 2>/dev/null; then
            echo "WARNING ❌ — Direct method calls found in API layer — MANDATORY FAIL"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        else
            echo "CLEAN ✅ — No direct method calls in API layer"
        fi
        echo ""

        # Sprint 11 specific: mutation drill evidence must exist
        if [ ! -f "evidence/sprint-$SPRINT/mutation-drill.txt" ]; then
            echo "MISSING ❌ — evidence/sprint-$SPRINT/mutation-drill.txt required"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        else
            echo "EXISTS ✅ — mutation-drill.txt"
            if grep -q "FAIL" "evidence/sprint-$SPRINT/mutation-drill.txt"; then
                echo "DRILL HAS FAILURES ❌"
                FAIL_COUNT=$((FAIL_COUNT + 1))
            else
                echo "DRILL ALL PASS ✅"
            fi
        fi
        echo ""
    fi

    # Sprint 12+ E2E / accessibility mandatory checks
    if [ "$SPRINT" -ge 12 ]; then
        if [ ! -f "evidence/sprint-$SPRINT/e2e-output.txt" ]; then
            echo "MISSING ❌ — e2e-output.txt required"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        else
            echo "EXISTS ✅ — e2e-output.txt"
        fi

        if [ ! -f "evidence/sprint-$SPRINT/lighthouse.txt" ]; then
            echo "MISSING ❌ — lighthouse.txt required"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        else
            echo "EXISTS ✅ — lighthouse.txt"
        fi

        # Sprint 12+ E2E test count (P-05)
        echo "--- E2E Test Count (auto-parsed, P-05) ---"
        if command -v python &>/dev/null && [ -d "tests/e2e" ]; then
            E2E_COUNT=$(cd agent && python -m pytest ../tests/e2e/ --co -q 2>/dev/null | tail -1 | grep -oP '\d+' || echo "0")
            echo "E2E test count (collected): $E2E_COUNT"
        else
            E2E_COUNT=0
            echo "E2E tests not available: $E2E_COUNT"
        fi
        echo ""

        # Sprint 12 final decision debt check: D-001→D-101 ALL present
        echo "--- Decision Debt: D-001→D-101 zero gap check ---"
        MISSING_DECISIONS=0
        for i in $(seq 1 101); do
            ID=$(printf "D-%03d" "$i")
            if ! grep -q "$ID" docs/ai/DECISIONS.md 2>/dev/null; then
                echo "MISSING ❌ — $ID"
                MISSING_DECISIONS=$((MISSING_DECISIONS + 1))
            fi
        done

        if [ "$MISSING_DECISIONS" -gt 0 ]; then
            echo "DECISION DEBT ❌ — $MISSING_DECISIONS decision(s) missing from DECISIONS.md"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        else
            echo "DECISION DEBT ZERO ✅ — D-001→D-101 all present"
        fi
        echo ""
    fi

    # INFORMATIVE checks (no fail increment)
    echo "=== INFORMATIVE (non-blocking) ==="
    echo "--- usePolling preserved (D-088 fallback) ---"
    grep -rn "usePolling" frontend/src/ 2>/dev/null || echo "INFO: not found"
    echo ""

} > "$CONTRACT_OUTPUT" 2>&1

pass "Contract evidence generated"

log ""

# ─── LIVE ENDPOINT CHECKS (MANDATORY) ─────────────────────────
log "--- Live Endpoint Checks ---"
{
    echo "=== Live Endpoint Checks ==="

    if curl -sf http://127.0.0.1:8003/api/v1/health > /dev/null 2>&1; then
        echo "GET /api/v1/health → 200 ✅"
        curl -s http://127.0.0.1:8003/api/v1/health | python -m json.tool 2>/dev/null
    else
        echo "GET /api/v1/health → UNREACHABLE ❌ — MANDATORY FAIL"
        echo "Backend :8003 must be running for closure check."
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo ""

    if [ "$SPRINT" -ge 10 ]; then
        echo "--- SSE stream (3s capture) ---"
        SSE_OUTPUT=$(timeout 3 curl -N -s http://127.0.0.1:8003/api/v1/events/stream 2>/dev/null || true)
        if echo "$SSE_OUTPUT" | grep -q "event:"; then
            echo "SSE stream active ✅"
            echo "$SSE_OUTPUT"
        else
            echo "SSE stream not responding ❌ — MANDATORY FAIL"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
        echo ""
    fi

    if [ "$SPRINT" -ge 11 ]; then
        echo "--- Host attack (D-070) ---"
        HOST_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: evil.com" http://127.0.0.1:8003/api/v1/health 2>/dev/null)
        if [ "$HOST_STATUS" = "403" ]; then
            echo "Host attack → 403 ✅"
        else
            echo "Host attack → $HOST_STATUS (expected 403) ❌ — MANDATORY FAIL"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
        echo ""
    fi

} >> "$CONTRACT_OUTPUT" 2>&1

log ""

# ─── SUMMARY ─────────────────────────────────────────────────
log "==========================================="
log "Sprint $SPRINT Closure Check Summary"
log "==========================================="
# P-05: Auto test count from raw output — source hierarchy: raw > report
TOTAL_TESTS=$((${BACKEND_COUNT:-0} + ${FRONTEND_COUNT:-0} + ${E2E_COUNT:-0}))
log "Test counts (auto-parsed, P-05 rule):"
log "  Backend:  ${BACKEND_COUNT:-0}"
log "  Frontend: ${FRONTEND_COUNT:-0}"
log "  E2E:      ${E2E_COUNT:-0}"
log "  Total:    $TOTAL_TESTS"
log ""
log "Failures: $FAIL_COUNT"
log ""

if [ "$FAIL_COUNT" -eq 0 ]; then
    log "✅ ELIGIBLE FOR CLOSURE REVIEW"
    log "Status: implementation_status=done, closure_status=evidence_pending"
    log "Next: GPT review + Claude assessment + operator sign-off → closure_status=closed"
else
    log "❌ NOT CLOSEABLE — $FAIL_COUNT check(s) failed"
    log "Status: implementation_status=in_progress"
    log "Fix failures above, then re-run."
fi

log ""
log "Evidence files:"
log "  $MAIN_OUTPUT"
log "  $CONTRACT_OUTPUT"
log "==========================================="

exit $FAIL_COUNT
