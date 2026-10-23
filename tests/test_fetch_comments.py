"""Fetch all PR review comments into raw_comments.json (no live network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from open_research_tagging.fetch_comments import (
    FetchConfigError,
    fetch_all_review_comments,
    resolve_owner_repo,
    write_raw_comments,
)


def test_resolve_owner_repo_from_flags():
    assert resolve_owner_repo(owner="o", repo="r", env_repository=None) == (
        "o",
        "r",
    )


def test_resolve_owner_repo_from_env():
    assert resolve_owner_repo(
        owner=None, repo=None, env_repository="acme/widget"
    ) == ("acme", "widget")


def test_resolve_owner_repo_flags_override_env():
    assert resolve_owner_repo(
        owner="a", repo="b", env_repository="x/y"
    ) == ("a", "b")


def test_resolve_owner_repo_missing_raises():
    with pytest.raises(FetchConfigError, match="owner"):
        resolve_owner_repo(owner=None, repo=None, env_repository=None)
    with pytest.raises(FetchConfigError, match="owner"):
        resolve_owner_repo(owner=None, repo=None, env_repository="noslash")


def test_fetch_all_review_comments_paginates(tmp_path: Path):
    pages = {
        "https://api.github.com/repos/o/r/pulls/comments?per_page=100": (
            [{"id": 1}, {"id": 2}],
            {
                "link": (
                    '<https://api.github.com/repos/o/r/pulls/comments'
                    '?per_page=100&page=2>; rel="next"'
                )
            },
        ),
        (
            "https://api.github.com/repos/o/r/pulls/comments"
            "?per_page=100&page=2"
        ): (
            [{"id": 3}],
            {},
        ),
    }

    def getter(url: str, headers: dict[str, str]):
        assert "Authorization" in headers
        return pages[url]

    comments = fetch_all_review_comments(
        "o", "r", token="tok", getter=getter
    )
    assert [c["id"] for c in comments] == [1, 2, 3]


def test_write_raw_comments_payload(tmp_path: Path):
    out = tmp_path / "data" / "raw_comments.json"
    payload = write_raw_comments(
        comments=[{"id": 9, "body": "#stance/ban"}],
        owner="o",
        repo="r",
        path=out,
    )
    assert payload["source"] == "o/r"
    assert payload["count"] == 1
    assert "pulls/comments" in payload["endpoint"]
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["comments"][0]["id"] == 9


def test_fetch_comments_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from open_research_tagging import fetch_comments as fc

    monkeypatch.setattr(
        fc,
        "fetch_all_review_comments",
        lambda owner, repo, token=None, getter=None: [{"id": 42}],
    )
    out = tmp_path / "raw_comments.json"
    fc.main(["--owner", "o", "--repo", "r", "--out", str(out)])
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["count"] == 1
    assert loaded["comments"][0]["id"] == 42
    assert loaded["source"] == "o/r"
