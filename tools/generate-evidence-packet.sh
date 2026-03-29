#!/bin/bash
# tools/generate-evidence-packet.sh
# Generates canonical evidence packet per D-127 sprint closure class taxonomy.
# Usage: bash tools/generate-evidence-packet.sh <sprint_number> <class>
#   class = governance | product (required)
# Output: evidence/sprint-{N}/ with all canonical files per D-127 manifest

set -euo pipefail

SPRINT=${1:?"Usage: $0 <sprint_number> <class>"}
CLASS=${2:?"Usage: $0 <sprint_number> <class>  (class = governance | product)"}

if [[ "$CLASS" != "governance" && "$CLASS" != "product" ]]; then
    echo "ERROR: class must be 'governance' or 'product', got '$CLASS'"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/evidence/sprint-$SPRINT"
MANIFEST="$REPO_ROOT/tools/canonical-evidence-manifest-${CLASS}.txt"

if [ ! -f "$MANIFEST" ]; then
    echo "ERROR: manifest not found: $MANIFEST"
    exit 1
fi

mkdir -p "$EVIDENCE_DIR"

echo "=== Evidence Packet Generator ==="
echo "Sprint: $SPRINT"
echo "Class: $CLASS"
echo "Output: $EVIDENCE_DIR"
echo ""

# Governance-sprint NO EVIDENCE placeholders (per D-127)
GOVERNANCE_PLACEHOLDERS=(
    "e2e-output.txt"
    "contract-evidence.txt"
    "grep-evidence.txt"
    "live-checks.txt"
    "mutation-drill.txt"
    "lighthouse.txt"
)

# Write sprint-class.txt (canonical class metadata source)
echo "$CLASS" > "$EVIDENCE_DIR/sprint-class.txt"
echo "[+] sprint-class.txt = $CLASS"

# --- Run test suites and capture output ---

echo ""
echo "--- Running test suites ---"

# Backend pytest
echo "[*] Backend tests..."
cd "$REPO_ROOT/agent"
python -m pytest tests/ -v > "$EVIDENCE_DIR/pytest-output.txt" 2>&1 || true
echo "[+] pytest-output.txt"

# Validator tests
if [ -f "$REPO_ROOT/tests/test_project_validator.py" ]; then
    cd "$REPO_ROOT"
    python -m pytest tests/test_project_validator.py -v > "$EVIDENCE_DIR/validator-tests.txt" 2>&1 || true
    echo "[+] validator-tests.txt"
fi

# Board validator
cd "$REPO_ROOT"
python tools/project-validator.py > "$EVIDENCE_DIR/validator-output.txt" 2>&1 || true
echo "[+] validator-output.txt"

# Frontend vitest
cd "$REPO_ROOT/frontend"
npx vitest run > "$EVIDENCE_DIR/vitest-output.txt" 2>&1 || true
echo "[+] vitest-output.txt"

# TypeScript
npx tsc --noEmit > "$EVIDENCE_DIR/tsc-output.txt" 2>&1 || true
echo "[+] tsc-output.txt"

# Lint
npm run lint > "$EVIDENCE_DIR/lint-output.txt" 2>&1 || true
echo "[+] lint-output.txt"

# Build
npm run build > "$EVIDENCE_DIR/build-output.txt" 2>&1 || true
echo "[+] build-output.txt"

cd "$REPO_ROOT"

# Playwright
npx playwright test --reporter=list > "$EVIDENCE_DIR/playwright-output.txt" 2>&1 || true
echo "[+] playwright-output.txt"

# --- Class-specific evidence ---

if [ "$CLASS" = "product" ]; then
    # Product: generate real evidence files
    echo ""
    echo "--- Product-class evidence ---"

    # Contract evidence (grep checks)
    if [ -f "$EVIDENCE_DIR/contract-evidence.txt" ] && [ -s "$EVIDENCE_DIR/contract-evidence.txt" ]; then
        echo "[=] contract-evidence.txt (already exists)"
    else
        echo "Run sprint-closure-check.sh to generate contract-evidence.txt" > "$EVIDENCE_DIR/contract-evidence.txt"
        echo "[!] contract-evidence.txt (stub — run closure-check for real output)"
    fi
    cp "$EVIDENCE_DIR/contract-evidence.txt" "$EVIDENCE_DIR/grep-evidence.txt" 2>/dev/null || \
        echo "Run sprint-closure-check.sh to generate grep-evidence.txt" > "$EVIDENCE_DIR/grep-evidence.txt"
    echo "[+] grep-evidence.txt"

    # Live checks
    {
        echo "=== Live Endpoint Checks ==="
        echo "Date: $(date -Iseconds)"
        echo ""
        if curl -sf http://127.0.0.1:8003/api/v1/health > /dev/null 2>&1; then
            echo "GET /api/v1/health → 200 OK"
        else
            echo "GET /api/v1/health → UNREACHABLE"
        fi
    } > "$EVIDENCE_DIR/live-checks.txt"
    echo "[+] live-checks.txt"

    # E2E output
    cp "$EVIDENCE_DIR/playwright-output.txt" "$EVIDENCE_DIR/e2e-output.txt" 2>/dev/null || true
    echo "[+] e2e-output.txt"

    # Mutation drill + lighthouse: must be produced by sprint work
    for f in mutation-drill.txt lighthouse.txt; do
        if [ ! -f "$EVIDENCE_DIR/$f" ]; then
            echo "REQUIRED — produce during sprint work" > "$EVIDENCE_DIR/$f"
            echo "[!] $f (stub — must be produced by sprint work)"
        else
            echo "[=] $f (already exists)"
        fi
    done

elif [ "$CLASS" = "governance" ]; then
    echo ""
    echo "--- Governance-class placeholders (D-127) ---"

    for f in "${GOVERNANCE_PLACEHOLDERS[@]}"; do
        echo "NO EVIDENCE — governance sprint, not applicable per D-127" > "$EVIDENCE_DIR/$f"
        echo "[+] $f (NO EVIDENCE)"
    done
fi

# --- Closure check ---
echo ""
echo "--- Closure check ---"
# Note: closure-check-output.txt is produced by sprint-closure-check.sh, not this generator
if [ ! -f "$EVIDENCE_DIR/closure-check-output.txt" ]; then
    echo "Run tools/sprint-closure-check.sh $SPRINT to generate" > "$EVIDENCE_DIR/closure-check-output.txt"
    echo "[!] closure-check-output.txt (stub — run closure-check)"
else
    echo "[=] closure-check-output.txt (already exists)"
fi

# --- Review summary ---
REVIEW_FILE="$REPO_ROOT/docs/ai/reviews/S${SPRINT}-REVIEW.md"
if [ -f "$REVIEW_FILE" ]; then
    cp "$REVIEW_FILE" "$EVIDENCE_DIR/review-summary.md"
    echo "[+] review-summary.md (from S${SPRINT}-REVIEW.md)"
else
    echo "Review not yet written" > "$EVIDENCE_DIR/review-summary.md"
    echo "[!] review-summary.md (stub — write review first)"
fi

# --- File manifest ---
echo "=== Sprint $SPRINT Evidence Manifest ===" > "$EVIDENCE_DIR/file-manifest.txt"
echo "Generated: $(date -Iseconds)" >> "$EVIDENCE_DIR/file-manifest.txt"
echo "Class: $CLASS" >> "$EVIDENCE_DIR/file-manifest.txt"
echo "" >> "$EVIDENCE_DIR/file-manifest.txt"
ls -la "$EVIDENCE_DIR/" >> "$EVIDENCE_DIR/file-manifest.txt"
echo "[+] file-manifest.txt"

# --- Verification ---
echo ""
echo "=== Verification ==="
DIFF_OUTPUT=$(diff <(ls -1 "$EVIDENCE_DIR/" | sort) <(cat "$MANIFEST" | sort) 2>&1 || true)
if [ -z "$DIFF_OUTPUT" ]; then
    echo "✅ Manifest match: all canonical files present, no extras"
else
    echo "❌ Manifest mismatch:"
    echo "$DIFF_OUTPUT"
fi

echo ""
echo "=== Done ==="
echo "Evidence packet: $EVIDENCE_DIR/ ($CLASS class, $(ls -1 "$EVIDENCE_DIR/" | wc -l) files)"
