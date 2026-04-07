# Browser DOM Observations — S78 Browser Audit

**Date:** 2026-04-07
**Mode:** observe_only

---

## Layout Structure (all pages)

- Sidebar: fixed left, collapsed by default (~50px wide), emoji icons, "Expand menu" button at bottom
- Header: "Vezir" title left, SSE status indicator right ("Polling 30s" / "Reconnecting...")
- Main content: full width minus sidebar
- No breadcrumbs on any page
- No footer

## Sidebar (navigation)

- 9 navigation links: Missions, Health, Approvals, Telemetry, Monitoring, Templates, Costs, Agents, Projects
- Collapsed state: only emoji icons visible, no text labels, no tooltips
- Expanded state: text labels appear (via "Expand menu" button)
- Active page highlighted with brighter icon
- Accessibility: links have text content in DOM (accessible to screen readers)
- No keyboard focus indicator visible on sidebar items

## Error State Patterns

### Pattern A: Red banner + technical error + Retry (Missions, Approvals, Templates)
- Red-bordered container
- Bold "Failed to load {resource}" heading
- Technical error message below
- Red "Retry" button

### Pattern B: Red banner + technical error, NO Retry (Health, Costs, Telemetry)
- Same red banner
- No retry button
- User stuck with no recovery action

### Pattern C: Silent empty (Agents)
- No error banner at all
- Section headers present but empty content
- Indistinguishable from "no data" state

### Pattern D: Mixed states (Monitoring)
- Error banner + loading spinner + empty states all visible simultaneously
- "Loading summary..." text never resolves
- Multiple widget sections (Missions, Structured Logs, Live Events) each with own state

### Pattern E: Error + empty (Projects)
- Error text AND "No projects found" both visible
- Count shows "(0)" implying successful response

## SSE Status (header, all pages)

- Top-right corner
- Shows colored dot + text
- States observed: "Polling 30s" (green dot), "Reconnecting..." (yellow dot)
- "No events yet" present in accessibility tree
- Does NOT show "Disconnected" or "Error" state when API unreachable

## 404 Page

- Clean centered layout
- Large "404" heading
- "Page not found" subtitle
- "Go to Missions" button (good CTA)
- Sidebar still visible (consistent navigation)
