"""GitHub project communication service — D-151.

Outbound-only GitHub integration for the project aggregate. Pulls issue/PR
thread activity and publishes top-level comments. GitHub is an external
communication surface, never an execution owner.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GitHubProjectServiceError(RuntimeError):
    """Raised when GitHub communication fails."""


class GitHubProjectService:
    """Minimal GitHub REST client for project-bound sync/comment flows."""

    def __init__(
        self,
        token_env: str = "VEZIR_GITHUB_TOKEN",
        api_root: str = "https://api.github.com",
        user_agent: str = "VezirProjectGitHub/1.0",
    ):
        self._token_env = token_env
        self._api_root = api_root.rstrip("/")
        self._user_agent = user_agent

    def _token(self) -> str:
        token = os.getenv(self._token_env, "").strip()
        if not token:
            raise GitHubProjectServiceError(
                f"Missing GitHub token env: {self._token_env}"
            )
        return token

    def _request(self, method: str, path: str, body: dict | None = None) -> dict | list:
        url = f"{self._api_root}{path}"
        payload = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(url, data=payload, method=method.upper())
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Authorization", f"Bearer {self._token()}")
        req.add_header("User-Agent", self._user_agent)
        if payload is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise GitHubProjectServiceError(
                f"GitHub {method.upper()} {path} failed: {e.code} {detail[:300]}"
            ) from e
        except URLError as e:
            raise GitHubProjectServiceError(
                f"GitHub {method.upper()} {path} failed: {e}"
            ) from e

    @staticmethod
    def _normalize_repo(repo_full_name: str) -> str:
        repo = repo_full_name.strip().strip("/")
        if repo.count("/") != 1:
            raise GitHubProjectServiceError(
                f"Invalid repo_full_name: {repo_full_name}"
            )
        return repo

    def fetch_issue(self, repo_full_name: str, issue_number: int) -> dict:
        repo = self._normalize_repo(repo_full_name)
        return self._request("GET", f"/repos/{repo}/issues/{issue_number}")

    def fetch_issue_comments(self, repo_full_name: str, issue_number: int) -> list[dict]:
        repo = self._normalize_repo(repo_full_name)
        data = self._request(
            "GET",
            f"/repos/{repo}/issues/{issue_number}/comments?per_page=100",
        )
        return data if isinstance(data, list) else []

    def fetch_pull_request(self, repo_full_name: str, pr_number: int) -> dict:
        repo = self._normalize_repo(repo_full_name)
        return self._request("GET", f"/repos/{repo}/pulls/{pr_number}")

    def fetch_pull_request_review_comments(
        self, repo_full_name: str, pr_number: int
    ) -> list[dict]:
        repo = self._normalize_repo(repo_full_name)
        data = self._request(
            "GET",
            f"/repos/{repo}/pulls/{pr_number}/comments?per_page=100",
        )
        return data if isinstance(data, list) else []

    def post_issue_comment(
        self,
        repo_full_name: str,
        issue_number: int,
        body: str,
    ) -> dict:
        repo = self._normalize_repo(repo_full_name)
        text = body.strip()
        if not text:
            raise GitHubProjectServiceError("GitHub comment body is empty")
        return self._request(
            "POST",
            f"/repos/{repo}/issues/{issue_number}/comments",
            {"body": text},
        )

    def sync_binding(self, binding: dict) -> dict:
        """Pull bound thread metadata + comments into normalized activity entries."""
        repo = self._normalize_repo(binding["repo_full_name"])
        issue_number = binding.get("issue_number")
        pr_number = binding.get("pr_number")

        if issue_number is None and pr_number is None:
            raise GitHubProjectServiceError(
                "Binding is missing both issue_number and pr_number"
            )

        thread_number = issue_number or pr_number
        issue = self.fetch_issue(repo, int(thread_number))
        issue_comments = self.fetch_issue_comments(repo, int(thread_number))

        activity: list[dict] = [
            {
                "activity_id": f"issue:{issue['number']}",
                "kind": "pull_request" if "pull_request" in issue else "issue",
                "direction": "inbound",
                "repo_full_name": repo,
                "thread_number": issue["number"],
                "author": (issue.get("user") or {}).get("login"),
                "title": issue.get("title"),
                "body": issue.get("body") or "",
                "state": issue.get("state"),
                "created_at": issue.get("created_at"),
                "updated_at": issue.get("updated_at"),
                "html_url": issue.get("html_url"),
            }
        ]

        for comment in issue_comments:
            activity.append(
                {
                    "activity_id": f"issue_comment:{comment['id']}",
                    "kind": "issue_comment",
                    "direction": "inbound",
                    "repo_full_name": repo,
                    "thread_number": issue["number"],
                    "author": (comment.get("user") or {}).get("login"),
                    "body": comment.get("body") or "",
                    "created_at": comment.get("created_at"),
                    "updated_at": comment.get("updated_at"),
                    "html_url": comment.get("html_url"),
                    "comment_id": comment.get("id"),
                }
            )

        if pr_number is not None:
            pr = self.fetch_pull_request(repo, int(pr_number))
            activity.append(
                {
                    "activity_id": f"pr:{pr['number']}",
                    "kind": "pull_request_meta",
                    "direction": "inbound",
                    "repo_full_name": repo,
                    "thread_number": pr["number"],
                    "author": (pr.get("user") or {}).get("login"),
                    "title": pr.get("title"),
                    "body": pr.get("body") or "",
                    "state": pr.get("state"),
                    "created_at": pr.get("created_at"),
                    "updated_at": pr.get("updated_at"),
                    "html_url": pr.get("html_url"),
                    "mergeable_state": pr.get("mergeable_state"),
                }
            )
            for comment in self.fetch_pull_request_review_comments(repo, int(pr_number)):
                activity.append(
                    {
                        "activity_id": f"pr_review_comment:{comment['id']}",
                        "kind": "pr_review_comment",
                        "direction": "inbound",
                        "repo_full_name": repo,
                        "thread_number": pr["number"],
                        "author": (comment.get("user") or {}).get("login"),
                        "body": comment.get("body") or "",
                        "path": comment.get("path"),
                        "line": comment.get("line"),
                        "created_at": comment.get("created_at"),
                        "updated_at": comment.get("updated_at"),
                        "html_url": comment.get("html_url"),
                        "comment_id": comment.get("id"),
                    }
                )

        activity.sort(key=lambda item: item.get("created_at") or "")
        return {
            "repo_full_name": repo,
            "issue_number": issue_number,
            "pr_number": pr_number,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "activity": activity,
        }
