# Next Step

**Last updated:** 2026-03-23

---

## Phase 3-B: Core Agent Runner with Claude

**Goal:** Phase 3-A design freeze complete. Implement the first working agent that handles requests end-to-end via Telegram.

**Steps:**
1. Create `agent/` directory with Python project structure
2. Implement `agent/oc-agent-runner.py` (main orchestrator)
3. Implement `agent/providers/claude_provider.py` (Anthropic SDK)
4. Implement `agent/services/mcp_client.py` (MCP HTTP client)
5. Implement `agent/services/tool_gateway.py` (basic policy check)
6. Create `wsl/oc-agent-run` (WSL-Windows bridge)
7. Create config files (`agent-registry.json`, `agent-config.json`)
8. Test: "CPU kullanimi kac?" works end-to-end via Telegram

**After this:** Phase 3-C (Risk Engine + Approval Service).
