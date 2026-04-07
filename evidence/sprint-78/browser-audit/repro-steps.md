# Reproduction Steps — S78 Browser Audit Findings

## Pre-condition for all findings

1. Backend API on port 8003 must be **stopped**
2. Frontend dev server on port 4000 must be **running** (`cd frontend && npm run dev`)
3. Open browser to http://localhost:4000

---

## UX-001: Technical error message on API failure

1. Navigate to http://localhost:4000/missions
2. Observe red error banner
3. Read error text: "Failed to execute 'text' on 'Response': body stream already read"
4. Same error appears on /health, /approvals, /telemetry, /templates, /costs, /projects

---

## UX-002: Health page no Retry button

1. Navigate to http://localhost:4000/health
2. Observe "Failed to load health" and "Failed to load capabilities" errors
3. Note: no Retry button is present (unlike /missions, /approvals, /templates which have Retry)

---

## UX-003: Agent Health silent empty state

1. Navigate to http://localhost:4000/agents
2. Observe "Agent Health" heading and "LLM PROVIDERS" label
3. Below that: completely blank. No error, no loading indicator, no empty state message.
4. Compare with /missions which shows explicit error banner.

---

## UX-004: Projects contradictory error + empty

1. Navigate to http://localhost:4000/projects
2. Observe red error text AND "No projects found." text both visible
3. Header shows "Projects (0)" — implies successful zero-result response
4. Contradictory: error state and empty state shown simultaneously

---

## UX-005: Monitoring Dashboard stuck loading

1. Navigate to http://localhost:4000/monitoring
2. Observe "Error: HTTP 500" red banner at top
3. Below: "Loading summary..." text that never resolves
4. Below: "Missions (0)" and "No missions recorded yet." sections
5. Right panel: "Live Events: Disconnected" with Connect button
6. Multiple conflicting states visible simultaneously

---

## UX-006: Sidebar no tooltip

1. On any page, observe the left sidebar (collapsed state)
2. Hover over any emoji icon
3. Note: icon highlights but no tooltip text appears
4. User cannot identify which icon maps to which page without expanding sidebar

---

## UX-007: SSE status misleading

1. On any page, observe top-right corner of header
2. Note: shows "Polling 30s" with green/yellow dot
3. Backend is offline, but status implies active successful polling
4. On some pages, briefly shows "Reconnecting..." then settles to "Polling 30s"
