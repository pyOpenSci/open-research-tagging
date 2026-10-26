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


def test_cli_body_malformed_exits_1(codebook_path: Path):
    code = main(["--body", "#Design", "--codebook", str(codebook_path)])
    assert code == 1


def test_cli_body_unknown_id_exits_0(codebook_path: Path):
    """Draft policy: well-formed but unknown ids do not fail the check."""
    code = main(
        ["--body", "#stance/nope", "--codebook", str(codebook_path)]
    )
    assert code == 0


def test_cli_body_mix_malformed_and_unknown_exits_1(codebook_path: Path):
    code = main(
        [
            "--body",
            "#Design\n#stance/nope",
            "--codebook",
            str(codebook_path),
        ]
    )
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
        "pull_request": {"number": 7},
        "comment": {
            "id": 99,
            "body": "#Design",
            "html_url": "https://github.com/o/r/pull/7#discussion_r99",
            "user": {"login": "alice"},
        },
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
    assert posted[0][0].endswith("/pulls/7/comments/99/replies")
    assert "Tag format check" in posted[0][1]["body"]


def test_cli_from_event_soft_survives_reply_http_error(
    tmp_path: Path,
    codebook_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """--soft must exit 0 even if the reply POST fails (workflow promise)."""
    from open_research_tagging.github_client import GitHubHTTPError

    event = {
        "pull_request": {"number": 7},
        "comment": {
            "id": 99,
            "body": "#Design",
            "user": {"login": "alice"},
        },
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_TOKEN", "tok")

    def poster(url: str, headers: dict, data: bytes | None):
        raise GitHubHTTPError(404, url, '{"message":"Not Found"}')

    code = main(
        [
            "--from-event",
            "--reply",
            "--soft",
            "--codebook",
            str(codebook_path),
        ],
        poster=poster,
    )
    assert code == 0


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
