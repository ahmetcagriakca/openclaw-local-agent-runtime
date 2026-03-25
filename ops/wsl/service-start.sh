#!/usr/bin/env bash
# service-start.sh — Start OpenClaw services (systemd or manual)
# Usage: bash ops/wsl/service-start.sh [--manual]
set -euo pipefail

OC_ROOT="${OC_ROOT:-/home/akca/oc}"
PYTHON="${PYTHON:-python3.14}"
MODE="${1:-systemd}"

echo "=== OpenClaw Service Start ==="
echo "Mode: ${MODE}"
echo ""

if [ "$MODE" = "--manual" ] || [ "$MODE" = "manual" ]; then
    echo "[1/2] Starting OpenClaw gateway (manual)..."
    cd "${OC_ROOT}"
    source .venv/bin/activate 2>/dev/null || true
    nohup ${PYTHON} -m openclaw.gateway > /tmp/openclaw-gateway.log 2>&1 &
    echo "  PID: $!"

    echo "[2/2] Verifying..."
    sleep 3
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null | grep -q "200"; then
        echo "  Gateway started successfully."
    else
        echo "  WARN: Gateway may still be starting. Check /tmp/openclaw-gateway.log"
    fi
else
    echo "[1/2] Starting via systemd..."
    sudo systemctl start openclaw.service
    sudo systemctl status openclaw.service --no-pager

    echo "[2/2] Enabling auto-start..."
    sudo systemctl enable openclaw.service
    echo "  Service enabled for auto-start."
fi

echo ""
echo "=== Service Start Complete ==="
