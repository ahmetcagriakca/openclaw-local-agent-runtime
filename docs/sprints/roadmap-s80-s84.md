# Sprint Roadmap — S80 → S84

**Created:** 2026-04-07
**Phase:** 10 (continued)
**Baseline:** S79 closed, 2276 tests, 146+2 decisions, 0 blockers

---

## Overview

| Sprint | Title | Class | Prerequisite | Est. Size |
|--------|-------|-------|-------------|-----------|
| **S80** | Housekeeping + Dependency Upgrades | Governance + DevEx | None | Small |
| **S81** | EventBus Production Wiring (D-147) | Product | S80 | Medium |
| **S82** | Docker Production Image (D-116) | DevEx + Ops | None | Medium |
| **S83** | D-150 Capability Routing Transition | Architecture | Operator review | Large |
| **S84** | SSO/RBAC Full External Auth | Security | S80 | Large |

## Item Mapping

| Carry-Forward Item | Sprint | Status |
|-------------------|--------|--------|
| Close stale S79 issues + B-148 | S80 | Planned |
| eslint 9→10 migration | S80 | Planned |
| vite 6→8 + plugin-react | S80 | Planned |
| Doc hygiene (NEXT.md, open-items.md) | S80 | Planned |
| PROJECT_TOKEN CI verification | S80 | Planned |
| EventBus production wiring (D-147) | S81 | Planned |
| Docker prod image optimization (D-116) | S82 | Planned |
| D-150 Capability Routing Transition | S83 | Needs operator review |
| SSO/RBAC full external auth (D-104/D-108) | S84 | Planned |

## Out of Sprint Scope

| Item | Reason |
|------|--------|
| D-021→D-058 extraction | AKCA-assigned decision debt, non-blocking |
| Dependabot security alerts (2) | Pre-existing, covered by eslint/vite upgrades in S80 |

## Recommended Execution Order

1. **S80** first — cleans up governance debt, unblocks CI verification
2. **S81** or **S82** — independent, can run in any order
3. **S83** — requires D-150 operator review, can start design while S81/S82 run
4. **S84** — largest scope, benefits from all prior cleanup
