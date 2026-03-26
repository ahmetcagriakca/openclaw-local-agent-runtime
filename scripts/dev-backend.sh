#!/usr/bin/env bash
# Start Vezir API backend (FastAPI on :8003).
# Usage: bash scripts/dev-backend.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

cd "$ROOT/agent"
echo "Starting Vezir API on http://127.0.0.1:8003 ..."
python -m uvicorn api.server:app --host 127.0.0.1 --port 8003 --reload
