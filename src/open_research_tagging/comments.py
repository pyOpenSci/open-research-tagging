"""Helpers for normalizing GitHub PR review comments (refs first; quotes later)."""

from __future__ import annotations

import re
from typing import Any, Mapping


def project_from_path(path: str | None) -> str | None:
    """Return projects/<slug>/… slug, or None for _template / non-project paths."""
    if not path:
        return None
    parts = path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "projects" and parts[1] != "_template":
        return parts[1]
    return None


def pr_number_from_comment(comment: Mapping[str, Any]) -> int | None:
    """PR number from pull_request_url, else from html_url /pull/N."""
    pr_url = comment.get("pull_request_url") or ""
    tail = pr_url.rstrip("/").split("/")[-1]
    if tail.isdigit():
        return int(tail)
    html = comment.get("html_url") or ""
    match = re.search(r"/pull/(\d+)", html)
    return int(match.group(1)) if match else None


def user_login_from_comment(comment: Mapping[str, Any]) -> str | None:
    user = comment.get("user")
    if not isinstance(user, Mapping):
        return None
    login = user.get("login")
    return str(login) if isinstance(login, str) and login else None


def comment_refs(comment: Mapping[str, Any]) -> dict[str, Any]:
    """Path, project slug, user, PR number, and html_url from a raw comment."""
    path = comment.get("path")
    path_str = str(path) if isinstance(path, str) else None
    html_url = comment.get("html_url")
    return {
        "path": path_str,
        "project": project_from_path(path_str),
        "user": user_login_from_comment(comment),
        "pr_number": pr_number_from_comment(comment),
        "html_url": str(html_url) if isinstance(html_url, str) else None,
    }
