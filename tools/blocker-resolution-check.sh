#!/usr/bin/env bash
# tools/blocker-resolution-check.sh — Verify all review blockers are resolved
# Usage: blocker-resolution-check.sh <sprint-number>
# Exit 0: all resolved, Exit 1: unresolved, Exit 2: unresolvable exist

set -euo pipefail

SPRINT="${1:?Usage: blocker-resolution-check.sh <sprint-number>}"
REPO_ROOT="$(git rev-parse --show-toplevel)"

REVIEW_FILE="$REPO_ROOT/docs/ai/reviews/S${SPRINT}-GPT-REVIEW.md"
DELTA_PACKET="$REPO_ROOT/docs/sprints/sprint-${SPRINT}/review-delta-packet.md"
EVIDENCE_DIR="$REPO_ROOT/evidence/sprint-${SPRINT}"
RESOLUTION_LOG="$EVIDENCE_DIR/blocker-resolution-log.txt"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

[[ ! -f "$REVIEW_FILE" ]] && { echo -e "${RED}Review file not found${NC}" >&2; exit 1; }
[[ ! -f "$DELTA_PACKET" ]] && { echo -e "${RED}Delta packet not found${NC}" >&2; exit 1; }
mkdir -p "$EVIDENCE_DIR"

mapfile -t BLOCKER_IDS < <(grep -oP 'B[0-9]+' "$REVIEW_FILE" | sort -u)

if [[ ${#BLOCKER_IDS[@]} -eq 0 ]]; then
  echo -e "${GREEN}No blockers found${NC}"
  echo "NO BLOCKERS FOUND" > "$RESOLUTION_LOG"
  exit 0
fi

echo "Blocker Resolution Check — Sprint $SPRINT"
echo "=========================================="

TOTAL=${#BLOCKER_IDS[@]}; RESOLVED=0; UNRESOLVED=0; UNRESOLVABLE=0

{
  echo "# Blocker Resolution Log — Sprint $SPRINT"
  echo "Date: $(date -Iseconds)"
  echo ""
  echo "| Blocker | Patch | Commit | Evidence | Status |"
  echo "|---------|-------|--------|----------|--------|"
} > "$RESOLUTION_LOG"

for bid in "${BLOCKER_IDS[@]}"; do
  patch_found="NO"; commit_found="NO"; evidence_found="NO"; status="UNRESOLVED"

  if grep -qP "^\|.*${bid}.*\|" "$DELTA_PACKET" 2>/dev/null; then
    patch_found="YES"
    if grep -P "^\|.*${bid}.*\|" "$DELTA_PACKET" | grep -qi "UNRESOLVABLE"; then
      status="UNRESOLVABLE"; ((UNRESOLVABLE++))
      echo -e "${YELLOW}  $bid: UNRESOLVABLE${NC}"
      echo "| $bid | $patch_found | N/A | N/A | $status |" >> "$RESOLUTION_LOG"
      continue
    fi
  fi

  local_commit=$(grep -P "^\|.*${bid}.*\|" "$DELTA_PACKET" 2>/dev/null | grep -oP '[0-9a-f]{7,40}' | head -1 || echo "")
  if [[ -n "$local_commit" ]] && git cat-file -t "$local_commit" &>/dev/null; then
    commit_found="YES"
  fi

  local_evidence=$(grep -P "^\|.*${bid}.*\|" "$DELTA_PACKET" 2>/dev/null | awk -F'|' '{print $(NF-1)}' | xargs || echo "")
  if [[ -n "$local_evidence" ]]; then
    for epath in $local_evidence; do
      epath_clean=$(echo "$epath" | sed 's|^[[:space:]]*||;s|[[:space:]]*$||')
      if [[ -f "$REPO_ROOT/$epath_clean" ]] || [[ -f "$epath_clean" ]]; then
        evidence_found="YES"; break
      fi
    done
  fi

  if [[ "$patch_found" == "YES" && "$commit_found" == "YES" && "$evidence_found" == "YES" ]]; then
    status="RESOLVED"; ((RESOLVED++))
    echo -e "${GREEN}  $bid: RESOLVED${NC}"
  else
    status="UNRESOLVED"; ((UNRESOLVED++))
    echo -e "${RED}  $bid: UNRESOLVED — patch=$patch_found commit=$commit_found evidence=$evidence_found${NC}"
  fi
  echo "| $bid | $patch_found | $commit_found | $evidence_found | $status |" >> "$RESOLUTION_LOG"
done

echo ""
echo "Total: $TOTAL | Resolved: $RESOLVED | Unresolved: $UNRESOLVED | Unresolvable: $UNRESOLVABLE"

{
  echo ""
  echo "## Summary"
  echo "- Total: $TOTAL, Resolved: $RESOLVED, Unresolved: $UNRESOLVED, Unresolvable: $UNRESOLVABLE"
  if [[ $UNRESOLVED -eq 0 && $UNRESOLVABLE -eq 0 ]]; then
    echo "**ALL RESOLVED — ready for re-review**"
  elif [[ $UNRESOLVABLE -gt 0 && $UNRESOLVED -eq 0 ]]; then
    echo "**ESCALATE — unresolvable blockers**"
  else
    echo "**NOT READY — $UNRESOLVED unresolved**"
  fi
} >> "$RESOLUTION_LOG"

[[ $UNRESOLVED -gt 0 ]] && exit 1
[[ $UNRESOLVABLE -gt 0 ]] && exit 2
exit 0
