"""Load projects/*/project.yaml from open PRs into site rows (13a).

Comments already refresh from every PR; project rows historically only came
from projects/ on the checked-out branch (usually main). This module discovers
open PRs that touch project.yaml, fetches those files at the PR head, and
merges rows so new slugs appear on the site before merge.
"""

from __future__ import annotations

import base64
import re
from typing import Any, Callable, Mapping

import yaml

from open_research_tagging.github_client import Getter, GitHubHTTPError, github_get, paginate

API = "https://api.github.com"
PROJECT_YAML_RE = re.compile(r"^projects/([^/]+)/project\.yaml$")

WarnFn = Callable[[str], None]


def project_yaml_spec_from_path(path: str) -> dict[str, str] | None:
    """Return {slug, path} for projects/<slug>/project.yaml, else None."""
    match = PROJECT_YAML_RE.match(path.replace("\\", "/"))
    if not match:
        return None
    slug = match.group(1)
    if slug.startswith("_"):
        return None
    return {"slug": slug, "path": match.group(0)}


def discover_open_pr_project_yamls(
    owner: str,
    repo: str,
    token: str | None = None,
    *,
    getter: Getter | None = None,
    warn: WarnFn | None = None,
) -> list[dict[str, Any]]:
    """
    List open-PR project.yaml paths (slug, path, pr_number, head_sha).

    On API failure, warn and return [] so refresh can continue with main only.
    """
    note = warn or (lambda _msg: None)
    pulls_url = f"{API}/repos/{owner}/{repo}/pulls?state=open&per_page=100"
    try:
        pulls = paginate(pulls_url, token, getter=getter)
    except GitHubHTTPError as exc:
        note(f"Warning: open-PR project discovery failed ({exc}); skipping")
        return []

    found: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()
    for pull in pulls:
        if not isinstance(pull, Mapping):
            continue
        number = pull.get("number")
        head = pull.get("head") if isinstance(pull.get("head"), Mapping) else {}
        sha = head.get("sha") if isinstance(head, Mapping) else None
        if not isinstance(number, int) or not sha:
            continue
        files_url = (
            f"{API}/repos/{owner}/{repo}/pulls/{number}/files?per_page=100"
        )
        try:
            files = paginate(files_url, token, getter=getter)
        except GitHubHTTPError as exc:
            note(
                f"Warning: could not list files for PR #{number} ({exc}); "
                "skipping that PR"
            )
            continue
        for file_row in files:
            if not isinstance(file_row, Mapping):
                continue
            filename = file_row.get("filename")
            if not isinstance(filename, str):
                continue
            spec = project_yaml_spec_from_path(filename)
            if spec is None:
                continue
            slug = spec["slug"]
            if slug in seen_slugs:
                note(
                    f"Warning: open PR #{number} also has projects/{slug}/"
                    "project.yaml; keeping the first open PR for that slug"
                )
                continue
            seen_slugs.add(slug)
            found.append(
                {
                    "slug": slug,
                    "path": spec["path"],
                    "pr_number": number,
                    "head_sha": str(sha),
                }
            )
    return found


def _decode_contents_payload(payload: Mapping[str, Any]) -> str:
    """Decode a GitHub Contents API file payload to text."""
    encoding = str(payload.get("encoding") or "")
    content = payload.get("content")
    if not isinstance(content, str):
        raise ValueError("Contents payload missing content string")
    if encoding == "base64":
        return base64.b64decode(content).decode("utf-8")
    return content


def fetch_open_pr_project_docs(
    owner: str,
    repo: str,
    specs: list[Mapping[str, Any]],
    token: str | None = None,
    *,
    getter: Getter | None = None,
    warn: WarnFn | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch and parse project.yaml for each discovery spec.

    Returns list of {data, path, pr_number, slug}. Skips failures with a warning.
    """
    note = warn or (lambda _msg: None)
    docs: list[dict[str, Any]] = []
    for spec in specs:
        path = str(spec["path"])
        sha = str(spec["head_sha"])
        pr_number = int(spec["pr_number"])
        url = f"{API}/repos/{owner}/{repo}/contents/{path}?ref={sha}"
        try:
            body, _headers = github_get(url, token, getter=getter)
        except GitHubHTTPError as exc:
            note(
                f"Warning: could not fetch {path} from PR #{pr_number} "
                f"({exc}); skipping"
            )
            continue
        if not isinstance(body, Mapping):
            note(f"Warning: unexpected contents payload for {path}; skipping")
            continue
        try:
            text = _decode_contents_payload(body)
            data = yaml.safe_load(text)
        except (ValueError, yaml.YAMLError) as exc:
            note(f"Warning: invalid project.yaml at {path} ({exc}); skipping")
            continue
        if not isinstance(data, dict):
            note(f"Warning: {path} is not a YAML mapping; skipping")
            continue
        docs.append(
            {
                "data": data,
                "path": path,
                "pr_number": pr_number,
                "slug": str(spec.get("slug") or data.get("slug") or ""),
            }
        )
    return docs


def merge_project_rows(
    main_rows: list[Mapping[str, Any]],
    pr_rows: list[Mapping[str, Any]],
    *,
    warn: WarnFn | None = None,
) -> list[dict[str, Any]]:
    """
    Combine main and open-PR rows; main wins on slug conflict.

    Among open-PR rows, the first slug wins (discovery already prefers first).
    Result sorted by slug.
    """
    note = warn or (lambda _msg: None)
    by_slug: dict[str, dict[str, Any]] = {}
    for row in pr_rows:
        slug = str(row.get("slug") or "")
        if not slug:
            continue
        if slug in by_slug:
            note(
                f"Warning: duplicate open-PR project slug '{slug}'; "
                "keeping the first"
            )
            continue
        by_slug[slug] = dict(row)
    for row in main_rows:
        slug = str(row.get("slug") or "")
        if not slug:
            continue
        by_slug[slug] = dict(row)
    return [by_slug[k] for k in sorted(by_slug)]
