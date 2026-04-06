# Sprint 70 Test Evidence

**Date:** 2026-04-06
**Sprint:** 70 — Validator/Closer Drift Hardening

## Test Results

### Root-level tests (tests/)
- 60 passed, 0 failed (was 41 before S70 → +19 new)
- `test_project_validator.py`: 31 tests (25 existing + 6 new derive_closed_sprints)
- `test_close_merged_issues.py`: 15 tests (new file)
- `test_state_sync.py`: 10 tests (unchanged)

### Backend tests (agent/tests/)
- 1551 passed, 4 skipped, 0 failed
- 4 skipped: pre-existing WinError 50 quarantine (test_audit_integrity)

### New tests added
1. `TestDeriveClosedSprints::test_parses_sprint_milestones`
2. `TestDeriveClosedSprints::test_ignores_non_sprint_milestones`
3. `TestDeriveClosedSprints::test_empty_milestones`
4. `TestDeriveClosedSprints::test_api_failure_returns_empty`
5. `TestDeriveClosedSprints::test_pagination`
6. `TestDeriveClosedSprints::test_case_insensitive_match`
7. `TestClosedSprintOpenIssue::test_no_closed_sprints_skips_check`
8. `TestClosedSprintOpenIssue::test_empty_closed_sprints_skips_check`
9. `TestIsBranchMerged::test_branch_exists_with_merged_pr`
10. `TestIsBranchMerged::test_branch_exists_no_merged_pr`
11. `TestIsBranchMerged::test_branch_deleted_with_merged_pr`
12. `TestIsBranchMerged::test_branch_deleted_no_merged_pr`
13. `TestIsBranchMerged::test_branch_deleted_api_failure`
14. `TestHasMergedPr::test_issue_has_merged_pr_via_search`
15. `TestHasMergedPr::test_issue_has_merged_pr_via_timeline`
16. `TestHasMergedPr::test_issue_no_merged_pr`
17. `TestHasMergedPr::test_both_api_calls_fail`
18. `TestMainDryRun::test_skips_unmerged_branch`
19. `TestMainDryRun::test_closes_merged_branch_dryrun`
20. `TestMainDryRun::test_no_branch_falls_back_to_pr_check` (was already counted — correcting)
21. `TestMainDryRun::test_parent_not_closed_when_tasks_unmerged`

Total new: 19 tests
