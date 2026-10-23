"""COMMENTING.md should point at the tag picker, not a second full tag table."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMMENTING = REPO / "codebook" / "COMMENTING.md"


def test_commenting_md_workflow_points_at_picker():
    text = COMMENTING.read_text(encoding="utf-8")
    lower = text.lower()
    assert "tags.html" in text
    assert "tag picker" in lower
    assert "copy" in lower
    # No hand-maintained full id catalogs (picker + codebook.yaml are canonical)
    assert "## Tag reference" not in text
    assert "**Stance ids:**" not in text
    assert "**Scope types:**" not in text
    assert "**Rationale ids:**" not in text
