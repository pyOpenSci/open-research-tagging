"""Library helpers for Actions tag-check (shared warning rules with normalize)."""

from __future__ import annotations

import os

from open_research_tagging.codebook import Codebook
from open_research_tagging.tags import parse_and_enrich, tag_warnings

GUIDE_PATH = "codebook/COMMENTING.md"


def check_body(body: str | None, codebook: Codebook) -> list[str]:
    """Return tag warnings for a comment body (empty list if clean)."""
    text = body or ""
    tags = parse_and_enrich(text, codebook)
    return tag_warnings(text, tags, codebook)


def format_reply(
    warnings: list[str],
    *,
    guide_repo: str | None = None,
) -> str:
    """Markdown reply body for a review comment with bad/unknown tags."""
    repo = (
        guide_repo
        or os.environ.get("GITHUB_REPOSITORY")
        or "owner/open-research-tagging"
    )
    guide_url = f"https://github.com/{repo}/blob/main/{GUIDE_PATH}"
    lines = [
        "⚠️ **Tag format check** — this review comment has hashtags that "
        "won't be picked up by the research site.",
        "",
    ]
    for warning in warnings:
        lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "Expected shape:",
            "```",
            "#disclosure/required",
            "#stance/permissive-with-conditions",
            "",
            "Optional free-text note…",
            "```",
            "",
            f"Guide: {guide_url}",
        ]
    )
    return "\n".join(lines)
