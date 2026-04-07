# Secrets Contract

**Effective:** Sprint 24+
**Owner:** AKCA (Operator)
**Last updated:** 2026-04-07

---

## Active Secrets

| Secret | Scope | Used By | Owner | Created |
|--------|-------|---------|-------|---------|
| `GITHUB_TOKEN` | Auto-generated | All workflows | GitHub | Auto |
| `PROJECT_TOKEN` | Project V2 read/write + repo | `status-sync.yml`, `project-auto-add.yml` | AKCA | 2026-04-07 (rotated) |

## Secret Details

### GITHUB_TOKEN (automatic)

- **Type:** GitHub-generated per workflow run
- **Permissions:** Defined in workflow `permissions:` block
- **Rotation:** Automatic (per-run, expires after workflow)
- **No action required.**

### PROJECT_TOKEN

- **Type:** Classic PAT with `repo` + `project` scopes
- **Purpose:** Project V2 field mutations (status-sync, project-auto-add workflows)
- **Required scopes:** `repo` (full), `project` (read/write)
- **Expiration:** 90 days from creation (expires Jul 06, 2026)
- **Consumer:** `.github/workflows/status-sync.yml`, `.github/workflows/project-auto-add.yml` — used when `PROJECT_TOKEN` secret exists, falls back to `GITHUB_TOKEN` otherwise
- **Note:** Fine-grained PATs do not support `project` scope for personal accounts — classic PAT required (B-148)
- **Fallback behavior:** Without `PROJECT_TOKEN`, status-sync skips project field update with "No project found" log

#### Rotation Runbook

1. **Generate new token:**
   - GitHub Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
   - Scopes: `repo` (full) + `project` (read/write)
   - Expiration: 90 days recommended
   - Note: Fine-grained PATs lack `project` scope for personal accounts

2. **Update secret:**
   - Repo Settings → Secrets and variables → Actions
   - Edit `PROJECT_TOKEN` → paste new token

3. **Verify:**
   - Create or update a PR with `[SN-N.M]` title pattern
   - Check status-sync workflow run log for "SUCCESS: Issue #N status updated"

4. **Rollback:**
   - Delete `PROJECT_TOKEN` secret → workflow falls back to `GITHUB_TOKEN`
   - Project field updates will stop but PR/issue operations continue normally

#### Rotation Triggers

- Token expiration (check GitHub PAT page)
- Security incident requiring credential rotation
- Scope changes to Project V2

---

## Workflow Secret Usage Inventory

| Workflow | Secret | Purpose |
|----------|--------|---------|
| `ci.yml` | — | No secrets needed |
| `benchmark.yml` | — | No secrets needed |
| `close-sprint-issues.yml` | `GITHUB_TOKEN` | Close issues via gh CLI |
| `closure-preflight.yml` | `GITHUB_TOKEN` | Issue/branch status queries |
| `issue-from-plan.yml` | `GITHUB_TOKEN` | Create issues, commit files |
| `project-auto-add.yml` | `GITHUB_TOKEN` | Add issues to Project V2 |
| `status-sync.yml` | `PROJECT_TOKEN` / `GITHUB_TOKEN` | Project V2 field mutations |

---

## Rules

1. No undocumented secrets — every secret in workflow files must appear in this contract
2. No secrets with unlimited expiration — use 90-day rotation cycle
3. Rotation ownership is explicit — see Owner column
4. Fallback behavior documented for every custom secret
5. Secret grep verification: `grep -r "secrets\." .github/workflows/ --include="*.yml"`
