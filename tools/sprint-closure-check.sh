#!/bin/bash
# tools/sprint-closure-check.sh
# Sprint closure evidence checker per D-127 class taxonomy.
# Usage: bash tools/sprint-closure-check.sh <sprint_number> [--governance]
# Class detection: reads evidence/sprint-{N}/sprint-class.txt (D-127)
#   --governance flag: explicit override to force governance rules
# Output: evidence/sprint-{N}/closure-check-output.txt
# Result: "ELIGIBLE FOR CLOSURE REVIEW" or "NOT CLOSEABLE"

set -euo pipefail

# Python command resolution for cross-platform compatibility
# Windows: Microsoft Store aliases shadow real python; use known local path
PYTHON_CMD="python"
PYTHON_LOCAL="$HOME/AppData/Local/Python/bin/python.exe"
if [ -x "$PYTHON_LOCAL" ]; then
    PYTHON_CMD="$PYTHON_LOCAL"
elif command -v python3.14 &>/dev/null; then
    PYTHON_CMD="python3.14"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
fi

SPRINT=${1:?"Usage: $0 <sprint_number> [--governance]"}
GOVERNANCE_OVERRIDE=false
if [[ "${2:-}" == "--governance" ]]; then
    GOVERNANCE_OVERRIDE=true
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/evidence/sprint-$SPRINT"
MAIN_OUTPUT="$EVIDENCE_DIR/closure-check-output.txt"
CONTRACT_OUTPUT="$EVIDENCE_DIR/contract-evidence.txt"
FAIL_COUNT=0

# D-127: Resolve sprint class from packet metadata
CLASS_FILE="$EVIDENCE_DIR/sprint-class.txt"
if [ "$GOVERNANCE_OVERRIDE" = true ]; then
    SPRINT_CLASS="governance"
elif [ -f "$CLASS_FILE" ]; then
    SPRINT_CLASS="$(cat "$CLASS_FILE" | tr -d '[:space:]')"
else
    echo "ERROR: sprint-class.txt not found at $CLASS_FILE"
    echo "Run: bash tools/generate-evidence-packet.sh $SPRINT <class> first"
    exit 1
fi

if [[ "$SPRINT_CLASS" != "governance" && "$SPRINT_CLASS" != "product" ]]; then
    echo "ERROR: invalid sprint class '$SPRINT_CLASS' in $CLASS_FILE"
    exit 1
fi

# Decision-driven config
EXPECTED_DATAQUALITY_STATES=6  # D-079 amendment

mkdir -p "$EVIDENCE_DIR"

log() { echo "[$(date -Iseconds)] $1" | tee -a "$MAIN_OUTPUT"; }
pass() { log "✅ PASS: $1"; }
fail() { log "❌ FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# Clear previous output
> "$MAIN_OUTPUT"
> "$CONTRACT_OUTPUT"

log "=== Sprint $SPRINT Closure Check ==="
log "Class: $SPRINT_CLASS ($([ "$GOVERNANCE_OVERRIDE" = true ] && echo 'override' || echo 'auto-detected'))"
log "Date: $(date -Iseconds)"
log ""

# ─── BACKEND TESTS ───────────────────────────────────────────
log "--- Backend Tests ---"
cd agent
if $PYTHON_CMD -m pytest tests/ -v 2>&1 | tee -a "$MAIN_OUTPUT"; then
    BACKEND_COUNT=$($PYTHON_CMD -m pytest tests/ --co -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1)
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
if npx vitest run 2>&1 | tee -a "$MAIN_OUTPUT"; then
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
if npx tsc --noEmit 2>&1 | tee -a "$MAIN_OUTPUT"; then
    pass "TypeScript: 0 errors"
else
    fail "TypeScript errors found"
fi

log ""

# ─── LINT ─────────────────────────────────────────────────────
log "--- Lint Check ---"
if npm run lint 2>&1 | tee -a "$MAIN_OUTPUT"; then
    pass "Lint: 0 errors"
else
    fail "Lint errors found"
fi

log ""

# ─── BUILD ────────────────────────────────────────────────────
log "--- Production Build ---"
if npm run build 2>&1 | tee -a "$MAIN_OUTPUT"; then
    pass "Production build successful"
else
    fail "Production build failed"
fi
cd ..

log ""

# ─── SPRINT DOC VALIDATOR ────────────────────────────────────
log "--- Sprint Doc Validator ---"
if [ -f "tools/validate_sprint_docs.py" ]; then
    if $PYTHON_CMD tools/validate_sprint_docs.py --sprint "$SPRINT" 2>&1 | tee -a "$MAIN_OUTPUT"; then
        pass "Sprint doc validator: all checks passed"
    else
        fail "Sprint doc validator failed"
    fi
else
    log "  Sprint doc validator not found — skipped"
fi

log ""

# ─── DOC DRIFT CHECK (decision index + test counts) ─────────
log "--- Doc Drift Check ---"
if [ -f "tools/doc_drift_check.py" ]; then
    if $PYTHON_CMD tools/doc_drift_check.py --skip-tests 2>&1 | tee -a "$MAIN_OUTPUT"; then
        pass "Doc drift check: all checks passed"
    else
        fail "Doc drift check: mismatches found"
    fi
else
    log "  Doc drift check not found — skipped"
fi

log ""

# ─── PROJECT V2 BOARD VALIDATOR (D-123/D-124/D-125) ─────────
log "--- Project V2 Board Validator ---"
VALIDATOR_OUTPUT=$($PYTHON_CMD tools/project-validator.py 2>&1)
VALIDATOR_EXIT=$?
echo "$VALIDATOR_OUTPUT" | tee -a "$MAIN_OUTPUT"

if [ $VALIDATOR_EXIT -eq 0 ]; then
    pass "Project V2 board validator: VALID"
    # Save JSON output for evidence
    $PYTHON_CMD tools/project-validator.py --json > "$EVIDENCE_DIR/validator-board.json" 2>/dev/null
else
    fail "Project V2 board validator: NOT VALID"
fi

# Log warnings from validator (non-blocking)
WARN_COUNT=$(echo "$VALIDATOR_OUTPUT" | grep -c "WARN" || true)
if [ "$WARN_COUNT" -gt 0 ]; then
    log "  Board validator warnings: $WARN_COUNT (non-blocking)"
fi

log ""

# ─── CONTRACT EVIDENCE (product class only, D-127) ───────────
if [ "$SPRINT_CLASS" = "product" ]; then
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

    check_grep "DataQuality states (D-079, expected $EXPECTED_DATAQUALITY_STATES)" "fresh|partial|stale|degraded|unknown|not_reached" "frontend/src/types/api.ts"
    check_grep "CapabilityStatus tri-state (available/unavailable/unknown)" "available|unavailable|unknown" "frontend/src/types/api.ts"
    check_grep "ErrorBoundary usage" "ErrorBoundary" "frontend/src/App.tsx"

    # Sprint 10+ SSE mandatory checks
    if [ "$SPRINT" -ge 10 ]; then
        check_grep "SSE hooks" "useSSE|SSEContext" "frontend/src/hooks/SSEContext.tsx"
        check_grep "ConnectionIndicator" "ConnectionIndicator" "frontend/src/components/ConnectionIndicator.tsx"
        check_grep "FileWatcher class" "class FileWatcher" "agent/api/file_watcher.py"
        check_grep "SSEManager class" "class SSEManager" "agent/api/sse_manager.py"
    fi

    # Sprint 11+ mutation mandatory checks
    if [ "$SPRINT" -ge 11 ]; then
        check_grep "Atomic request artifact" "request.*artifact|signal.*file|atomic.*write" "agent/api/"
        check_grep "CSRF middleware" "SameSite|Origin.*check|csrf" "agent/api/"
        check_grep "MutationResponse contract" "requestId.*lifecycleState|lifecycleState|requestedAt" "agent/api/schemas.py"
        check_grep "Mutation audit fields" "tabId|sessionId" "agent/api/"
        check_grep "Mutation SSE events" "mutation_applied|mutation_requested|mutation_accepted" "agent/api/"

        echo "--- Bridge rule: no direct method call in API layer ---"
        # Check for raw approve/reject/cancel/retry methods (not async endpoint handlers)
        if grep -rnE "^\s+def (approve|reject|cancel_mission|retry_mission)\b" agent/api/ 2>/dev/null | grep -v "async def" | grep -v "_approval\|_mission"; then
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
        if command -v $PYTHON_CMD &>/dev/null && [ -f "agent/tests/test_e2e.py" ]; then
            E2E_COUNT=$(cd agent && $PYTHON_CMD -m pytest tests/test_e2e.py --co -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1 || echo "0")
            echo "E2E test count (collected): $E2E_COUNT"
        else
            E2E_COUNT=0
            echo "E2E tests not available: $E2E_COUNT"
        fi
        echo ""

        # Decision debt check: D-001→D-103 ALL present (updated Sprint 13)
        DECISION_MAX=103
        echo "--- Decision Debt: D-001→D-$DECISION_MAX zero gap check ---"
        MISSING_DECISIONS=0
        for i in $(seq 1 $DECISION_MAX); do
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
            echo "DECISION DEBT ZERO ✅ — D-001→D-$DECISION_MAX all present"
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

# ─── LIVE ENDPOINT CHECKS (product class only, D-127) ────────
log "--- Live Endpoint Checks ---"
{
    echo "=== Live Endpoint Checks ==="

    if curl -sf http://127.0.0.1:8003/api/v1/health > /dev/null 2>&1; then
        echo "GET /api/v1/health → 200 ✅"
        curl -s http://127.0.0.1:8003/api/v1/health | $PYTHON_CMD -m json.tool 2>/dev/null
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

else
    # Governance class: skip contract evidence and live checks (D-127)
    log "--- Contract Evidence ---"
    log "  SKIPPED (governance class per D-127)"
    log ""
    log "--- Live Endpoint Checks ---"
    log "  SKIPPED (governance class per D-127)"
    log ""
fi  # end product-class-only block

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
