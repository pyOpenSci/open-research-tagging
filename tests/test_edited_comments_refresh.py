"""13j: edited Files-tab comments must refresh after fetch + process."""

from __future__ import annotations

import json
from pathlib import Path

from open_research_tagging.codebook import Codebook, validate_codebook
from open_research_tagging.comments import normalize
from open_research_tagging.fetch_comments import (
    fetch_all_review_comments,
    write_raw_comments,
)
from open_research_tagging import process_comments as pc

from codebook_fixtures import minimal_codebook


def _codebook() -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook()))


def _raw(
    *,
    body: str,
    updated_at: str,
    comment_id: int = 42,
) -> dict:
    return {
        "id": comment_id,
        "body": body,
        "path": "projects/acme/policy.md",
        "user": {"login": "alice"},
        "pull_request_url": "https://api.github.com/repos/o/r/pulls/3",
        "html_url": "https://github.com/o/r/pull/3#discussion_r42",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": updated_at,
        "line": 1,
        "diff_hunk": "@@ -1 +1 @@\n+line\n",
    }


def test_normalize_uses_current_body_and_updated_at():
    """Same comment id with a new body → new tags (edit simulation)."""
    before = normalize(
        _raw(body="#stance/ban\nold", updated_at="2026-01-01T00:00:00Z"),
        _codebook(),
        repo_root=Path("/nonexistent"),
    )
    after = normalize(
        _raw(body="#stance/allow\nedited", updated_at="2026-01-03T12:00:00Z"),
        _codebook(),
        repo_root=Path("/nonexistent"),
    )
    assert before["id"] == after["id"] == 42
    assert before["tag_strings"] == ["#stance/ban"]
    assert after["tag_strings"] == ["#stance/allow"]
    assert after["body"].startswith("#stance/allow")
    assert after["updated_at"] == "2026-01-03T12:00:00Z"


def test_fetch_passthrough_keeps_edited_body_fields():
    """List-comments API objects are stored as-is (body + updated_at)."""
    pages = {
        "https://api.github.com/repos/o/r/pulls/comments?per_page=100": (
            [
                {
                    "id": 7,
                    "body": "#stance/allow\nafter edit",
                    "updated_at": "2026-02-01T00:00:00Z",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ],
            {},
        ),
    }

    def getter(url: str, headers: dict[str, str]):
        return pages[url]

    comments = fetch_all_review_comments("o", "r", token="t", getter=getter)
    assert comments[0]["body"] == "#stance/allow\nafter edit"
    assert comments[0]["updated_at"] == "2026-02-01T00:00:00Z"


def test_process_comments_rebuilds_from_raw_not_prior_json(
    tmp_path: Path, monkeypatch
):
    """Re-running process after an edit must not keep stale tags from prior out."""
    raw_path = tmp_path / "raw_comments.json"
    out_path = tmp_path / "comments.json"
    codebook_arg = tmp_path / "unused-codebook.yaml"

    write_raw_comments(
        comments=[_raw(body="#stance/ban", updated_at="2026-01-01T00:00:00Z")],
        owner="o",
        repo="r",
        path=raw_path,
    )
    monkeypatch.setattr(pc, "load_codebook", lambda path: _codebook())
    pc.main(
        [
            "--in",
            str(raw_path),
            "--out",
            str(out_path),
            "--codebook",
            str(codebook_arg),
            "--repo-root",
            str(tmp_path),
        ]
    )
    first = json.loads(out_path.read_text(encoding="utf-8"))
    assert first["data"][0]["tag_strings"] == ["#stance/ban"]

    write_raw_comments(
        comments=[
            _raw(
                body="#stance/allow\nedited note",
                updated_at="2026-01-05T00:00:00Z",
            )
        ],
        owner="o",
        repo="r",
        path=raw_path,
    )
    pc.main(
        [
            "--in",
            str(raw_path),
            "--out",
            str(out_path),
            "--codebook",
            str(codebook_arg),
            "--repo-root",
            str(tmp_path),
        ]
    )
    second = json.loads(out_path.read_text(encoding="utf-8"))
    row = second["data"][0]
    assert row["id"] == 42
    assert row["tag_strings"] == ["#stance/allow"]
    assert "edited note" in row["body"]
    assert row["updated_at"] == "2026-01-05T00:00:00Z"
