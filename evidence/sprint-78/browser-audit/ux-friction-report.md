# UX Friction Report — Sprint 78 Browser Audit

**Date:** 2026-04-07
**Mode:** observe_only
**Target:** http://localhost:4000 (Backend API offline)
**Pages audited:** /missions, /health, /approvals, /telemetry, /monitoring, /templates, /costs, /agents, /projects, /nonexistent-page

---

## Findings

### UX-001: Technical error message exposed to user on API failure

- **ID:** UX-001
- **Title:** Technical error "body stream already read" shown to user on backend failure
- **Category:** failure_visibility
- **Severity:** high
- **Reproducibility:** always
- **Page:** /missions, /health, /approvals, /telemetry, /templates, /costs, /projects
- **Repro steps:**
  1. Stop backend API (port 8003)
  2. Navigate to any page (e.g., /missions)
  3. Observe error banner
- **Expected:** User-friendly message: "Backend API is not reachable. Please start the API server or check your connection." with clear recovery action.
- **Actual:** Shows `Failed to execute 'text' on 'Response': body stream already read` — an internal browser/fetch API error message that means nothing to a user.
- **Console errors:** None visible (tracking started after page load)
- **Network errors:** Connection refused to localhost:8003 (all API calls fail)
- **Screenshot:** screenshot-evidence/UX-001-missions-error.png (ss_6911kxpcc)
- **Owner:** TBD
- **Status:** open
- **Stuck party:** user — user sees cryptic error, cannot distinguish "API down" from "bug in frontend"

---

### UX-002: Health page shows no retry button on failure

- **ID:** UX-002
- **Title:** Health page has no Retry button when API fails
- **Category:** failure_visibility
- **Severity:** medium
- **Reproducibility:** always
- **Page:** /health
- **Repro steps:**
  1. Stop backend API
  2. Navigate to /health
  3. Observe error state — no retry button available
- **Expected:** Retry button consistent with other pages (Missions, Approvals, Templates all have Retry)
- **Actual:** "Failed to load health" + "Failed to load capabilities" with no recovery action. User must manually refresh browser.
- **Console errors:** none
- **Network errors:** Connection refused
- **Screenshot:** screenshot-evidence/UX-002-health-no-retry.png (ss_6703gb1l0)
- **Owner:** TBD
- **Status:** open
- **Stuck party:** user — no recovery action available

---

### UX-003: Agent Health page shows silent empty state on API failure

- **ID:** UX-003
- **Title:** Agent Health page silently shows empty content — no error message
- **Category:** failure_visibility
- **Severity:** high
- **Reproducibility:** always
- **Page:** /agents
- **Repro steps:**
  1. Stop backend API
  2. Navigate to /agents
  3. Observe page
- **Expected:** Error banner with "Failed to load agent data" + Retry button (consistent with other pages)
- **Actual:** Page shows "Agent Health" heading and "LLM PROVIDERS" label, then completely blank. No error message, no loading indicator, no retry. User cannot tell if data is loading, empty, or failed.
- **Console errors:** none
- **Network errors:** Connection refused
- **Screenshot:** screenshot-evidence/UX-003-agents-silent-empty.png (ss_4060ejms9)
- **Owner:** TBD
- **Status:** open
- **Stuck party:** user — indistinguishable from "no agents configured" vs "API unreachable"

---

### UX-004: Projects page shows contradictory error + empty state simultaneously

- **ID:** UX-004
- **Title:** Projects shows error message AND "No projects found" at the same time
- **Category:** data_quality_display
- **Severity:** medium
- **Reproducibility:** always
- **Page:** /projects
- **Repro steps:**
  1. Stop backend API
  2. Navigate to /projects
  3. Observe both error text and empty state text visible
- **Expected:** Show EITHER error state (with retry) OR empty state — never both simultaneously. On API failure, show error. On successful empty response, show "No projects found" with CTA.
- **Actual:** Red error text `Error: Failed to execute 'text' on 'Response': body stream already read` AND gray `No projects found.` both visible. Count shows "Projects (0)" which implies successful fetch of zero items.
- **Console errors:** none
- **Network errors:** Connection refused
- **Screenshot:** screenshot-evidence/UX-004-projects-contradictory.png (ss_5638mk39f)
- **Owner:** TBD
- **Status:** open
- **Stuck party:** user — conflicting signals: "0 projects" suggests success, error text suggests failure

---

### UX-005: Monitoring Dashboard shows "Loading summary..." stuck state with HTTP 500

- **ID:** UX-005
- **Title:** Monitoring Dashboard stuck in mixed error/loading state
- **Category:** latency_perception
- **Severity:** high
- **Reproducibility:** always
- **Page:** /monitoring
- **Repro steps:**
  1. Stop backend API
  2. Navigate to /monitoring
  3. Observe page layout
- **Expected:** Clear error state: "API unavailable" with retry option. Summary section should not show perpetual "Loading summary..."
- **Actual:** Three simultaneous states visible: (1) Red "Error: HTTP 500" banner, (2) "Loading summary..." text that never resolves, (3) "Missions (0)" / "No missions recorded yet" empty states, (4) "Live Events: Disconnected" with Connect button. The "HTTP 500" is odd since backend is down (should be connection refused, not 500).
- **Console errors:** none
- **Network errors:** Connection refused (the HTTP 500 text may be a catch-all)
- **Screenshot:** screenshot-evidence/UX-005-monitoring-stuck.png (ss_5905dnunz)
- **Owner:** TBD
- **Status:** open
- **Stuck party:** both — agent side (SSE disconnected, no data) + user side (cannot distinguish server error from unreachable)

---

### UX-006: Sidebar icons have no tooltip in collapsed state

- **ID:** UX-006
- **Title:** Collapsed sidebar uses emoji icons with no tooltip labels
- **Category:** navigation_confusion
- **Severity:** medium
- **Reproducibility:** always
- **Page:** all pages
- **Repro steps:**
  1. Observe sidebar in default collapsed state
  2. Hover over any icon
  3. No tooltip appears showing page name
- **Expected:** On hover, show tooltip with page name (e.g., "Missions", "Health", "Approvals"). Alternatively, use recognizable standard icons with aria-label visible on hover.
- **Actual:** Sidebar shows colorful emoji icons (target, heart, lock, chart, envelope, clipboard, coin, robot, folder). Hover shows highlight but no tooltip text. User must expand sidebar or guess which emoji maps to which page. Accessibility tree does have text labels (good for screen readers) but visual users get no hover hint.
- **Console errors:** none
- **Network errors:** none
- **Screenshot:** screenshot-evidence/UX-006-sidebar-no-tooltip.png (ss_6859w2o7j)
- **Owner:** TBD
- **Status:** open
- **Stuck party:** user — must memorize emoji-to-page mapping or always expand sidebar

---

### UX-007: SSE status shows "Polling 30s" with green dot when backend is offline

- **ID:** UX-007
- **Title:** SSE status indicator misleading — shows active polling state when backend unreachable
- **Category:** agent_stuck_vs_user_stuck
- **Severity:** medium
- **Reproducibility:** always
- **Page:** all pages (top-right header)
- **Repro steps:**
  1. Stop backend API
  2. Navigate to any page
  3. Observe top-right status indicator
- **Expected:** Red/yellow indicator with "Disconnected" or "API Unreachable" text. Should match the actual connection state.
- **Actual:** Shows "Polling 30s" with a green/yellow dot, implying the system is actively and successfully polling. Some pages show "Reconnecting..." briefly but then settle to "Polling 30s". This gives false confidence that the system is operational.
- **Console errors:** none
- **Network errors:** SSE connection fails repeatedly
- **Screenshot:** screenshot-evidence/UX-007-sse-misleading.png (ss_6911kxpcc)
- **Owner:** TBD
- **Status:** open
- **Stuck party:** both — user thinks system is working (polling), agent cannot receive events

---

## Summary

| Metric | Value |
|--------|-------|
| Total findings | 7 |
| Categories covered | 5 (failure_visibility, data_quality_display, latency_perception, navigation_confusion, agent_stuck_vs_user_stuck) |
| Severity breakdown | high: 3, medium: 4 |
| Stuck party breakdown | user: 5, both: 2 |

### Key Theme

The dominant issue is **failure visibility when backend is offline**. Every page except /agents shows a technical error message ("body stream already read") that leaks internal fetch API internals. /agents is worse — it shows nothing at all. The SSE status indicator adds confusion by showing an "active" state when the connection is down.
