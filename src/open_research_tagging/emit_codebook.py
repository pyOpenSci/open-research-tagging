"""Maintainer / Actions entrypoint: codebook.yaml → site/data/codebook.json.

Researchers do not use this CLI; the browser loads the emitted JSON.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from open_research_tagging.codebook import load_codebook_file
from open_research_tagging.codebook_emit import write_codebook_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CODEBOOK = REPO_ROOT / "codebook" / "codebook.yaml"
DEFAULT_OUT = REPO_ROOT / "site" / "data" / "codebook.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codebook",
        type=Path,
        default=DEFAULT_CODEBOOK,
        help="Path to codebook.yaml",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output path for codebook.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not args.codebook.exists():
        raise SystemExit(f"Missing codebook: {args.codebook}")
    data = load_codebook_file(args.codebook)
    write_codebook_json(args.out, data)
    print(f"Wrote codebook.json → {args.out}")


if __name__ == "__main__":
    main()
