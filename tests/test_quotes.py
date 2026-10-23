"""Quote resolution from local files or GitHub diff_hunk."""

from pathlib import Path

from open_research_tagging.quotes import (
    line_range,
    quote_from_diff_hunk,
    quote_from_local_file,
    resolve_quote,
)


def test_line_range_single_line():
    assert line_range({"line": 5}) == (5, 5)


def test_line_range_multi_line():
    assert line_range({"start_line": 2, "line": 4}) == (2, 4)


def test_line_range_swaps_if_start_after_end():
    assert line_range({"start_line": 9, "line": 3}) == (3, 9)


def test_line_range_missing():
    assert line_range({}) == (None, None)


def test_quote_from_local_file_selection(tmp_path: Path):
    path = tmp_path / "doc.md"
    path.write_text("a\nb\nc\nd\n", encoding="utf-8")
    quote, mode = quote_from_local_file(tmp_path, "doc.md", 2, 3)
    assert mode == "selection"
    assert quote == "b\nc"


def test_quote_from_local_file_paragraph(tmp_path: Path):
    path = tmp_path / "doc.md"
    path.write_text("intro\n\nalpha\nbeta\ngamma\n\nafter\n", encoding="utf-8")
    quote, mode = quote_from_local_file(tmp_path, "doc.md", 4, 4)
    assert mode == "paragraph"
    assert quote == "alpha\nbeta\ngamma"


def test_quote_from_local_file_missing_file(tmp_path: Path):
    assert quote_from_local_file(tmp_path, "nope.md", 1, 1) == (None, None)


def test_quote_from_diff_hunk_strips_and_skips_deletions():
    hunk = "@@ -1,3 +1,3 @@\n context\n-old\n+new\n"
    assert quote_from_diff_hunk(hunk) == "context\nnew"


def test_resolve_quote_prefers_local_file(tmp_path: Path):
    (tmp_path / "f.md").write_text("only line\n", encoding="utf-8")
    comment = {
        "path": "f.md",
        "line": 1,
        "diff_hunk": "@@\n+hunk text\n",
    }
    result = resolve_quote(comment, repo_root=tmp_path)
    assert result["quote"] == "only line"
    assert result["quote_source"] == "paragraph"
    assert result["diff_hunk"] == "@@\n+hunk text\n"


def test_resolve_quote_falls_back_to_diff_hunk(tmp_path: Path):
    comment = {
        "path": "missing.md",
        "line": 1,
        "diff_hunk": "@@\n+from hunk\n",
    }
    result = resolve_quote(comment, repo_root=tmp_path)
    assert result["quote"] == "from hunk"
    assert result["quote_source"] == "diff_hunk"


def test_resolve_quote_empty_when_nothing_available(tmp_path: Path):
    result = resolve_quote({"path": "x.md", "line": 1}, repo_root=tmp_path)
    assert result["quote"] is None
    assert result["quote_source"] is None
    assert result["start_line"] == 1
    assert result["line"] == 1
