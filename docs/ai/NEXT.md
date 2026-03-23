# Next Step

**Last updated:** 2026-03-23

---

## Phase 3-C: Risk Engine + Approval Service

**Goal:** Phase 3-B complete. Add risk classification and user approval flow for medium/high risk tool calls.

**Steps:**
1. Implement risk engine — classify tool calls by risk level (low/medium/high)
2. Implement approval service — Telegram-based approval flow for medium/high risk
3. Integrate approval service with agent runner
4. Add approval timeout and auto-deny for unresponded requests
5. Test: medium-risk tool (write_file) requires user approval via Telegram
6. Test: low-risk tool (get_system_info) executes without approval

**After this:** Phase 3-D (Multi-agent routing + Mission Controller).
