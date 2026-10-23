"""Coding view entry points + when-to-use docs (10e)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
COMMENTING = REPO / "codebook" / "COMMENTING.md"
README = REPO / "README.md"
PROJECTS_JS = SITE / "js" / "projects.js"
PROJECTS_HTML = SITE / "projects.html"


def test_projects_page_links_per_slug_to_coding_view():
    js = PROJECTS_JS.read_text(encoding="utf-8")
    assert "coding.html?project=" in js
    html = PROJECTS_HTML.read_text(encoding="utf-8")
    assert 'href="coding.html"' in html


def test_commenting_md_distinguishes_picker_and_coding_view():
    text = COMMENTING.read_text(encoding="utf-8")
    lower = text.lower()
    assert "coding.html" in text or "coding view" in lower
    assert "project.yaml" in text
    assert "tag picker" in lower
    # Three roles: passage comments, overall coding, not "comes later"
    assert "comes later" not in lower
    assert "copy yaml" in lower or "coding:" in text


def test_readme_mentions_coding_view():
    text = README.read_text(encoding="utf-8")
    lower = text.lower()
    assert "coding.html" in text or "coding view" in lower
    assert "tags.html" in text
