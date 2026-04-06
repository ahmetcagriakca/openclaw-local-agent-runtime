#!/usr/bin/env bash
# tools/review-loop.sh — Vezir Autonomous Review Pipeline Orchestrator
# Usage: tools/review-loop.sh <sprint-number> [--auto-patch]
#
# Runs the full Stage 0→5 pipeline:
#   Stage 0: Preflight (evidence generation)
#   Stage 1: Deterministic gate validation
#   Stage 2: Delta packet verification
#   Stage 3: AI review via ask-gpt-review.sh
#   Stage 4: HOLD → patch directive → Claude Code → resolution check → re-review
#   Stage 5: ESCALATE or max rounds → operator
#
# Flags:
#   --auto-patch   Enable Claude Code auto-patching on HOLD (default: prompt)
#
# Requires: APIM_ENDPOINT, APIM_KEY, APIM_MODEL env vars
#           jq, tmux (for Claude Code dispatch)

set -euo pipefail

SPRINT="${1:?Usage: review-loop.sh <sprint-number> [--auto-patch]}"
AUTO_PATCH=0
[[ "${2:-}" == "--auto-patch" ]] && AUTO_PATCH=1

REPO_ROOT="$(git rev-parse --show-toplevel)"
MAX_ROUNDS=5
CURRENT_ROUND=1

SPRINT_DIR="$REPO_ROOT/docs/sprints/sprint-${SPRINT}"
EVIDENCE_DIR="$REPO_ROOT/evidence/sprint-${SPRINT}"
REVIEW_FILE="$REPO_ROOT/docs/ai/reviews/S${SPRINT}-GPT-REVIEW.md"
DELTA_PACKET="$SPRINT_DIR/review-delta-packet.md"
PATCH_DIRECTIVE="$SPRINT_DIR/patch-directive.md"
RESOLUTION_LOG="$EVIDENCE_DIR/blocker-resolution-log.txt"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[review-loop]${NC} $*"; }
warn() { echo -e "${YELLOW}[review-loop]${NC} $*"; }
fail() { echo -e "${RED}[review-loop]${NC} $*" >&2; }
pass() { echo -e "${GREEN}[review-loop]${NC} $*"; }

stage_0_preflight() {
  log "═══ Stage 0: Preflight Build ═══"
  mkdir -p "$EVIDENCE_DIR"

  if [[ -f "$REPO_ROOT/tools/sprint-closure-check.sh" ]]; then
    log "Running closure check..."
    if bash "$REPO_ROOT/tools/sprint-closure-check.sh" "$SPRINT" > "$EVIDENCE_DIR/closure-check-output.txt" 2>&1; then
      pass "Closure check: ELIGIBLE"
    else
      fail "Closure check: NOT CLOSEABLE"
      cat "$EVIDENCE_DIR/closure-check-output.txt"
      return 1
    fi
  else
    fail "sprint-closure-check.sh not found"
    return 1
  fi

  if [[ -f "$REPO_ROOT/tools/project-validator.py" ]]; then
    log "Running validator..."
    python "$REPO_ROOT/tools/project-validator.py" > "$EVIDENCE_DIR/validator-output.txt" 2>&1 || true
    pass "Validator output saved"
  fi

  local retro_found=0
  for f in "$SPRINT_DIR"/SPRINT-*-RETRO.md "$SPRINT_DIR"/retrospective.md "$SPRINT_DIR"/retro.md; do
    [[ -f "$f" ]] && retro_found=1 && break
  done
  if [[ $retro_found -eq 0 ]]; then
    fail "Retrospective missing in $SPRINT_DIR"
    return 1
  fi

  pass "Stage 0: PASS"
}

stage_1_gate() {
  log "═══ Stage 1: Deterministic Gate Validation ═══"
  local failures=0

  if [[ ! -f "$EVIDENCE_DIR/closure-check-output.txt" ]]; then
    fail "closure-check-output.txt MISSING"; ((failures++))
  elif ! grep -qi "ELIGIBLE" "$EVIDENCE_DIR/closure-check-output.txt"; then
    fail "closure-check: NOT ELIGIBLE"; ((failures++))
  fi

  if [[ ! -f "$EVIDENCE_DIR/validator-output.txt" ]]; then
    warn "validator-output.txt MISSING (non-blocking)"
  fi

  if [[ ! -f "$DELTA_PACKET" ]]; then
    fail "Delta packet missing: $DELTA_PACKET"
    fail "Copy template: cp docs/ai/prompts/review-delta-packet_v2.md $DELTA_PACKET"
    ((failures++))
  fi

  if [[ -f "$DELTA_PACKET" ]]; then
    local placeholders
    placeholders=$(grep -cE '\{(N|phase|issue|owner|one-line|status|XXX|YYY|ZZZ|count|sha)\}' "$DELTA_PACKET" 2>/dev/null || echo 0)
    if [[ "$placeholders" -gt 0 ]]; then
      fail "Delta packet has $placeholders unfilled placeholders"; ((failures++))
    fi
  fi

  if [[ $failures -gt 0 ]]; then
    fail "Stage 1: BLOCKED ($failures failures)"; return 1
  fi
  pass "Stage 1: PASS"
}

stage_2_verify_packet() {
  log "═══ Stage 2: Delta Packet Verification ═══"
  local required_sections=("REVIEW TYPE" "BASELINE" "SCOPE" "GATE STATUS" "DECISIONS" "CHANGED FILES" "TASK DONE CHECK" "TEST SUMMARY" "EVIDENCE MANIFEST" "CLAIMS TO VERIFY")
  local missing=0

  for section in "${required_sections[@]}"; do
    if ! grep -qi "$section" "$DELTA_PACKET"; then
      fail "Missing section: $section"; ((missing++))
    fi
  done

  if [[ $missing -gt 0 ]]; then
    fail "Stage 2: BLOCKED ($missing missing sections)"; return 1
  fi

  sed -i "s/^- Round:.*/- Round: $CURRENT_ROUND/" "$DELTA_PACKET"
  pass "Stage 2: PASS (Round $CURRENT_ROUND)"
}

stage_3_review() {
  log "═══ Stage 3: AI Review (Round $CURRENT_ROUND) ═══"
  FORCE_REVIEW=1 bash "$REPO_ROOT/tools/ask-gpt-review.sh" "$SPRINT"

  if [[ ! -f "$REVIEW_FILE" ]]; then
    fail "Review file not created: $REVIEW_FILE"; return 1
  fi
  pass "Review written: $REVIEW_FILE"
}

parse_verdict() {
  local verdict
  verdict=$(grep -oP '## 2\. Verdict\s*\n\K(PASS|HOLD|ESCALATE)' "$REVIEW_FILE" 2>/dev/null || \
            grep -oP 'Verdict:?\s*\K(PASS|HOLD|ESCALATE)' "$REVIEW_FILE" 2>/dev/null || \
            grep -oiP '\b(PASS|HOLD|ESCALATE)\b' "$REVIEW_FILE" 2>/dev/null | head -1)
  echo "${verdict:-UNKNOWN}"
}

extract_blockers() {
  sed -n '/Blocking Findings/,/Required Patch Set\|PASS Criteria\|## [0-9]/p' "$REVIEW_FILE" | \
    grep -E '^\s*-?\s*B[0-9]+' || echo ""
}

extract_patches() {
  sed -n '/Required Patch Set/,/PASS Criteria\|## [0-9]/p' "$REVIEW_FILE" | \
    grep -E '^\s*-?\s*P[0-9]+' || echo ""
}

generate_patch_directive() {
  log "Generating patch directive..."
  local blockers patches
  blockers=$(extract_blockers)
  patches=$(extract_patches)

  cat > "$PATCH_DIRECTIVE" << DIRECTIVE
# Patch Directive — Sprint $SPRINT, Round $CURRENT_ROUND

## Source
GPT Review: docs/ai/reviews/S${SPRINT}-GPT-REVIEW.md
Round: $CURRENT_ROUND

## Blockers to Resolve

$blockers

## Required Patches

$patches

## Instructions

For each blocker above:
1. Apply the exact patch described
2. Generate new evidence (rerun the relevant command)
3. Save evidence to evidence/sprint-${SPRINT}/
4. Update the delta packet Section 12 (PATCHES APPLIED) with:
   - Patch ID (P1, P2...)
   - Blocker reference (B1, B2...)
   - What changed
   - Commit SHA
   - New evidence path

## Acceptance Criteria

Each blocker is resolved when:
- [ ] Patch committed to repo
- [ ] Evidence command rerun and raw output saved
- [ ] Delta packet Section 12 updated
- [ ] No new test failures introduced (run full test suite)

## Constraints

- Do NOT rewrite history (no rebase on pushed commits)
- Do NOT add scope — only fix listed blockers
- Do NOT modify files outside blocker scope
- If a blocker is UNRESOLVABLE (requires past-tense artifact, external dependency, etc.), document why in Section 12 with status "UNRESOLVABLE" and reason

## After Patching

\`\`\`bash
python -m pytest --tb=short -q
cd frontend && npx vitest run && cd ..
bash tools/blocker-resolution-check.sh $SPRINT
git add -A && git commit -m "fix(s$SPRINT): resolve R${CURRENT_ROUND} review blockers" && git push
\`\`\`
DIRECTIVE

  pass "Patch directive: $PATCH_DIRECTIVE"
}

dispatch_claude_code() {
  if command -v claude &>/dev/null; then
    log "Dispatching to Claude Code..."
    local prompt
    prompt=$(cat "$PATCH_DIRECTIVE")
    claude --dangerously-skip-permissions --max-turns 50 -p "$prompt" 2>&1 | \
      tee "$EVIDENCE_DIR/claude-code-patch-r${CURRENT_ROUND}.log"
    pass "Claude Code patch complete"
  else
    warn "Claude Code CLI not found. Manual patch required."
    warn "Patch directive: $PATCH_DIRECTIVE"
    exit 0
  fi
}

stage_4_patch_loop() {
  local verdict="$1"

  while [[ "$verdict" == "HOLD" && $CURRENT_ROUND -lt $MAX_ROUNDS ]]; do
    ((CURRENT_ROUND++))
    log "═══ Stage 4: Patch Cycle (Round $CURRENT_ROUND / $MAX_ROUNDS) ═══"

    generate_patch_directive

    if [[ $AUTO_PATCH -eq 1 ]]; then
      dispatch_claude_code
    else
      warn "Manual patch required."
      warn "Patch directive: $PATCH_DIRECTIVE"
      warn "After patching: bash tools/blocker-resolution-check.sh $SPRINT"
      warn "Then re-run: tools/review-loop.sh $SPRINT"
      exit 0
    fi

    log "Running blocker resolution check..."
    local rc=0
    bash "$REPO_ROOT/tools/blocker-resolution-check.sh" "$SPRINT" || rc=$?

    if [[ $rc -eq 2 ]]; then
      warn "UNRESOLVABLE blockers detected"
      stage_5_escalate "UNRESOLVABLE blockers cannot be patched"
      return 0
    elif [[ $rc -eq 1 ]]; then
      fail "Not all blockers resolved — retrying patch"
      continue
    fi

    pass "All blockers resolved — submitting Round $CURRENT_ROUND"
    sed -i "s/^- Round:.*/- Round: $CURRENT_ROUND/" "$DELTA_PACKET"
    sed -i "s/^- Review Type:.*/- Review Type: re-review/" "$DELTA_PACKET"

    stage_3_review
    verdict=$(parse_verdict)
    log "Round $CURRENT_ROUND verdict: $verdict"

    if [[ "$verdict" == "ESCALATE" ]]; then
      stage_5_escalate "GPT issued ESCALATE at Round $CURRENT_ROUND"
      return 0
    fi
  done

  if [[ "$verdict" == "HOLD" && $CURRENT_ROUND -ge $MAX_ROUNDS ]]; then
    stage_5_escalate "Max rounds ($MAX_ROUNDS) reached"
    return 0
  fi

  echo "$verdict"
}

stage_5_escalate() {
  local reason="$1"
  log "═══ Stage 5: Operator Escalation ═══"
  warn "Reason: $reason"

  cat >> "$REVIEW_FILE" << ESCALATION

---

## Operator Escalation

- **Round:** $CURRENT_ROUND
- **Reason:** $reason
- **Action required:**
  1. Override close — document reason, set closure_status=closed
  2. Remediation task — create for next sprint
  3. Waiver — defer with documented waiver

### Remaining Blockers
$(extract_blockers)

### Resolution Log
$(cat "$RESOLUTION_LOG" 2>/dev/null || echo "No resolution log.")
ESCALATION

  warn "Escalation appended to: $REVIEW_FILE"
  warn "Operator action required."
}

main() {
  log "╔════════════════════════════════════════╗"
  log "║  Vezir Review Pipeline — Sprint $SPRINT"
  log "║  Auto-patch: $([ $AUTO_PATCH -eq 1 ] && echo 'ON' || echo 'OFF')"
  log "╚════════════════════════════════════════╝"
  echo ""

  stage_0_preflight || { fail "Stopped at Stage 0"; exit 1; }
  echo ""
  stage_1_gate || { fail "Stopped at Stage 1"; exit 1; }
  echo ""
  stage_2_verify_packet || { fail "Stopped at Stage 2"; exit 1; }
  echo ""
  stage_3_review || { fail "Stopped at Stage 3"; exit 1; }
  echo ""

  local verdict
  verdict=$(parse_verdict)
  log "Round $CURRENT_ROUND verdict: $verdict"

  case "$verdict" in
    PASS)
      pass "═══ PIPELINE COMPLETE — PASS ═══"
      pass "Sprint $SPRINT eligible for operator close"
      ;;
    HOLD)
      warn "HOLD — entering patch cycle"
      echo ""
      result=$(stage_4_patch_loop "$verdict")
      [[ "$result" == "PASS" ]] && pass "═══ PIPELINE COMPLETE — PASS (Round $CURRENT_ROUND) ═══"
      ;;
    ESCALATE)
      stage_5_escalate "GPT issued ESCALATE at Round 1"
      ;;
    *)
      fail "Unknown verdict: $verdict"; exit 1
      ;;
  esac
}

main
