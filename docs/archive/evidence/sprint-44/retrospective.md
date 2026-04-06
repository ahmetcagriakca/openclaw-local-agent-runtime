# Sprint 44 Retrospective — CI/CD & Repo Quality

## What Went Well
- All 3 CI pipelines fixed from red to green in single session
- 22 CodeQL security findings resolved systematically
- Dependabot auto-configured, immediately produced PRs
- Coverage reporting now in CI with artifact upload

## What Didn't Go Well
- Python 3.14 was never released — should have caught earlier
- localStorage→sessionStorage change broke 4 test files (ripple effect)
- Coverage thresholds set too high initially (50%), had to lower to 25%
- Custom CodeQL workflow conflicted with GitHub default setup
- Coverage artifacts accidentally committed to git

## Lessons Learned
- **Pin Python to released versions** — 3.14 was speculative
- **Audit all test mocks when changing storage APIs** — grep for localStorage across all tests
- **Set coverage thresholds at current level** — then ratchet up incrementally
- **Don't create custom CodeQL workflow when default setup is active**
- **Add generated dirs to .gitignore immediately** when adding coverage tools

## Metrics
| Metric | Before | After |
|--------|--------|-------|
| CI status | All failing | All green |
| Code scanning | 22 open | 0 open |
| Dependabot alerts | 2 open | 0 open |
| Coverage config | None | vitest + pytest-cov |
| PR template | None | Created |
| README badges | Stale/broken | Current + coverage |
