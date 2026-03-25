#!/usr/bin/env bash
# health-check.sh — Health endpoint verification for OpenClaw services
# Usage: bash ops/wsl/health-check.sh
set -euo pipefail

WMCP_HOST="${WMCP_HOST:-localhost}"
WMCP_PORT="${WMCP_PORT:-8001}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8002}"
MCC_PORT="${MCC_PORT:-8003}"

EXIT_CODE=0

check_service() {
    local name="$1"
    local url="$2"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        echo "  OK   ${name} (${url})"
    else
        echo "  FAIL ${name} (${url}) — HTTP ${code}"
        EXIT_CODE=1
    fi
}

echo "=== OpenClaw Health Check ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

check_service "WMCP Server" "http://${WMCP_HOST}:${WMCP_PORT}/health"
check_service "Dashboard"   "http://${WMCP_HOST}:${DASHBOARD_PORT}/health"
check_service "MCC API"     "http://${WMCP_HOST}:${MCC_PORT}/health"

echo ""
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "All services healthy."
else
    echo "One or more services unhealthy."
fi

exit $EXIT_CODE
