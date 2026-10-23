"""Shared GitHub HTTP helpers (auth headers, GET, Link pagination).

Used by fetch and tag-check entrypoints. Tests inject a getter or urlopen so
CI never hits the live API.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping

API_VERSION = "2022-11-28"
USER_AGENT = "open-research-tagging"

Getter = Callable[[str, dict[str, str]], tuple[Any, dict[str, str]]]
Poster = Callable[
    [str, dict[str, str], bytes | None],
    tuple[Any, dict[str, str]],
]
UrlOpen = Callable[[urllib.request.Request], Any]


class GitHubHTTPError(Exception):
    """GitHub API returned an error status or unexpected payload shape."""

    def __init__(self, status: int, url: str, body: str) -> None:
        self.status = status
        self.url = url
        self.body = body
        super().__init__(f"GitHub API error {status} for {url}: {body}")


def auth_headers(token: str | None) -> dict[str, str]:
    """Standard GitHub REST headers; Bearer token when provided."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def next_link(link_header: str | None) -> str | None:
    """Parse Link header for rel=\"next\" URL, if any."""
    if not link_header:
        return None
    for part in link_header.split(","):
        bit = part.strip()
        if 'rel="next"' in bit:
            start = bit.find("<")
            end = bit.find(">")
            if start != -1 and end != -1 and end > start:
                return bit[start + 1 : end]
    return None


def _default_getter(
    url: str,
    headers: dict[str, str],
    *,
    urlopen: UrlOpen | None = None,
) -> tuple[Any, dict[str, str]]:
    open_fn = urlopen or urllib.request.urlopen
    req = urllib.request.Request(url, headers=headers)
    try:
        with open_fn(req) as resp:
            raw = resp.read()
            if isinstance(raw, bytes):
                text = raw.decode("utf-8")
            else:
                text = str(raw)
            body = json.loads(text) if text else None
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return body, resp_headers
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GitHubHTTPError(exc.code, url, detail) from exc


def github_get(
    url: str,
    token: str | None,
    *,
    getter: Getter | None = None,
    urlopen: UrlOpen | None = None,
) -> tuple[Any, dict[str, str]]:
    """
    GET a GitHub API URL and return (parsed JSON, lowercase header map).

    Prefer `getter` for tests. `urlopen` stubs only the urllib call.
    """
    headers = auth_headers(token)
    if getter is not None:
        return getter(url, headers)
    return _default_getter(url, headers, urlopen=urlopen)


def paginate(
    url: str,
    token: str | None,
    *,
    getter: Getter | None = None,
    urlopen: UrlOpen | None = None,
) -> list[Any]:
    """Follow Link rel=next until exhausted; each page must be a JSON list."""
    items: list[Any] = []
    current: str | None = url
    while current:
        page, headers = github_get(
            current, token, getter=getter, urlopen=urlopen
        )
        if not isinstance(page, list):
            raise GitHubHTTPError(
                0,
                current,
                f"expected list page, got {type(page).__name__}",
            )
        items.extend(page)
        current = next_link(headers.get("link"))
    return items


def _default_poster(
    url: str,
    headers: dict[str, str],
    data: bytes | None,
    *,
    urlopen: UrlOpen | None = None,
) -> tuple[Any, dict[str, str]]:
    open_fn = urlopen or urllib.request.urlopen
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with open_fn(req) as resp:
            raw = resp.read()
            if isinstance(raw, bytes):
                text = raw.decode("utf-8")
            else:
                text = str(raw)
            body = json.loads(text) if text else {}
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return body, resp_headers
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GitHubHTTPError(exc.code, url, detail) from exc


def github_post(
    url: str,
    token: str | None,
    payload: Mapping[str, Any] | None = None,
    *,
    poster: Poster | None = None,
    urlopen: UrlOpen | None = None,
) -> tuple[Any, dict[str, str]]:
    """
    POST JSON to a GitHub API URL; return (parsed JSON, lowercase headers).

    Prefer `poster` for tests.
    """
    headers = auth_headers(token)
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}
    if poster is not None:
        return poster(url, headers, data)
    return _default_poster(url, headers, data, urlopen=urlopen)
