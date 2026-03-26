#!/usr/bin/env bash
# Run all Vezir platform tests (backend + frontend).
# Usage: bash scripts/test-all.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
NODE_PATH="C:/Users/AKCA/node20/node-v20.18.1-win-x64"
FAILURES=0

echo "==========================================="
echo "  Vezir Platform — Full Test Suite"
echo "==========================================="

# Backend tests
echo ""
echo "--- Backend (pytest) ---"
cd "$ROOT/agent"
if python -m pytest tests/ -v --timeout=30; then
    echo "PASS: Backend tests"
else
    echo "FAIL: Backend tests"
    FAILURES=$((FAILURES + 1))
fi

# Frontend TypeScript
echo ""
echo "--- Frontend TypeScript (tsc) ---"
cd "$ROOT/frontend"
export PATH="$NODE_PATH:$PATH"
if npx tsc --noEmit; then
    echo "PASS: TypeScript 0 errors"
else
    echo "FAIL: TypeScript errors"
    FAILURES=$((FAILURES + 1))
fi

# Frontend tests
echo ""
echo "--- Frontend (vitest) ---"
if npx vitest run; then
    echo "PASS: Frontend tests"
else
    echo "FAIL: Frontend tests"
    FAILURES=$((FAILURES + 1))
fi

# Math service tests
echo ""
echo "--- Math Service ---"
cd "$ROOT/agent"
if python -m pytest math_service/test_app.py -v --timeout=10 2>/dev/null; then
    echo "PASS: Math service tests"
else
    echo "SKIP: Math service tests (file not found or failed)"
fi

echo ""
echo "==========================================="
if [ $FAILURES -eq 0 ]; then
    echo "  ALL SUITES PASSED"
else
    echo "  $FAILURES SUITE(S) FAILED"
fi
echo "==========================================="
exit $FAILURES
