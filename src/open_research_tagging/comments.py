"""Normalize GitHub PR review comments into comments.json rows."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from open_research_tagging.codebook import Codebook
from open_research_tagging.quotes import resolve_quote
from open_research_tagging.tags import codes_by_dimension, parse_and_enrich, tag_warnings

# open_research_tagging/comments.py → src/ → repo root
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


class ProcessedCommentsError(ValueError):
    """Input looks like processed comments.json, not raw review comments."""


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


def normalize(
    comment: Mapping[str, Any],
    codebook: Codebook,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Turn one raw GitHub review-comment object into a comments.json row."""
    root = repo_root if repo_root is not None else _DEFAULT_REPO_ROOT
    body = comment.get("body") or ""
    body_str = body if isinstance(body, str) else str(body)
    tags = parse_and_enrich(body_str, codebook)
    warnings = tag_warnings(body_str, tags, codebook)
    quoted = resolve_quote(comment, repo_root=root)
    refs = comment_refs(comment)
    return {
        "id": comment.get("id"),
        "body": body_str,
        "quote": quoted["quote"],
        "quote_source": quoted["quote_source"],
        "diff_hunk": quoted["diff_hunk"],
        "tags": tags,
        "tag_strings": [t["raw"] for t in tags],
        "displays": [t["display"] for t in tags],
        "filter_keys": [t["filter_key"] for t in tags],
        "parse_warnings": warnings,
        "needs_tag_review": bool(warnings),
        "codes": codes_by_dimension(tags),
        "path": refs["path"],
        "project": refs["project"],
        "start_line": quoted["start_line"],
        "line": quoted["line"],
        "side": comment.get("side"),
        "user": refs["user"],
        "pr_number": refs["pr_number"],
        "html_url": refs["html_url"],
        "commit_id": comment.get("commit_id"),
        "created_at": comment.get("created_at"),
        "updated_at": comment.get("updated_at"),
    }


def load_raw_comments(path: str | Path) -> list[dict[str, Any]]:
    """Load a raw review-comment dump (list or {comments: [...]})."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "data" in data and "meta" in data:
        raise ProcessedCommentsError(
            f"{path} looks processed already; pass raw_comments.json"
        )
    if isinstance(data, dict) and "comments" in data:
        comments = data["comments"]
        if not isinstance(comments, list):
            raise ValueError(f"{path}: 'comments' must be a list")
        return comments
    if isinstance(data, list):
        return data
    raise ValueError(f"Unrecognized JSON shape in {path}")


def build_comments_payload(
    rows: list[Mapping[str, Any]],
    *,
    source_file: str | Path,
    codebook: Codebook,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Build the {meta, data} envelope for comments.json."""
    root = repo_root if repo_root is not None else _DEFAULT_REPO_ROOT
    source = Path(source_file)
    try:
        relative = str(source.resolve().relative_to(root.resolve()))
    except ValueError:
        relative = str(source)
    return {
        "meta": {
            "source_file": relative,
            "count": len(rows),
            "is_fixture": "fixture" in source.name,
            "codebook_version": codebook.version,
        },
        "data": list(rows),
    }


def write_comments_json(payload: Mapping[str, Any], path: str | Path) -> None:
    """Write comments.json with trailing newline."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
