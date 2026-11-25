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
        page.wait_for_selector(f'.tag-item:has(.tag-hashtag:text-is("{hashtag}"))')
        row = page.locator(f'.tag-item:has(.tag-hashtag:text-is("{hashtag}"))')
        # Stage via card label (hashtag / Copy use click.stop).
        row.locator(".tag-label").click()

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


def test_staged_panel_stays_in_view_while_catalog_scrolls(page, site_base_url):
    """14e: sticky staged panel remains near the top after scrolling the catalog."""
    page.set_viewport_size({"width": 420, "height": 640})
    page.goto(f"{site_base_url}/tags.html", wait_until="networkidle")
    page.wait_for_selector(".tag-item")
    page.wait_for_selector(".staged-panel")

    catalog = page.locator(".tag-catalog")
    assert catalog.count() == 1
    # Tall enough page that scrolling would move a non-sticky staged panel away.
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(100)

    top = page.locator(".staged-panel").evaluate(
        "el => el.getBoundingClientRect().top"
    )
    # Stuck near the top of the viewport (allow a little chrome padding).
    assert 0 <= top <= 80, f"staged panel top={top} after scroll (expected sticky)"


def test_catalog_copy_hashtag_without_staging(page, context, site_base_url):
    """14f: per-row Copy puts one hashtag on the clipboard; does not stage."""
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.goto(f"{site_base_url}/tags.html", wait_until="networkidle")
    page.wait_for_selector(".tag-item")
    hashtag = "#stance/ban"
    page.fill("#tag-search", hashtag)
    row = page.locator(f'.tag-item:has(.tag-hashtag:text-is("{hashtag}"))')
    row.wait_for()
    row.locator(".tag-copy").first.click()
    page.wait_for_selector("#copy-status:text-matches('Copied')")
    # Single-tag copy must not force the multi-stage workflow.
    assert page.locator("#staged-list li").count() == 0
    clip = page.evaluate("navigator.clipboard.readText()")
    assert clip.strip() == hashtag


def test_catalog_click_toggles_stage(page, site_base_url):
    """Card body click stages, then unstages."""
    page.goto(f"{site_base_url}/tags.html", wait_until="networkidle")
    page.wait_for_selector(".tag-item")
    hashtag = "#stance/ban"
    page.fill("#tag-search", hashtag)
    row = page.locator(f'.tag-item:has(.tag-hashtag:text-is("{hashtag}"))')
    row.locator(".tag-label").click()
    assert page.locator(f'#staged-list li:has(.tag-hashtag:text-is("{hashtag}"))').count() == 1
    row.locator(".tag-label").click()
    assert page.locator("#staged-list li").count() == 0
