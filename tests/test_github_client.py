"""Shared GitHub HTTP client: headers, GET, Link pagination (no live network)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from open_research_tagging.github_client import (
    GitHubHTTPError,
    auth_headers,
    github_get,
    github_post,
    next_link,
    paginate,
)


def test_auth_headers_include_accept_and_optional_bearer():
    bare = auth_headers(None)
    assert bare["Accept"] == "application/vnd.github+json"
    assert "Authorization" not in bare
    assert "X-GitHub-Api-Version" in bare

    authed = auth_headers("tok_abc")
    assert authed["Authorization"] == "Bearer tok_abc"


def test_next_link_parses_rel_next():
    link = (
        '<https://api.github.com/r?page=1>; rel="prev", '
        '<https://api.github.com/r?page=2>; rel="next"'
    )
    assert next_link(link) == "https://api.github.com/r?page=2"
    assert next_link(None) is None
    assert next_link("") is None
    assert next_link('<https://api.github.com/r?page=1>; rel="last"') is None


def test_github_get_uses_injected_getter():
    def fake_getter(url: str, headers: dict[str, str]) -> tuple[Any, dict[str, str]]:
        assert url == "https://api.github.com/repos/o/r/pulls/comments"
        assert headers["Authorization"] == "Bearer secret"
        return [{"id": 1}], {"link": ""}

    body, headers = github_get(
        "https://api.github.com/repos/o/r/pulls/comments",
        "secret",
        getter=fake_getter,
    )
    assert body == [{"id": 1}]
    assert headers.get("link") == ""


def test_github_get_raises_http_error_from_getter():
    def boom(url: str, headers: dict[str, str]) -> tuple[Any, dict[str, str]]:
        raise GitHubHTTPError(404, url, '{"message":"Not Found"}')

    with pytest.raises(GitHubHTTPError, match="404") as exc_info:
        github_get("https://api.github.com/x", None, getter=boom)
    assert exc_info.value.status == 404
    assert "Not Found" in exc_info.value.body


def test_paginate_follows_link_next():
    pages = {
        "https://api.github.com/items?page=1": (
            [{"id": 1}, {"id": 2}],
            {
                "link": (
                    '<https://api.github.com/items?page=2>; rel="next"'
                )
            },
        ),
        "https://api.github.com/items?page=2": (
            [{"id": 3}],
            {"link": ""},
        ),
    }

    def fake_getter(url: str, headers: dict[str, str]) -> tuple[Any, dict[str, str]]:
        return pages[url]

    items = paginate(
        "https://api.github.com/items?page=1",
        token=None,
        getter=fake_getter,
    )
    assert items == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_paginate_rejects_non_list_page():
    def fake_getter(url: str, headers: dict[str, str]) -> tuple[Any, dict[str, str]]:
        return {"message": "nope"}, {}

    with pytest.raises(GitHubHTTPError, match="list"):
        paginate("https://api.github.com/x", None, getter=fake_getter)


def test_default_getter_parses_json_bytes():
    """Smoke that default path wires urllib-shaped responses via a stub opener."""
    class Resp:
        headers = {"Link": '<https://api.github.com/next>; rel="next"'}

        def read(self) -> bytes:
            return json.dumps([{"ok": True}]).encode()

        def __enter__(self) -> "Resp":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(req: object) -> Resp:
        return Resp()

    body, headers = github_get(
        "https://api.github.com/x",
        None,
        urlopen=fake_urlopen,
    )
    assert body == [{"ok": True}]
    assert next_link(headers.get("link")) == "https://api.github.com/next"


def test_github_post_uses_injected_poster():
    def fake_poster(url: str, headers: dict[str, str], data: bytes | None):
        assert url.endswith("/replies")
        assert headers["Authorization"] == "Bearer secret"
        assert headers["Content-Type"] == "application/json"
        assert json.loads(data or b"{}") == {"body": "hi"}
        return {"ok": True}, {}

    body, _headers = github_post(
        "https://api.github.com/repos/o/r/pulls/1/comments/1/replies",
        "secret",
        {"body": "hi"},
        poster=fake_poster,
    )
    assert body == {"ok": True}
