"""Maintainer / Actions entrypoint: raw review comments → site/data/comments.json.

Researchers do not use this CLI; they tag on GitHub and browse the static site.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from open_research_tagging.codebook import load_codebook
from open_research_tagging.comments import (
    build_comments_payload,
    load_raw_comments,
    normalize,
    write_comments_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = REPO_ROOT / "site" / "data" / "raw_comments.json"
DEFAULT_OUT = REPO_ROOT / "site" / "data" / "comments.json"
DEFAULT_CODEBOOK = REPO_ROOT / "codebook" / "codebook.yaml"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in",
        dest="infile",
        type=Path,
        default=DEFAULT_IN,
        help="Raw review comments JSON (list or {comments: [...]})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output path for processed comments.json",
    )
    parser.add_argument(
        "--codebook",
        type=Path,
        default=DEFAULT_CODEBOOK,
        help="Path to codebook.yaml",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repo root for resolving local policy file quotes",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not args.infile.exists():
        raise SystemExit(f"Missing input: {args.infile}")
    codebook = load_codebook(args.codebook)
    raw = load_raw_comments(args.infile)
    rows = [
        normalize(comment, codebook, repo_root=args.repo_root) for comment in raw
    ]
    payload = build_comments_payload(
        rows,
        source_file=args.infile,
        codebook=codebook,
        repo_root=args.repo_root,
    )
    write_comments_json(payload, args.out)
    print(f"Wrote {len(rows)} comments → {args.out}")


if __name__ == "__main__":
    main()
