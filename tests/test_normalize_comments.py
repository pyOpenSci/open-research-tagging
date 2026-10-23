"""Normalize raw GitHub review comments into comments.json rows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from open_research_tagging.codebook import Codebook, validate_codebook
from open_research_tagging.comments import (
    ProcessedCommentsError,
    build_comments_payload,
    load_raw_comments,
    normalize,
    write_comments_json,
)

from codebook_fixtures import minimal_codebook


def _codebook() -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook()))


def _sample_raw(**overrides: object) -> dict:
    base: dict = {
        "id": 99,
        "body": "#disclosure/required\n\nnote",
        "path": "projects/acme/policy.md",
        "user": {"login": "alice"},
        "pull_request_url": "https://api.github.com/repos/o/r/pulls/3",
        "html_url": "https://github.com/o/r/pull/3#discussion_r99",
        "side": "RIGHT",
        "commit_id": "abc123",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "line": 2,
        "diff_hunk": "@@ -1,3 +1,3 @@\n+Hello world\n",
    }
    base.update(overrides)
    return base


def test_normalize_happy_path_tags_and_refs():
    row = normalize(_sample_raw(), _codebook(), repo_root=Path("/nonexistent"))
    assert row["id"] == 99
    assert row["project"] == "acme"
    assert row["user"] == "alice"
    assert row["pr_number"] == 3
    assert row["needs_tag_review"] is False
    assert row["parse_warnings"] == []
    assert "disclosure:required" in row["filter_keys"]
    assert row["tag_strings"] == ["#disclosure/required"]
    assert row["displays"] == ["Disclosure: Required"]
    assert row["codes"]["disclosure"][0]["value"] == "required"
    assert row["quote_source"] == "diff_hunk"
    assert row["quote"]
    assert row["side"] == "RIGHT"
    assert row["commit_id"] == "abc123"


def test_normalize_sets_needs_tag_review_on_warnings():
    bad = _sample_raw(body="#Design")
    row = normalize(bad, _codebook(), repo_root=Path("/nonexistent"))
    assert row["needs_tag_review"] is True
    assert row["parse_warnings"]
    assert row["tags"] == []


def test_load_raw_comments_list_and_comments_key(tmp_path: Path):
    as_list = tmp_path / "raw.json"
    as_list.write_text(json.dumps([_sample_raw()]), encoding="utf-8")
    assert len(load_raw_comments(as_list)) == 1

    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(json.dumps({"comments": [_sample_raw()]}), encoding="utf-8")
    assert len(load_raw_comments(wrapped)) == 1


def test_load_raw_comments_rejects_processed_payload(tmp_path: Path):
    path = tmp_path / "comments.json"
    path.write_text(
        json.dumps({"meta": {"count": 0}, "data": []}),
        encoding="utf-8",
    )
    with pytest.raises(ProcessedCommentsError, match="processed already"):
        load_raw_comments(path)


def test_build_and_write_payload_meta(tmp_path: Path):
    codebook = _codebook()
    rows = [normalize(_sample_raw(), codebook, repo_root=Path("/nonexistent"))]
    source = Path("site/data/raw_comments.fixture.json")
    payload = build_comments_payload(
        rows,
        source_file=source,
        codebook=codebook,
        repo_root=tmp_path,
    )
    assert payload["meta"]["count"] == 1
    assert payload["meta"]["is_fixture"] is True
    assert payload["meta"]["codebook_version"] == "test-0.1"
    assert "fixture" in payload["meta"]["source_file"]

    out = tmp_path / "site" / "data" / "comments.json"
    write_comments_json(payload, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["meta"]["count"] == 1
    assert loaded["data"][0]["filter_keys"] == ["disclosure:required"]


def test_payload_is_fixture_false_for_live_raw_name(tmp_path: Path):
    codebook = _codebook()
    payload = build_comments_payload(
        [],
        source_file=tmp_path / "raw_comments.json",
        codebook=codebook,
        repo_root=tmp_path,
    )
    assert payload["meta"]["is_fixture"] is False
    assert payload["meta"]["count"] == 0


def test_normalize_empty_body():
    row = normalize(
        _sample_raw(body=""),
        _codebook(),
        repo_root=Path("/nonexistent"),
    )
    assert row["tags"] == []
    assert row["needs_tag_review"] is False
    assert row["body"] == ""


def test_normalize_scope_codes_shape():
    row = normalize(
        _sample_raw(body="#scope/code:banned"),
        _codebook(),
        repo_root=Path("/nonexistent"),
    )
    assert row["needs_tag_review"] is False
    entry = row["codes"]["scope"][0]
    assert entry["contribution_type"] == "code"
    assert entry["position"] == "banned"
    assert entry["filter_key"] == "scope:code:banned"


def test_load_raw_comments_empty_list(tmp_path: Path):
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")
    assert load_raw_comments(path) == []


def test_load_raw_comments_unrecognized_shape(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"foo": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unrecognized JSON shape"):
        load_raw_comments(path)


def test_process_comments_cli(tmp_path: Path):
    from codebook_fixtures import REAL_CODEBOOK_PATH
    from open_research_tagging.process_comments import main

    raw_path = tmp_path / "raw_comments.fixture.json"
    raw_path.write_text(json.dumps([_sample_raw()]), encoding="utf-8")
    out = tmp_path / "comments.json"
    main(
        [
            "--in",
            str(raw_path),
            "--out",
            str(out),
            "--codebook",
            str(REAL_CODEBOOK_PATH),
            "--repo-root",
            str(tmp_path),
        ]
    )
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["meta"]["is_fixture"] is True
    assert loaded["meta"]["count"] == 1
    assert "disclosure:required" in loaded["data"][0]["filter_keys"]
