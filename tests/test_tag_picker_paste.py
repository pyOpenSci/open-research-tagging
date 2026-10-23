"""9e: staged picker output as a review-comment body must parse cleanly."""

from __future__ import annotations

from pathlib import Path

import pytest

from open_research_tagging.codebook import load_codebook
from open_research_tagging.tag_catalog import canonical_tag_strings
from open_research_tagging.tags import collect_tag_warnings, parse_tags

pytest.importorskip("playwright")
pytest.importorskip("pytest_playwright")

REPO = Path(__file__).resolve().parents[1]
CODEBOOK_YAML = REPO / "codebook" / "codebook.yaml"

pytestmark = pytest.mark.integration


def comment_body_from_copy_text(copy_text: str, note: str) -> str:
    """COMMENTING.md shape: hashtags, blank line, free-text note."""
    block = (copy_text or "").strip()
    return f"{block}\n\n{note.strip()}\n"


def test_comment_shape_from_canonical_strings_parses_clean():
    codebook = load_codebook(CODEBOOK_YAML)
    strings = canonical_tag_strings(codebook)
    # Mix value + scope
    sample = [
        next(s for s in strings if s.startswith("#stance/")),
        next(s for s in strings if s.startswith("#scope/")),
        next(s for s in strings if s.startswith("#disclosure/")),
    ]
    copy_text = "\n".join(sample)
    body = comment_body_from_copy_text(copy_text, "Passage note for parse check.")
    tags = parse_tags(body)
    assert [t["raw"] for t in tags] == sample
    assert collect_tag_warnings(body, tags, codebook) == []


def test_picker_stage_copy_preview_parses_as_review_comment(page, site_base_url):
    codebook = load_codebook(CODEBOOK_YAML)
    page.goto(f"{site_base_url}/tags.html", wait_until="networkidle")
    page.wait_for_selector(".tag-row")

    # Stage one stance, one scope, one disclosure via search + click
    expected = [
        "#stance/permissive-with-conditions",
        "#scope/code:restricted",
        "#disclosure/required",
    ]
    for hashtag in expected:
        page.fill("#tag-search", hashtag)
        page.wait_for_selector(f'.tag-row:not([disabled]) .tag-hashtag:text-is("{hashtag}")')
        page.locator(
            f'.tag-row:not([disabled]):has(.tag-hashtag:text-is("{hashtag}"))'
        ).click()

    page.wait_for_selector("#copy-preview")
    copy_text = page.locator("#copy-preview").input_value()
    assert copy_text
    lines = [ln for ln in copy_text.splitlines() if ln.strip()]
    assert lines == expected

    body = comment_body_from_copy_text(
        copy_text, "Automated 9e paste-shape check."
    )
    tags = parse_tags(body)
    assert [t["raw"] for t in tags] == lines
    assert collect_tag_warnings(body, tags, codebook) == []
