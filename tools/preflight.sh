#!/usr/bin/env bash
# Preflight check — run before commit/push to catch common issues.
# Sprint 48 (48.4): Local CI alignment.
#
# Usage: bash tools/preflight.sh

set -e

echo "=== Preflight Check ==="
echo ""

# 1. Ruff lint
echo "[1/5] Ruff lint..."
cd agent && python -m ruff check . && cd ..
echo "  PASS"

# 2. TypeScript check
echo "[2/5] TypeScript check..."
cd frontend && npx tsc --noEmit && cd ..
echo "  PASS"

# 3. OpenAPI drift
echo "[3/5] OpenAPI drift check..."
python tools/export_openapi.py
if ! git diff --exit-code docs/api/openapi.json > /dev/null 2>&1; then
  echo "  FAIL: OpenAPI spec has drifted. Run 'python tools/export_openapi.py' and commit."
  exit 1
fi
echo "  PASS"

# 4. Backend tests (quick subset)
echo "[4/5] Backend tests (quick)..."
cd agent && python -m pytest tests/ -q --timeout=30 && cd ..
echo "  PASS"

# 5. Frontend tests
echo "[5/5] Frontend tests..."
cd frontend && npx vitest run --reporter=dot && cd ..
echo "  PASS"

echo ""
echo "=== Preflight PASS ==="
