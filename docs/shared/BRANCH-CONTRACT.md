# Branch Naming Contract

**Effective:** Sprint 19+
**Owner:** Operator (AKCA)

---

## Branch Naming Pattern

```
sprint-N/tN.M-slug
sprint-N/tN.M.K-slug
```

- `N` = sprint number
- `M` = task number
- `K` = optional sub-task number
- `slug` = short kebab-case description
- Dots allowed in branch names

**Examples:**
- `sprint-19/t19.1-plan-schema`
- `sprint-19/t19.5-branch-contract`
- `sprint-20/t20.3.1-field-config`

## Rules

1. **Branch-per-task is mandatory.** Every implementation task gets its own branch.
2. **No direct commits to `main`.** All changes go through PR.
3. **Gate tasks are branch-exempt.** Gates (G1, G2, RETRO, CLOSURE) produce review/verdict text only, never code changes.
4. **Gate finding requiring code → separate remediation task** with its own branch. Gate task itself stays branch-exempt.
5. **Merge: manual after gate PASS.** Operator authority.
6. **PR-per-task: deferred.** Operator decides after retrospective.

## Validation

Use `tools/check-branch-name.sh` to validate the current branch:

```bash
bash tools/check-branch-name.sh
```

Can be used as a pre-push hook or manual check.

## main Branch Protection

- `main` is protected via GitHub branch protection rules
- Require a pull request before merging (no direct push)
- Force pushes and branch deletion disabled
- All changes must go through PR review
