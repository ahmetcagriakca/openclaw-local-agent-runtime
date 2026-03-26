#!/usr/bin/env bash
# Start Vezir UI frontend (Vite on :3000).
# Usage: bash scripts/dev-frontend.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
NODE_PATH="C:/Users/AKCA/node20/node-v20.18.1-win-x64"

export PATH="$NODE_PATH:$PATH"
cd "$ROOT/frontend"
echo "Starting Vezir UI on http://localhost:3000 ..."
npm run dev
