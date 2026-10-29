"""Maintainer / Actions entrypoint: project.yaml + comments.json → projects.json.

Researchers do not use this CLI; they code on GitHub and browse the static site.
With --include-open-prs, also fold in projects/*/project.yaml from open PRs so
new slugs appear on the site before merge (13a).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from open_research_tagging.codebook import load_codebook
from open_research_tagging.fetch_comments import FetchConfigError, resolve_owner_repo
from open_research_tagging.open_pr_projects import (
    discover_open_pr_project_yamls,
    fetch_open_pr_project_docs,
    merge_project_rows,
)
from open_research_tagging.projects import (
    build_project_from_data,
    build_projects_payload,
    collect_project_rows,
    comment_index,
    write_projects_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMMENTS = REPO_ROOT / "site" / "data" / "comments.json"
DEFAULT_OUT = REPO_ROOT / "site" / "data" / "projects.json"
DEFAULT_CODEBOOK = REPO_ROOT / "codebook" / "codebook.yaml"
DEFAULT_PROJECTS = REPO_ROOT / "projects"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comments",
        type=Path,
        default=DEFAULT_COMMENTS,
        help="Processed comments.json ({meta, data})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output path for projects.json",
    )
    parser.add_argument(
        "--codebook",
        type=Path,
        default=DEFAULT_CODEBOOK,
        help="Path to codebook.yaml",
    )
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=DEFAULT_PROJECTS,
        help="Directory containing projects/<slug>/project.yaml",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repo root for relative paths in output",
    )
    parser.add_argument(
        "--include-open-prs",
        action="store_true",
        help=(
            "Also load projects/*/project.yaml from open PRs (needs "
            "GITHUB_TOKEN + owner/repo)"
        ),
    )
    parser.add_argument("--owner", help="GitHub org or user (open-PR mode)")
    parser.add_argument("--repo", help="Repository name (open-PR mode)")
    return parser.parse_args(argv)


def load_comments_data(path: Path) -> list[dict]:
    """Load processed comments.json data list; empty if file missing."""
    if not path.exists():
        print(f"Warning: no comments file at {path}; comment counts will be 0")
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        data = payload.get("data") or []
        if isinstance(data, list):
            return data
    raise SystemExit(f"Unrecognized comments JSON shape in {path}")


def collect_open_pr_rows(
    *,
    owner: str,
    repo: str,
    codebook,
    comments: list[dict],
    token: str | None,
) -> list[dict]:
    """Discover/fetch open-PR project.yaml files and build site rows."""
    cidx = comment_index(comments)
    specs = discover_open_pr_project_yamls(
        owner, repo, token=token, warn=print
    )
    docs = fetch_open_pr_project_docs(
        owner, repo, specs, token=token, warn=print
    )
    rows: list[dict] = []
    for doc in docs:
        row = build_project_from_data(
            doc["data"],
            codebook=codebook,
            cidx=cidx,
            yaml_path=str(doc["path"]),
            slug_fallback=str(doc.get("slug") or ""),
            from_open_pr=True,
            pr_number=int(doc["pr_number"]),
        )
        if row is not None:
            rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    codebook = load_codebook(args.codebook)
    comments = load_comments_data(args.comments)
    rows = collect_project_rows(
        projects_dir=args.projects_dir,
        codebook=codebook,
        comments=comments,
        repo_root=args.repo_root,
    )
    if args.include_open_prs:
        try:
            owner, repo = resolve_owner_repo(
                owner=args.owner,
                repo=args.repo,
                env_repository=os.environ.get("GITHUB_REPOSITORY"),
            )
        except FetchConfigError as exc:
            raise SystemExit(str(exc)) from exc
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        pr_rows = collect_open_pr_rows(
            owner=owner,
            repo=repo,
            codebook=codebook,
            comments=comments,
            token=token,
        )
        rows = merge_project_rows(rows, pr_rows, warn=print)
        print(f"Included {len(pr_rows)} open-PR project row(s)")
    payload = build_projects_payload(
        rows,
        comments_source=args.comments,
        codebook=codebook,
        repo_root=args.repo_root,
    )
    write_projects_json(payload, args.out)
    print(f"Wrote {len(rows)} projects → {args.out}")


if __name__ == "__main__":
    main()
