#!/usr/bin/env python3
"""Tests for D-152 PR issue-link gate validator.

Test matrix:
- valid linkage PASS
- missing issue FAIL
- missing closes FAIL
- wrong sprint FAIL
- wrong parent FAIL
- wrong branch FAIL
- exempt task PASS
- multiple task issues FAIL
"""
import sys
from pathlib import Path

# Add tools/ to path for import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import importlib  # noqa: E402

_mod = importlib.import_module("pr-issue-link-check")
is_exempt = _mod.is_exempt
parse_pr_body = _mod.parse_pr_body
validate_linkage = _mod.validate_linkage


class TestParseBody:
    """Test PR body field extraction."""

    def test_extracts_task_issue(self):
        body = "- Task-Issue: #451\n- Closes: #451"
        parsed = parse_pr_body(body)
        assert parsed["task_issues"] == [451]

    def test_extracts_parent_issue(self):
        body = "- Parent-Issue: #442\n- Task-Issue: #443\n- Closes: #443"
        parsed = parse_pr_body(body)
        assert parsed["parent_issues"] == [442]

    def test_extracts_sprint(self):
        body = "- Sprint: 85\n- Task-Issue: #1\n- Closes: #1"
        parsed = parse_pr_body(body)
        assert parsed["sprints"] == [85]

    def test_extracts_task_id(self):
        body = "- Task-ID: T-85.01\n- Task-Issue: #1\n- Closes: #1"
        parsed = parse_pr_body(body)
        assert parsed["task_ids"] == ["T-85.01"]

    def test_extracts_closes(self):
        body = "- Closes: #451"
        parsed = parse_pr_body(body)
        assert 451 in parsed["closes"]

    def test_extracts_native_closes(self):
        body = "Some text\nCloses #451\nMore text"
        parsed = parse_pr_body(body)
        assert 451 in parsed["closes"]

    def test_empty_body(self):
        parsed = parse_pr_body("")
        assert parsed["task_issues"] == []
        assert parsed["closes"] == []


class TestIsExempt:
    """Test exempt PR title detection."""

    def test_docs_exempt(self):
        assert is_exempt("docs: update handoff") is True

    def test_chore_exempt(self):
        assert is_exempt("chore: regenerate types") is True

    def test_ci_exempt(self):
        assert is_exempt("ci: fix workflow") is True

    def test_fix_exempt(self):
        assert is_exempt("fix: hotfix for production") is True

    def test_bootstrap_exempt(self):
        assert is_exempt("bootstrap: D-152 task packet") is True

    def test_merge_exempt(self):
        assert is_exempt("merge: resolve conflicts") is True

    def test_revert_exempt(self):
        assert is_exempt("revert: undo last commit") is True

    def test_feat_not_exempt(self):
        assert is_exempt("feat: new feature") is False

    def test_implementation_not_exempt(self):
        assert is_exempt("[D-152] Issue-First PR Link Gate (#451)") is False

    def test_case_insensitive(self):
        assert is_exempt("Docs: uppercase") is True
        assert is_exempt("CHORE: all caps") is True


class TestValidLinkage:
    """Test valid PR linkage passes."""

    def test_valid_linkage_passes(self):
        title = "[D-152] Issue-First PR Link Gate (#451)"
        body = (
            "- Task-Issue: #451\n"
            "- Parent-Issue: #450\n"
            "- Sprint: 85\n"
            "- Task-ID: T-85.01\n"
            "- Closes: #451\n"
        )
        errors = validate_linkage(title, body)
        assert errors == []

    def test_valid_with_native_closes(self):
        title = "[S85] Some feature"
        body = "- Task-Issue: #100\n\nCloses #100"
        errors = validate_linkage(title, body)
        assert errors == []


class TestMissingIssueFail:
    """Test missing task issue fails."""

    def test_no_task_issue(self):
        title = "[S85] Feature"
        body = "- Closes: #100"
        errors = validate_linkage(title, body)
        assert any("Missing Task-Issue" in e for e in errors)

    def test_empty_body(self):
        title = "feat: something"
        body = ""
        errors = validate_linkage(title, body)
        assert any("Missing Task-Issue" in e for e in errors)


class TestMissingClosesFail:
    """Test missing closes line fails."""

    def test_no_closes(self):
        title = "[S85] Feature"
        body = "- Task-Issue: #100"
        errors = validate_linkage(title, body)
        assert any("Missing Closes" in e for e in errors)


class TestWrongSprintFail:
    """Test wrong sprint fails."""

    def test_sprint_mismatch(self):
        title = "[S85] Feature"
        body = "- Task-Issue: #100\n- Sprint: 84\n- Closes: #100"
        errors = validate_linkage(title, body, expected_sprint=85)
        assert any("Sprint mismatch" in e for e in errors)

    def test_sprint_match_passes(self):
        title = "[S85] Feature"
        body = "- Task-Issue: #100\n- Sprint: 85\n- Closes: #100"
        errors = validate_linkage(title, body, expected_sprint=85)
        assert errors == []


class TestWrongParentFail:
    """Test wrong parent issue fails."""

    def test_parent_mismatch(self):
        title = "[S85] Feature"
        body = "- Task-Issue: #100\n- Parent-Issue: #50\n- Closes: #100"
        errors = validate_linkage(title, body, expected_parent=42)
        assert any("Parent-Issue mismatch" in e for e in errors)


class TestWrongBranchFail:
    """Test wrong branch fails."""

    def test_branch_mismatch(self):
        title = "[S85] Feature"
        body = "- Task-Issue: #100\n- Closes: #100"
        errors = validate_linkage(
            title, body,
            expected_branch="feat/s85-feature",
            actual_branch="wrong-branch",
        )
        assert any("Branch mismatch" in e for e in errors)

    def test_branch_match_passes(self):
        title = "[S85] Feature"
        body = "- Task-Issue: #100\n- Closes: #100"
        errors = validate_linkage(
            title, body,
            expected_branch="feat/s85-feature",
            actual_branch="feat/s85-feature",
        )
        assert errors == []


class TestExemptPass:
    """Test exempt PRs pass without linkage."""

    def test_docs_exempt_no_linkage(self):
        errors = validate_linkage("docs: update README", "no linkage here")
        assert errors == []

    def test_chore_exempt_empty_body(self):
        errors = validate_linkage("chore: cleanup", "")
        assert errors == []

    def test_bootstrap_exempt(self):
        errors = validate_linkage("bootstrap: D-152 task packet", "")
        assert errors == []


class TestMultipleTaskIssuesFail:
    """Test multiple task issues fails."""

    def test_two_task_issues(self):
        title = "[S85] Feature"
        body = "- Task-Issue: #100\n- Task-Issue: #101\n- Closes: #100"
        errors = validate_linkage(title, body)
        assert any("Multiple Task-Issue" in e for e in errors)


class TestClosesMatchesTaskIssue:
    """Test that Closes must reference the task issue."""

    def test_closes_different_from_task_issue(self):
        title = "[S85] Feature"
        body = "- Task-Issue: #100\n- Closes: #200"
        errors = validate_linkage(title, body)
        assert any("not in Closes" in e for e in errors)
