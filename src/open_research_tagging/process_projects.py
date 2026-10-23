"""Maintainer / Actions entrypoint: project.yaml + comments.json → projects.json.

Researchers do not use this CLI; they code on GitHub and browse the static site.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from open_research_tagging.codebook import load_codebook
from open_research_tagging.projects import (
    build_projects_payload,
    collect_project_rows,
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
