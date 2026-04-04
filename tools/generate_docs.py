"""Docs-as-product generator — B-113.

Usage: python tools/generate_docs.py
Output: docs/generated/api-reference.md, architecture.md, onboarding.md

Reads the live OpenAPI spec and system state to produce developer-facing
documentation. Re-run after every sprint closure to keep docs current.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OC_ROOT = SCRIPT_DIR.parent
OPENAPI_PATH = OC_ROOT / "docs" / "api" / "openapi.json"
OUTPUT_DIR = OC_ROOT / "docs" / "generated"


# ── Helpers ────────────────────────────────────────────────────────

def _load_openapi() -> dict:
    if not OPENAPI_PATH.exists():
        print(f"ERROR: OpenAPI spec not found at {OPENAPI_PATH}")
        print("Run: cd agent && python ../tools/export_openapi.py")
        sys.exit(1)
    return json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))


def _method_upper(method: str) -> str:
    return method.upper()


# ── API Reference Generator ───────────────────────────────────────

def generate_api_reference(spec: dict) -> str:
    """Generate markdown API reference from OpenAPI spec."""
    lines = [
        "# Vezir Platform — API Reference",
        "",
        f"**Auto-generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**OpenAPI version:** {spec.get('openapi', '?')}",
        f"**Base URL:** `http://127.0.0.1:8003`",
        "",
        "---",
        "",
    ]

    # Group endpoints by tag
    paths = spec.get("paths", {})
    tag_groups: dict[str, list] = {}

    for path, methods in sorted(paths.items()):
        for method, operation in sorted(methods.items()):
            if method in ("parameters", "servers", "summary", "description"):
                continue
            tags = operation.get("tags", ["other"])
            tag = tags[0] if tags else "other"
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append({
                "method": method,
                "path": path,
                "summary": operation.get("summary", ""),
                "operation_id": operation.get("operationId", ""),
                "responses": operation.get("responses", {}),
                "parameters": operation.get("parameters", []),
                "request_body": operation.get("requestBody"),
            })

    # Table of contents
    lines.append("## Contents")
    lines.append("")
    for tag in sorted(tag_groups.keys()):
        count = len(tag_groups[tag])
        lines.append(f"- [{tag}](#{tag.lower().replace(' ', '-')}) ({count} endpoints)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Endpoint details by tag
    total = 0
    for tag in sorted(tag_groups.keys()):
        endpoints = tag_groups[tag]
        total += len(endpoints)
        lines.append(f"## {tag}")
        lines.append("")
        lines.append("| Method | Path | Summary |")
        lines.append("|--------|------|---------|")
        for ep in endpoints:
            m = _method_upper(ep["method"])
            lines.append(f"| `{m}` | `{ep['path']}` | {ep['summary']} |")
        lines.append("")

        # Detail for each endpoint
        for ep in endpoints:
            m = _method_upper(ep["method"])
            lines.append(f"### `{m} {ep['path']}`")
            lines.append("")
            if ep["summary"]:
                lines.append(f"> {ep['summary']}")
                lines.append("")
            if ep["operation_id"]:
                lines.append(f"**Operation ID:** `{ep['operation_id']}`")
                lines.append("")

            # Parameters
            params = ep.get("parameters", [])
            if params:
                lines.append("**Parameters:**")
                lines.append("")
                lines.append("| Name | In | Type | Required |")
                lines.append("|------|----|------|----------|")
                for p in params:
                    schema = p.get("schema", {})
                    ptype = schema.get("type", "string")
                    req = "Yes" if p.get("required") else "No"
                    lines.append(f"| `{p['name']}` | {p.get('in', '?')} | {ptype} | {req} |")
                lines.append("")

            # Request body
            rb = ep.get("request_body")
            if rb:
                content = rb.get("content", {})
                for ct, ct_spec in content.items():
                    ref = ct_spec.get("schema", {}).get("$ref", "")
                    schema_name = ref.split("/")[-1] if ref else "object"
                    lines.append(f"**Request Body:** `{ct}` — `{schema_name}`")
                    lines.append("")

            # Responses
            responses = ep.get("responses", {})
            if responses:
                lines.append("**Responses:**")
                lines.append("")
                for code, resp in sorted(responses.items()):
                    desc = resp.get("description", "")
                    lines.append(f"- `{code}`: {desc}")
                lines.append("")

            lines.append("---")
            lines.append("")

    # Summary
    lines.append(f"**Total endpoints:** {total}")
    lines.append("")
    return "\n".join(lines)


# ── Architecture Overview Generator ───────────────────────────────

def generate_architecture() -> str:
    """Generate architecture overview from known system structure."""
    lines = [
        "# Vezir Platform — Architecture Overview",
        "",
        f"**Auto-generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "---",
        "",
        "## System Overview",
        "",
        "Vezir is a governed multi-agent mission platform that orchestrates",
        "9 specialist AI roles through a quality-gated, 11-state mission",
        "state machine. It integrates 3 LLM providers (GPT-4o, Claude Sonnet,",
        "Ollama) and 24 MCP tools via a Windows bridge.",
        "",
        "## Component Map",
        "",
        "```",
        "+------------------+     +------------------+     +------------------+",
        "|  Vezir UI (3000) |<--->| Vezir API (8003) |<--->| Mission Controller|",
        "|  React + Vite    |     | FastAPI + Uvicorn |     | 9 roles, 3 gates |",
        "+------------------+     +------------------+     +------------------+",
        "                              |                          |",
        "                              v                          v",
        "                    +------------------+     +------------------+",
        "                    | SSE Manager      |     | Policy Engine    |",
        "                    | Live updates     |     | YAML rules       |",
        "                    +------------------+     +------------------+",
        "                              |                          |",
        "                              v                          v",
        "                    +------------------+     +------------------+",
        "                    | Persistence      |     | LLM Providers    |",
        "                    | JSON file store  |     | GPT/Claude/Ollama|",
        "                    +------------------+     +------------------+",
        "                              |                          |",
        "                              v                          v",
        "                    +------------------+     +------------------+",
        "                    | Observability    |     | WMCP Bridge(8001)|",
        "                    | OTel + Alerts    |     | 24 MCP tools     |",
        "                    +------------------+     +------------------+",
        "```",
        "",
        "## Port Map",
        "",
        "| Port | Service | Protocol |",
        "|------|---------|----------|",
        "| 3000 | Vezir UI (React + Vite + Tailwind) | HTTP |",
        "| 8001 | WMCP (Windows MCP Proxy) | HTTP |",
        "| 8003 | Vezir API (FastAPI + Uvicorn) | HTTP/HTTPS |",
        "| 9000 | Math Service (example) | HTTP |",
        "",
        "## Mission State Machine",
        "",
        "11 states with governed transitions:",
        "",
        "```",
        "CREATED -> PLANNING -> READY -> RUNNING -> COMPLETED",
        "                                  |",
        "                                  +-> FAILED",
        "                                  +-> TIMED_OUT",
        "                                  +-> WAITING_APPROVAL -> RUNNING",
        "                                  +-> PAUSED -> RUNNING",
        "                                  +-> CANCELLED",
        "```",
        "",
        "## Specialist Roles (9)",
        "",
        "| # | Role | Responsibility |",
        "|---|------|---------------|",
        "| 1 | Planner | Mission decomposition, stage planning |",
        "| 2 | Researcher | Information gathering, context building |",
        "| 3 | Coder | Code generation, modification |",
        "| 4 | Reviewer | Quality review, gate enforcement |",
        "| 5 | Tester | Test execution, validation |",
        "| 6 | Deployer | Deployment, environment management |",
        "| 7 | Documenter | Documentation generation |",
        "| 8 | Optimizer | Performance optimization |",
        "| 9 | Security | Security analysis, vulnerability scanning |",
        "",
        "## Quality Gates (3)",
        "",
        "| Gate | Trigger | Action |",
        "|------|---------|--------|",
        "| G1 — Planning Gate | After PLANNING | Validates stage plan completeness |",
        "| G2 — Execution Gate | After each stage | Validates stage output quality |",
        "| G3 — Final Gate | Before COMPLETED | Validates all artifacts, coverage |",
        "",
        "## Governance",
        "",
        "- 132+ frozen architectural decisions (D-001 to D-133)",
        "- 18-step sprint closure checklist (Rule 16)",
        "- File-persisted state (atomic writes: temp -> fsync -> os.replace)",
        "- EventBus: 28 event types, 14 governance handlers",
        "- Alert engine: 9 rules with Telegram notification",
        "",
        "## Data Flow",
        "",
        "1. **Request** arrives via Dashboard UI or Telegram",
        "2. **Mission Create API** writes mission JSON, spawns controller thread",
        "3. **Controller** plans stages via Planner role",
        "4. **Quality Gate G1** validates the plan",
        "5. **Per-stage execution**: policy check -> role dispatch -> LLM call -> tool use",
        "6. **Quality Gate G2** validates each stage output",
        "7. **Quality Gate G3** validates final mission",
        "8. **SSE events** broadcast state changes to UI in real-time",
        "9. **Observability layer** records traces, metrics, structured logs",
        "",
        "## Key Technologies",
        "",
        "| Layer | Technology |",
        "|-------|-----------|",
        "| Backend | Python 3.14, FastAPI, Pydantic V2 |",
        "| Frontend | React 18, Vite, Tailwind CSS, TypeScript |",
        "| LLM | GPT-4o (OpenAI), Claude Sonnet (Anthropic), Ollama (local) |",
        "| Observability | OpenTelemetry (traces + metrics), structured JSON logs |",
        "| CI/CD | GitHub Actions (7 workflows), branch protection |",
        "| Testing | pytest (backend), Vitest (frontend), Playwright (E2E) |",
        "",
    ]
    return "\n".join(lines)


# ── Developer Onboarding Guide ────────────────────────────────────

def generate_onboarding() -> str:
    """Generate developer onboarding guide."""
    lines = [
        "# Vezir Platform — Developer Onboarding Guide",
        "",
        f"**Auto-generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "---",
        "",
        "## Prerequisites",
        "",
        "- **OS:** Windows 11 with WSL2",
        "- **Python:** 3.14+",
        "- **Node.js:** 20+",
        "- **Git:** 2.40+",
        "",
        "## Quick Start",
        "",
        "### 1. Clone the repository",
        "",
        "```bash",
        "git clone https://github.com/ahmetcagriakca/vezir.git",
        "cd vezir",
        "```",
        "",
        "### 2. Backend setup",
        "",
        "```bash",
        "cd agent",
        "pip install -r requirements.txt",
        "```",
        "",
        "### 3. Frontend setup",
        "",
        "```bash",
        "cd frontend",
        "npm install",
        "```",
        "",
        "### 4. Start services",
        "",
        "```bash",
        "# Terminal 1: Backend API",
        "cd agent && python -m api.server",
        "",
        "# Terminal 2: Frontend dev server",
        "cd frontend && npm run dev",
        "```",
        "",
        "The API runs on http://127.0.0.1:8003, UI on http://localhost:3000.",
        "",
        "## Running Tests",
        "",
        "### Backend (pytest)",
        "",
        "```bash",
        "cd agent && python -m pytest tests/ -v",
        "```",
        "",
        "### Frontend (Vitest)",
        "",
        "```bash",
        "cd frontend && npx vitest run",
        "```",
        "",
        "### TypeScript check",
        "",
        "```bash",
        "cd frontend && npx tsc --noEmit",
        "```",
        "",
        "### Playwright E2E",
        "",
        "```bash",
        "cd frontend && npx playwright test",
        "```",
        "",
        "### All-in-one preflight",
        "",
        "```bash",
        "bash tools/preflight.sh",
        "```",
        "",
        "## Project Structure",
        "",
        "```",
        "vezir/",
        "  agent/                  # Python backend",
        "    api/                  # FastAPI routers (~82 endpoints)",
        "    mission/              # Mission controller, state machine, roles",
        "    events/               # EventBus (28 event types)",
        "    observability/        # OTel tracing, metrics, alerts",
        "    persistence/          # JSON file stores",
        "    services/             # Risk engine, approval, etc.",
        "    auth/                 # Session, middleware, isolation",
        "    tests/                # Backend test suite",
        "  frontend/               # React dashboard",
        "    src/api/              # Generated API client (from OpenAPI)",
        "    src/components/       # React components",
        "    src/pages/            # Route pages",
        "  config/",
        "    policies/             # YAML policy rules",
        "    templates/            # Mission presets",
        "    tls/                  # TLS certificates",
        "  tools/                  # CLI tools (export, generate, audit)",
        "  docs/",
        "    ai/                   # Governance docs (STATE, NEXT, DECISIONS)",
        "    api/                  # OpenAPI spec",
        "    generated/            # Auto-generated docs (this tool)",
        "  bridge/                 # PowerShell MCP bridge",
        "```",
        "",
        "## Key Conventions",
        "",
        "- **Atomic writes:** Always use `atomic_write_json()` — never write directly",
        "- **Decisions:** Frozen as D-XXX in `docs/ai/DECISIONS.md`",
        "- **Commit format:** `Sprint N Task X.Y: <description>`",
        "- **Tests required:** Every feature must have tests before merge",
        "- **OpenAPI sync:** Run `python tools/export_openapi.py` after API changes",
        "- **SDK sync:** Run `cd frontend && npm run generate:api` after OpenAPI update",
        "",
        "## API Authentication",
        "",
        "Mission creation requires an `Authorization: Bearer <token>` header.",
        "In development, the token is configured via environment variable.",
        "",
        "## Useful Commands",
        "",
        "```bash",
        "# Export OpenAPI spec",
        "cd agent && python ../tools/export_openapi.py",
        "",
        "# Regenerate frontend API types",
        "cd frontend && npm run generate:api",
        "",
        "# Generate documentation",
        "python tools/generate_docs.py",
        "",
        "# Run benchmark (evidence only)",
        "python tools/benchmark_api.py",
        "",
        "# Generate backlog from GitHub",
        "python tools/generate-backlog.py",
        "```",
        "",
        "## Getting Help",
        "",
        "- System state: `docs/ai/STATE.md`",
        "- Roadmap: `docs/ai/NEXT.md`",
        "- Decisions: `docs/ai/DECISIONS.md`",
        "- Governance: `docs/ai/GOVERNANCE.md`",
        "- Backlog: `docs/ai/BACKLOG.md`",
        "",
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    spec = _load_openapi()

    # 1. API Reference
    api_ref = generate_api_reference(spec)
    api_path = OUTPUT_DIR / "api-reference.md"
    api_path.write_text(api_ref, encoding="utf-8")
    print(f"[1/3] API reference: {api_path}")

    # 2. Architecture overview
    arch = generate_architecture()
    arch_path = OUTPUT_DIR / "architecture.md"
    arch_path.write_text(arch, encoding="utf-8")
    print(f"[2/3] Architecture: {arch_path}")

    # 3. Onboarding guide
    onboard = generate_onboarding()
    onboard_path = OUTPUT_DIR / "onboarding.md"
    onboard_path.write_text(onboard, encoding="utf-8")
    print(f"[3/3] Onboarding: {onboard_path}")

    # Summary
    paths = spec.get("paths", {})
    endpoint_count = sum(len(m) for m in paths.values())
    print(f"\nDocs generated: {endpoint_count} API endpoints documented, "
          f"3 files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
