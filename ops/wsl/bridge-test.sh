#!/usr/bin/env bash
# bridge-test.sh — E2E test for oc-bridge (WSL → Windows → PowerShell)
# Usage: bash ops/wsl/bridge-test.sh
set -euo pipefail

OC_ROOT="${OC_ROOT:-/home/akca/oc}"
BRIDGE_HOST="${BRIDGE_HOST:-localhost}"
BRIDGE_PORT="${BRIDGE_PORT:-8001}"
BRIDGE_URL="http://${BRIDGE_HOST}:${BRIDGE_PORT}"

echo "=== OpenClaw Bridge E2E Test ==="
echo "Target: ${BRIDGE_URL}"
echo ""

# Test 1: Health endpoint
echo "[1/3] Health check..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BRIDGE_URL}/health" || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "  PASS: Health endpoint returned 200"
else
    echo "  FAIL: Health endpoint returned ${HTTP_CODE}"
    exit 1
fi

# Test 2: Capability list
echo "[2/3] Capability list..."
CAPS=$(curl -s "${BRIDGE_URL}/tools" 2>/dev/null || echo "")
if echo "$CAPS" | grep -q "tools"; then
    echo "  PASS: Tools endpoint returned tool list"
else
    echo "  FAIL: Tools endpoint did not return expected format"
    exit 1
fi

# Test 3: Echo test (safe read-only operation)
echo "[3/3] Echo test..."
RESULT=$(curl -s -X POST "${BRIDGE_URL}/execute" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: ${WMCP_API_KEY:-local-mcp-12345}" \
    -d '{"tool": "echo", "params": {"message": "bridge-test-ok"}}' \
    2>/dev/null || echo "")
if echo "$RESULT" | grep -q "bridge-test-ok"; then
    echo "  PASS: Echo test returned expected value"
else
    echo "  WARN: Echo test response: ${RESULT:-empty}"
fi

echo ""
echo "=== Bridge E2E Test Complete ==="
