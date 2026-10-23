"""Offline fixture: raw_comments.fixture.json → comments.json shape."""

from __future__ import annotations

import json
from pathlib import Path

from open_research_tagging.codebook import load_codebook
from open_research_tagging.comments import (
    build_comments_payload,
    load_raw_comments,
    normalize,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "site" / "data" / "raw_comments.fixture.json"
CODEBOOK = REPO_ROOT / "codebook" / "codebook.yaml"
COMMITTED_COMMENTS = REPO_ROOT / "site" / "data" / "comments.json"


def test_fixture_file_exists():
    assert FIXTURE.is_file(), f"missing offline fixture: {FIXTURE}"


def test_process_fixture_end_to_end():
    codebook = load_codebook(CODEBOOK)
    raw = load_raw_comments(FIXTURE)
    assert len(raw) >= 1
    rows = [normalize(c, codebook, repo_root=REPO_ROOT) for c in raw]
    payload = build_comments_payload(
        rows,
        source_file=FIXTURE,
        codebook=codebook,
        repo_root=REPO_ROOT,
    )
    assert payload["meta"]["is_fixture"] is True
    assert payload["meta"]["count"] == len(raw)
    assert payload["meta"]["codebook_version"]
    for row in payload["data"]:
        assert "filter_keys" in row
        assert "needs_tag_review" in row
        assert isinstance(row["needs_tag_review"], bool)
        assert row["project"] == "pyopensci"


def test_committed_comments_json_matches_fixture_count():
    assert COMMITTED_COMMENTS.is_file()
    raw = load_raw_comments(FIXTURE)
    loaded = json.loads(COMMITTED_COMMENTS.read_text(encoding="utf-8"))
    assert loaded["meta"]["is_fixture"] is True
    assert loaded["meta"]["count"] == len(raw)
    assert len(loaded["data"]) == len(raw)
