"""Build readable source quotes for PR review comments."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

# open_research_tagging/quotes.py → src/ → repo root
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


def line_range(comment: Mapping[str, Any]) -> tuple[int | None, int | None]:
    """Return (start_line, end_line) 1-based inclusive, if known."""
    end = comment.get("line") or comment.get("original_line")
    start = comment.get("start_line") or comment.get("original_start_line") or end
    try:
        end_i = int(end) if end is not None else None
        start_i = int(start) if start is not None else None
    except (TypeError, ValueError):
        return None, None
    if start_i is not None and end_i is not None and start_i > end_i:
        start_i, end_i = end_i, start_i
    return start_i, end_i


def quote_from_diff_hunk(diff_hunk: str | None) -> str | None:
    """Clean GitHub diff_hunk text for display (skip headers and pure deletions)."""
    if not diff_hunk:
        return None
    lines: list[str] = []
    for raw in diff_hunk.splitlines():
        if raw.startswith("@@"):
            continue
        if raw.startswith(("+", "-", " ")):
            if raw.startswith("-"):
                continue
            lines.append(raw[1:])
        else:
            lines.append(raw)
    text = "\n".join(lines).strip()
    return text or None


def quote_from_local_file(
    repo_root: Path,
    path: str | None,
    start: int | None,
    end: int | None,
) -> tuple[str | None, str | None]:
    """
    Read the commented span from the workspace copy of the file.

    Multi-line selection → exact lines (`selection`).
    Single line → blank-line-bounded paragraph (`paragraph`).
    """
    if not path or end is None:
        return None, None
    file_path = repo_root / path
    if not file_path.is_file():
        return None, None
    try:
        file_lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, None
    if not file_lines:
        return None, None

    start_i = start or end
    start_i = max(1, min(start_i, len(file_lines)))
    end_i = max(1, min(end, len(file_lines)))

    if start_i != end_i:
        chunk = file_lines[start_i - 1 : end_i]
        return "\n".join(chunk).strip(), "selection"

    idx = end_i - 1
    lo = idx
    while lo > 0 and file_lines[lo - 1].strip() != "":
        lo -= 1
    hi = idx
    while hi + 1 < len(file_lines) and file_lines[hi + 1].strip() != "":
        hi += 1
    chunk = file_lines[lo : hi + 1]
    return "\n".join(chunk).strip(), "paragraph"


def resolve_quote(
    comment: Mapping[str, Any],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """
    Prefer local file text when present; otherwise clean diff_hunk.

    Returns quote, quote_source, start_line, line, and raw diff_hunk.
    """
    root = repo_root if repo_root is not None else _DEFAULT_REPO_ROOT
    start, end = line_range(comment)
    hunk = comment.get("diff_hunk")
    path = comment.get("path")
    path_str = str(path) if isinstance(path, str) else None

    file_quote, mode = quote_from_local_file(root, path_str, start, end)
    if file_quote:
        return {
            "quote": file_quote,
            "quote_source": mode or "paragraph",
            "start_line": start,
            "line": end,
            "diff_hunk": hunk,
        }

    hunk_quote = quote_from_diff_hunk(hunk if isinstance(hunk, str) else None)
    if hunk_quote:
        return {
            "quote": hunk_quote,
            "quote_source": "diff_hunk",
            "start_line": start,
            "line": end,
            "diff_hunk": hunk,
        }

    return {
        "quote": None,
        "quote_source": None,
        "start_line": start,
        "line": end,
        "diff_hunk": hunk,
    }
