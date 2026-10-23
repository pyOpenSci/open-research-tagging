"""Maintainer / Actions entrypoint: fetch PR review comments → raw_comments.json.

Researchers do not use this CLI. Output is gitignored live dump; use the
committed fixture for offline regen.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from open_research_tagging.github_client import Getter, paginate

API = "https://api.github.com"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "site" / "data" / "raw_comments.json"


class FetchConfigError(ValueError):
    """Missing owner/repo for the fetch entrypoint."""


def resolve_owner_repo(
    *,
    owner: str | None,
    repo: str | None,
    env_repository: str | None,
) -> tuple[str, str]:
    """Resolve owner/repo from flags or GITHUB_REPOSITORY-style env value."""
    if owner and repo:
        return owner, repo
    env = env_repository or ""
    if "/" in env:
        left, right = env.split("/", 1)
        if left and right:
            return left, right
    raise FetchConfigError(
        "Pass --owner and --repo, or set GITHUB_REPOSITORY=owner/repo"
    )


def review_comments_url(owner: str, repo: str) -> str:
    return f"{API}/repos/{owner}/{repo}/pulls/comments?per_page=100"


def fetch_all_review_comments(
    owner: str,
    repo: str,
    token: str | None = None,
    *,
    getter: Getter | None = None,
) -> list[dict[str, Any]]:
    """Fetch every pull request review comment in the repo (all PRs)."""
    url = review_comments_url(owner, repo)
    items = paginate(url, token, getter=getter)
    return [item for item in items if isinstance(item, dict)]


def write_raw_comments(
    *,
    comments: list[dict[str, Any]],
    owner: str,
    repo: str,
    path: str | Path,
) -> dict[str, Any]:
    """Write the raw dump envelope and return the payload."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": f"{owner}/{repo}",
        "endpoint": f"{API}/repos/{owner}/{repo}/pulls/comments",
        "count": len(comments),
        "comments": comments,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", help="GitHub org or user")
    parser.add_argument("--repo", help="Repository name")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output path (default: site/data/raw_comments.json)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        owner, repo = resolve_owner_repo(
            owner=args.owner,
            repo=args.repo,
            env_repository=os.environ.get("GITHUB_REPOSITORY"),
        )
    except FetchConfigError as exc:
        raise SystemExit(str(exc)) from exc
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    comments = fetch_all_review_comments(owner, repo, token=token)
    write_raw_comments(
        comments=comments, owner=owner, repo=repo, path=args.out
    )
    print(f"Wrote {len(comments)} review comments → {args.out}")


if __name__ == "__main__":
    main()
