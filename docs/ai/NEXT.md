# Next Step

**Last updated:** 2026-03-23

---

## Phase 3-E: Multi-Provider (Claude + Ollama)

**Goal:** Phase 3-D complete. Add Claude and Ollama as alternative LLM providers, selectable via agent config.

**Steps:**
1. Implement `agent/providers/claude_provider.py` (Anthropic SDK)
2. Implement `agent/providers/ollama_provider.py` (local HTTP API)
3. Create `agent/agent-registry.json` for provider selection
4. Update agent runner to select provider from registry
5. Test: same request works with GPT-4o, Claude, and Ollama

**After this:** Phase 3-F (Multi-Agent Foundation — Mission Controller).
