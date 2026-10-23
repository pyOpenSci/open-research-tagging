"""Actions CLI for check_tags (no live network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from codebook_fixtures import minimal_codebook
from open_research_tagging.check_tags import main


@pytest.fixture
def codebook_path(tmp_path: Path) -> Path:
    path = tmp_path / "codebook.yaml"
    path.write_text(yaml.dump(minimal_codebook()), encoding="utf-8")
    return path


def test_cli_body_clean_exits_0(codebook_path: Path):
    code = main(
        ["--body", "#stance/ban", "--codebook", str(codebook_path)]
    )
    assert code == 0


def test_cli_body_dirty_exits_1(codebook_path: Path):
    code = main(["--body", "#Design", "--codebook", str(codebook_path)])
    assert code == 1


def test_cli_body_soft_exits_0(codebook_path: Path):
    code = main(
        ["--body", "#Design", "--soft", "--codebook", str(codebook_path)]
    )
    assert code == 0


def test_cli_from_event_with_reply(
    tmp_path: Path,
    codebook_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    event = {
        "comment": {
            "id": 99,
            "body": "#Design",
            "html_url": "https://github.com/o/r/pull/1#discussion_r99",
            "user": {"login": "alice"},
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_TOKEN", "tok")

    posted: list[tuple] = []

    def poster(url: str, headers: dict, data: bytes | None):
        posted.append((url, json.loads(data or b"{}")))
        return {"id": 1}, {}

    code = main(
        [
            "--from-event",
            "--reply",
            "--codebook",
            str(codebook_path),
        ],
        poster=poster,
    )
    assert code == 1
    assert len(posted) == 1
    assert posted[0][0].endswith("/pulls/comments/99/replies")
    assert "Tag format check" in posted[0][1]["body"]


def test_cli_from_event_skips_bot_reply(
    tmp_path: Path,
    codebook_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    event = {
        "comment": {
            "id": 99,
            "body": "#Design",
            "user": {"login": "dependabot[bot]"},
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_TOKEN", "tok")

    posted: list = []

    def poster(url: str, headers: dict, data: bytes | None):
        posted.append(url)
        return {}, {}

    code = main(
        ["--from-event", "--reply", "--codebook", str(codebook_path)],
        poster=poster,
    )
    assert code == 1
    assert posted == []


def test_cli_pr_scan(codebook_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")

    def getter(url: str, headers: dict):
        assert "pulls/3/comments" in url
        return (
            [
                {
                    "id": 1,
                    "body": "#stance/ban",
                    "html_url": "u1",
                    "user": {"login": "alice"},
                },
                {
                    "id": 2,
                    "body": "#Design",
                    "html_url": "u2",
                    "user": {"login": "bob"},
                },
                {
                    "id": 3,
                    "body": "#Design",
                    "html_url": "u3",
                    "user": {"login": "bot[bot]"},
                },
            ],
            {},
        )

    code = main(
        ["--pr", "3", "--codebook", str(codebook_path)],
        getter=getter,
    )
    assert code == 1


def test_cli_missing_mode_exits_2(codebook_path: Path):
    code = main(["--codebook", str(codebook_path)])
    assert code == 2
