"""11e: PR template + README enable-Pages / demo-prep checklist."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PR_TEMPLATE = REPO / ".github" / "PULL_REQUEST_TEMPLATE.md"
README = REPO / "README.md"


def test_pr_template_points_at_picker_and_coding_view():
    assert PR_TEMPLATE.is_file(), f"missing {PR_TEMPLATE}"
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    lower = text.lower()
    assert "projects/" in text
    assert "files tab" in lower or "Files tab" in text
    assert "tag picker" in lower or "tags.html" in text
    assert "COMMENTING.md" in text
    assert "coding view" in lower or "coding.html" in text
    assert "project.yaml" in text
    assert "#namespace/value" in text or "#stance/" in text


def test_readme_enable_pages_checklist():
    text = README.read_text(encoding="utf-8")
    lower = text.lower()
    assert "github actions" in lower
    assert "pages" in lower
    assert "update comment data" in lower or "update-comments" in text
    assert "tag picker" in lower
    assert "coding view" in lower or "coding.html" in text
    assert "enable" in lower or "settings" in lower
