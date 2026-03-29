#!/bin/bash
# Generate self-signed TLS certificate for development — D-130.
# Output: config/tls/server.pem + config/tls/server-key.pem
# Usage: bash tools/generate-dev-cert.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TLS_DIR="$REPO_ROOT/config/tls"
CERT="$TLS_DIR/server.pem"
KEY="$TLS_DIR/server-key.pem"

mkdir -p "$TLS_DIR"

if [ -f "$CERT" ] && [ -f "$KEY" ]; then
    echo "Certificates already exist at $TLS_DIR"
    echo "Delete them first to regenerate."
    exit 0
fi

echo "Generating self-signed TLS certificate..."
openssl req -x509 -newkey rsa:2048 -keyout "$KEY" -out "$CERT" \
    -days 365 -nodes -subj "/CN=localhost" 2>/dev/null

echo "Certificate: $CERT"
echo "Key: $KEY"
echo "Valid for 365 days, CN=localhost"
