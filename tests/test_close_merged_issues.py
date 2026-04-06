"""Tests for close-merged-issues.py — merge evidence gate (T70.4).

Covers:
- is_branch_merged: branch merged via PR, branch not merged, deleted branch
- has_merged_pr: issue with merged PR, issue without
- main() dry-run mode: skips unmerged tasks, closes merged tasks
"""

import importlib.util
import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

REPO_ROOT = Path(__file__).parent.parent

# Import hyphenated script module via importlib
_spec = importlib.util.spec_from_file_location(
    "close_merged_issues",
    REPO_ROOT / "tools" / "close-merged-issues.py",
)
closer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(closer)

is_branch_merged = closer.is_branch_merged
has_merged_pr = closer.has_merged_pr


def mock_gh(*responses):
    """Create a side_effect function that returns (stdout, rc) pairs in order."""
    call_idx = [0]

    def side_effect(*args):
        if call_idx[0] < len(responses):
            result = responses[call_idx[0]]
            call_idx[0] += 1
            return result
        return ("", 1)

    return side_effect


# --- is_branch_merged ---

class TestIsBranchMerged:
    @patch.object(closer, "gh")
    def test_branch_exists_with_merged_pr(self, mock):
        # Branch exists (rc=0), merged PR count = 1
        mock.side_effect = mock_gh(
            ("sprint-70/t70.1", 0),  # branch lookup
            ("1", 0),                 # merged PR count
        )
        assert is_branch_merged("sprint-70/t70.1") is True

    @patch.object(closer, "gh")
    def test_branch_exists_no_merged_pr(self, mock):
        mock.side_effect = mock_gh(
            ("sprint-70/t70.1", 0),  # branch exists
            ("0", 0),                 # no merged PRs
        )
        assert is_branch_merged("sprint-70/t70.1") is False

    @patch.object(closer, "gh")
    def test_branch_deleted_with_merged_pr(self, mock):
        # Branch doesn't exist (rc=1), but merged PR found
        mock.side_effect = mock_gh(
            ("", 1),    # branch not found
            ("1", 0),   # merged PR count
        )
        assert is_branch_merged("sprint-70/t70.1") is True

    @patch.object(closer, "gh")
    def test_branch_deleted_no_merged_pr(self, mock):
        mock.side_effect = mock_gh(
            ("", 1),    # branch not found
            ("0", 0),   # no merged PR
        )
        assert is_branch_merged("sprint-70/t70.1") is False

    @patch.object(closer, "gh")
    def test_branch_deleted_api_failure(self, mock):
        mock.side_effect = mock_gh(
            ("", 1),    # branch not found
            ("", 1),    # API failure
        )
        assert is_branch_merged("sprint-70/t70.1") is False


# --- has_merged_pr ---

class TestHasMergedPr:
    @patch.object(closer, "gh")
    def test_issue_has_merged_pr_via_search(self, mock):
        mock.side_effect = mock_gh(
            ("1", 0),  # pr list search found 1
        )
        assert has_merged_pr(347) is True

    @patch.object(closer, "gh")
    def test_issue_has_merged_pr_via_timeline(self, mock):
        mock.side_effect = mock_gh(
            ("0", 0),  # pr list search found 0
            ("1", 0),  # timeline cross-ref found 1
        )
        assert has_merged_pr(347) is True

    @patch.object(closer, "gh")
    def test_issue_no_merged_pr(self, mock):
        mock.side_effect = mock_gh(
            ("0", 0),  # pr list search = 0
            ("0", 0),  # timeline = 0
        )
        assert has_merged_pr(347) is False

    @patch.object(closer, "gh")
    def test_both_api_calls_fail(self, mock):
        mock.side_effect = mock_gh(
            ("", 1),   # search fails
            ("", 1),   # timeline fails
        )
        assert has_merged_pr(347) is False


# --- main() integration-level tests ---

class TestMainDryRun:
    """Test main() with mocked gh() and --dry-run."""

    def _make_issues_json(self, tmp_path, tasks, parent_issue=None):
        sprint_dir = tmp_path / "sprint-70"
        sprint_dir.mkdir()
        data = {
            "sprint": 70,
            "tasks": tasks,
        }
        if parent_issue is not None:
            data["parent_issue"] = parent_issue
        (sprint_dir / "issues.json").write_text(json.dumps(data))
        return str(sprint_dir)

    @patch.object(closer, "gh")
    @patch.object(closer, "is_branch_merged")
    @patch.object(closer, "has_merged_pr")
    def test_skips_unmerged_branch(self, mock_has_pr, mock_is_merged, mock_gh, tmp_path):
        mock_is_merged.return_value = False
        sprint_dir = self._make_issues_json(tmp_path, {
            "70.1": {"issue": 348, "branch": "sprint-70/t70.1"},
        })
        with patch.object(sys, "argv", ["close-merged-issues.py", sprint_dir, "--dry-run"]):
            with pytest.raises(SystemExit) as exc_info:
                closer.main()
            assert exc_info.value.code == 1  # exit 1 due to no_merge_evidence

    @patch.object(closer, "gh")
    @patch.object(closer, "is_branch_merged")
    def test_closes_merged_branch_dryrun(self, mock_is_merged, mock_gh, tmp_path):
        mock_is_merged.return_value = True
        mock_gh.side_effect = mock_gh_for_issue_view("OPEN")
        sprint_dir = self._make_issues_json(tmp_path, {
            "70.1": {"issue": 348, "branch": "sprint-70/t70.1"},
        })
        with patch.object(sys, "argv", ["close-merged-issues.py", sprint_dir, "--dry-run"]):
            closer.main()  # should not raise (no unmerged tasks)

    @patch.object(closer, "gh")
    @patch.object(closer, "has_merged_pr")
    def test_no_branch_falls_back_to_pr_check(self, mock_has_pr, mock_gh, tmp_path):
        mock_has_pr.return_value = False
        sprint_dir = self._make_issues_json(tmp_path, {
            "70.1": {"issue": 348},  # no branch key
        })
        with patch.object(sys, "argv", ["close-merged-issues.py", sprint_dir, "--dry-run"]):
            with pytest.raises(SystemExit) as exc_info:
                closer.main()
            assert exc_info.value.code == 1
        mock_has_pr.assert_called_once_with(348)

    @patch.object(closer, "gh")
    @patch.object(closer, "is_branch_merged")
    def test_parent_not_closed_when_tasks_unmerged(self, mock_is_merged, mock_gh, tmp_path, capsys):
        mock_is_merged.return_value = False
        sprint_dir = self._make_issues_json(tmp_path, {
            "70.1": {"issue": 348, "branch": "sprint-70/t70.1"},
        }, parent_issue=347)
        with patch.object(sys, "argv", ["close-merged-issues.py", sprint_dir, "--dry-run"]):
            with pytest.raises(SystemExit):
                closer.main()
        captured = capsys.readouterr()
        assert "NOT CLOSED" in captured.out
        assert "lack merge evidence" in captured.out


def mock_gh_for_issue_view(state):
    """Return a side_effect for gh() that handles issue view calls."""
    def side_effect(*args):
        if "issue" in args and "view" in args:
            return (state, 0)
        return ("", 0)
    return side_effect
