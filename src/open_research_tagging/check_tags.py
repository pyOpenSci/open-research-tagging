"""Actions tag-check: library helpers + CLI (not a researcher tool).

Modes:
  --body TEXT       check one body (tests/debug)
  --from-event      read GITHUB_EVENT_PATH review comment; optional --reply
  --pr N            scan all review comments on a PR
  --soft            print issues but exit 0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from open_research_tagging.codebook import Codebook, load_codebook
from open_research_tagging.fetch_comments import FetchConfigError, resolve_owner_repo
from open_research_tagging.github_client import Getter, Poster, github_post, paginate
from open_research_tagging.tags import parse_and_enrich, tag_warnings

API = "https://api.github.com"
GUIDE_PATH = "codebook/COMMENTING.md"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CODEBOOK = REPO_ROOT / "codebook" / "codebook.yaml"


def check_body(body: str | None, codebook: Codebook) -> list[str]:
    """Return tag warnings for a comment body (empty list if clean)."""
    text = body or ""
    tags = parse_and_enrich(text, codebook)
    return tag_warnings(text, tags, codebook)


def format_reply(
    warnings: list[str],
    *,
    guide_repo: str | None = None,
) -> str:
    """Markdown reply body for a review comment with bad/unknown tags."""
    repo = (
        guide_repo
        or os.environ.get("GITHUB_REPOSITORY")
        or "owner/open-research-tagging"
    )
    guide_url = f"https://github.com/{repo}/blob/main/{GUIDE_PATH}"
    lines = [
        "⚠️ **Tag format check** — this review comment has hashtags that "
        "won't be picked up by the research site.",
        "",
    ]
    for warning in warnings:
        lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "Expected shape:",
            "```",
            "#disclosure/required",
            "#stance/permissive-with-conditions",
            "",
            "Optional free-text note…",
            "```",
            "",
            f"Guide: {guide_url}",
        ]
    )
    return "\n".join(lines)


def is_bot_login(login: str | None) -> bool:
    return bool(login) and str(login).endswith("[bot]")


def fetch_pr_review_comments(
    owner: str,
    repo: str,
    pr: int,
    token: str | None = None,
    *,
    getter: Getter | None = None,
) -> list[dict[str, Any]]:
    """List review comments on one pull request."""
    url = f"{API}/repos/{owner}/{repo}/pulls/{pr}/comments?per_page=100"
    items = paginate(url, token, getter=getter)
    return [item for item in items if isinstance(item, dict)]


def reply_to_review_comment(
    owner: str,
    repo: str,
    comment_id: int,
    body: str,
    token: str,
    *,
    poster: Poster | None = None,
) -> None:
    """POST a reply on a pull request review comment."""
    url = f"{API}/repos/{owner}/{repo}/pulls/comments/{comment_id}/replies"
    github_post(url, token, {"body": body}, poster=poster)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--body",
        help="Check a single comment body (tests/debug only)",
    )
    parser.add_argument("--owner", help="GitHub org or user")
    parser.add_argument("--repo", help="Repository name")
    parser.add_argument("--pr", type=int, help="PR number to scan")
    parser.add_argument(
        "--from-event",
        action="store_true",
        help="Read pull_request_review_comment payload from GITHUB_EVENT_PATH",
    )
    parser.add_argument(
        "--reply",
        action="store_true",
        help="Post a reply when --from-event finds tag issues",
    )
    parser.add_argument(
        "--soft",
        action="store_true",
        help="Print warnings but always exit 0",
    )
    parser.add_argument(
        "--codebook",
        type=Path,
        default=DEFAULT_CODEBOOK,
        help="Path to codebook.yaml",
    )
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    getter: Getter | None = None,
    poster: Poster | None = None,
) -> int:
    """Run tag-check; return process exit code (0 or 1)."""
    args = parse_args(argv)
    codebook = load_codebook(args.codebook)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    problems: list[tuple[str, list[str], dict[str, Any] | None]] = []

    if args.body is not None:
        warns = check_body(args.body, codebook)
        if warns:
            problems.append(("stdin", warns, None))
    elif args.from_event:
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            print("GITHUB_EVENT_PATH not set", file=sys.stderr)
            return 2
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        comment = event.get("comment") or {}
        if not isinstance(comment, dict):
            comment = {}
        body = comment.get("body") or ""
        warns = check_body(str(body), codebook)
        if warns:
            loc = str(comment.get("html_url") or "event-comment")
            problems.append((loc, warns, comment))
            if args.reply and token and comment.get("id"):
                user = (comment.get("user") or {}).get("login")
                if is_bot_login(user if isinstance(user, str) else None):
                    print("Skipping reply to bot comment")
                else:
                    try:
                        owner, repo = resolve_owner_repo(
                            owner=args.owner,
                            repo=args.repo,
                            env_repository=os.environ.get("GITHUB_REPOSITORY"),
                        )
                    except FetchConfigError as exc:
                        print(str(exc), file=sys.stderr)
                        return 2
                    reply_to_review_comment(
                        owner,
                        repo,
                        int(comment["id"]),
                        format_reply(warns),
                        token,
                        poster=poster,
                    )
                    print(f"Replied on review comment {comment['id']}")
    elif args.pr is not None:
        try:
            owner, repo = resolve_owner_repo(
                owner=args.owner,
                repo=args.repo,
                env_repository=os.environ.get("GITHUB_REPOSITORY"),
            )
        except FetchConfigError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        comments = fetch_pr_review_comments(
            owner, repo, args.pr, token, getter=getter
        )
        for comment in comments:
            user = (comment.get("user") or {}).get("login")
            if is_bot_login(user if isinstance(user, str) else None):
                continue
            warns = check_body(comment.get("body") or "", codebook)
            if warns:
                loc = str(comment.get("html_url") or comment.get("id"))
                problems.append((loc, warns, comment))
    else:
        print("Pass --body, --from-event, or --pr N", file=sys.stderr)
        return 2

    if not problems:
        print("OK — no malformed codebook tags found.")
        return 0

    print(f"Found {len(problems)} comment(s) with tag issues:\n")
    for loc, warns, _ in problems:
        print(f"• {loc}")
        for warning in warns:
            print(f"  - {warning}")
        print()

    if args.soft:
        print("(soft mode: exiting 0)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
