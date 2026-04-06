#!/usr/bin/env bash
# tools/ask-gpt-review.sh — Vezir Sprint Review via Azure APIM
# Usage: tools/ask-gpt-review.sh <sprint-number>
# Requires: APIM_ENDPOINT, APIM_KEY, APIM_MODEL env vars
# Reads: docs/ai/prompts/gpt-review-system_v3.md (system prompt)
#         docs/ai/prompts/review-verdict-contract_v2.md (output contract)
#         docs/sprints/sprint-{N}/review-delta-packet.md (filled delta packet)
# Output: docs/ai/reviews/S{N}-GPT-REVIEW.md

set -euo pipefail

# ─── Load .env if present ───────────────────────────────────────────
REPO_ROOT="$(git rev-parse --show-toplevel)"
if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a; source "$REPO_ROOT/.env"; set +a
fi

# ─── Config ──────────────────────────────────────────────────────────
SPRINT="${1:?Usage: ask-gpt-review.sh <sprint-number>}"

# Azure APIM
APIM_ENDPOINT="${APIM_ENDPOINT:?Set APIM_ENDPOINT env var}"
APIM_KEY="${APIM_KEY:?Set APIM_KEY env var}"
APIM_MODEL="${APIM_MODEL:-gpt-5.3-codex-cagri}"

# File paths
SYSTEM_PROMPT="$REPO_ROOT/docs/ai/prompts/gpt-review-system_v3.md"
VERDICT_CONTRACT="$REPO_ROOT/docs/ai/prompts/review-verdict-contract_v2.md"
DELTA_PACKET="$REPO_ROOT/docs/sprints/sprint-${SPRINT}/review-delta-packet.md"
OUTPUT_FILE="$REPO_ROOT/docs/ai/reviews/S${SPRINT}-GPT-REVIEW.md"

# ─── Preflight checks ───────────────────────────────────────────────
for f in "$SYSTEM_PROMPT" "$VERDICT_CONTRACT" "$DELTA_PACKET"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: Missing required file: $f" >&2
    exit 1
  fi
done

# Check closure-check ran first (Stage 0/1 prerequisite)
CLOSURE_CHECK="$REPO_ROOT/evidence/sprint-${SPRINT}/closure-check-output.txt"
if [[ ! -f "$CLOSURE_CHECK" ]]; then
  echo "ERROR: closure-check-output.txt missing. Run Stage 0 first:" >&2
  echo "  bash tools/sprint-closure-check.sh $SPRINT" >&2
  exit 1
fi

# ─── Build payloads ─────────────────────────────────────────────────
# System = review rules + verdict contract
SYSTEM_CONTENT="$(cat "$SYSTEM_PROMPT")

---

# Output Contract (follow exactly)

$(cat "$VERDICT_CONTRACT")"

# User = filled delta packet
USER_CONTENT="$(cat "$DELTA_PACKET")"

# ─── Build JSON request body ────────────────────────────────────────
# Uses OpenAI Responses API format (input + input_text)
REQUEST_BODY=$(jq -n \
  --arg model "$APIM_MODEL" \
  --arg system "$SYSTEM_CONTENT" \
  --arg user "$USER_CONTENT" \
  '{
    model: $model,
    input: [
      {
        role: "system",
        content: [
          {
            type: "input_text",
            text: $system
          }
        ]
      },
      {
        role: "user",
        content: [
          {
            type: "input_text",
            text: $user
          }
        ]
      }
    ],
    max_output_tokens: 1500,
    temperature: 0.1
  }')

# ─── Call Azure APIM ────────────────────────────────────────────────
echo "Sending Sprint $SPRINT review to Azure APIM..."
echo "Model: $APIM_MODEL"
echo "Delta packet: $DELTA_PACKET"
echo ""

# Auto-detect auth header: Azure OpenAI uses api-key, APIM uses Ocp-Apim-Subscription-Key
if [[ "$APIM_ENDPOINT" == *".openai.azure.com"* ]]; then
  AUTH_HEADER="api-key: $APIM_KEY"
else
  AUTH_HEADER="Ocp-Apim-Subscription-Key: $APIM_KEY"
fi

# Write request body to temp file to avoid shell expansion issues with large JSON
REQUEST_FILE=$(mktemp)
trap 'rm -f "$REQUEST_FILE"' EXIT
echo "$REQUEST_BODY" > "$REQUEST_FILE"

RESPONSE=$(curl -s -w "\n%{http_code}" \
  "$APIM_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d @"$REQUEST_FILE")

# Split response body and HTTP status
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" -ne 200 ]]; then
  echo "ERROR: API returned HTTP $HTTP_CODE" >&2
  echo "$BODY" | jq . 2>/dev/null || echo "$BODY" >&2
  exit 1
fi

# ─── Extract response text ──────────────────────────────────────────
# Responses API returns output[].content[].text
VERDICT=$(echo "$BODY" | jq -r '
  .output[]
  | select(.role == "assistant")
  | .content[]
  | select(.type == "output_text")
  | .text
' 2>/dev/null)

# Fallback: try chat completions format (choices[].message.content)
if [[ -z "$VERDICT" || "$VERDICT" == "null" ]]; then
  VERDICT=$(echo "$BODY" | jq -r '.choices[0].message.content' 2>/dev/null)
fi

if [[ -z "$VERDICT" || "$VERDICT" == "null" ]]; then
  echo "ERROR: Could not extract verdict from response" >&2
  echo "$BODY" | jq . 2>/dev/null || echo "$BODY" >&2
  exit 1
fi

# ─── Write review file ──────────────────────────────────────────────
mkdir -p "$(dirname "$OUTPUT_FILE")"

cat > "$OUTPUT_FILE" << EOF
# Sprint $SPRINT — GPT Review (API)

**Date:** $(date +%Y-%m-%d)
**Reviewer:** GPT ($APIM_MODEL) via Azure APIM
**Method:** tools/ask-gpt-review.sh
**Delta Packet:** docs/sprints/sprint-${SPRINT}/review-delta-packet.md

---

$VERDICT
EOF

echo ""
echo "Review written to: $OUTPUT_FILE"
echo ""
echo "--- Verdict Preview ---"
echo "$VERDICT" | head -20
echo ""

# ─── Token usage (if available) ─────────────────────────────────────
USAGE=$(echo "$BODY" | jq -r '.usage // empty' 2>/dev/null)
if [[ -n "$USAGE" ]]; then
  echo "--- Token Usage ---"
  echo "$USAGE" | jq .
fi
