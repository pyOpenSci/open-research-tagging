"""Canonical tag catalog for the passage tag picker (9a)."""

from __future__ import annotations

from pathlib import Path

import pytest

from open_research_tagging.codebook import load_codebook
from open_research_tagging.codebook_emit import emit_codebook_json
from open_research_tagging.tag_catalog import (
    canonical_tag_entries,
    canonical_tag_strings,
)
from open_research_tagging.codebook import load_codebook_file
from open_research_tagging.tags import collect_tag_warnings, parse_tags

REPO = Path(__file__).resolve().parents[1]
CODEBOOK_YAML = REPO / "codebook" / "codebook.yaml"
SITE = REPO / "site"
TAGS_HTML = SITE / "tags.html"


@pytest.fixture
def codebook():
    return load_codebook(CODEBOOK_YAML)


def test_canonical_strings_are_unique_and_parse_clean(codebook):
    entries = canonical_tag_entries(codebook)
    strings = canonical_tag_strings(codebook)
    assert entries
    assert len(strings) == len(entries)
    assert len(set(strings)) == len(strings)

    for entry in entries:
        assert entry["hashtag"].startswith("#")
        assert entry["label"]
        assert entry["dimension"]
        assert entry["namespace"]
        parsed = parse_tags(entry["hashtag"])
        assert len(parsed) == 1
        warnings = collect_tag_warnings(entry["hashtag"], parsed, codebook)
        assert warnings == [], (entry["hashtag"], warnings)


def test_scope_pairs_are_fully_enumerated(codebook):
    scope = [
        e for e in canonical_tag_entries(codebook) if e["kind"] == "scope"
    ]
    n_types = len(codebook._scope_types)
    n_pos = len(codebook._scope_positions)
    assert len(scope) == n_types * n_pos
    assert any(e["hashtag"] == "#scope/code:restricted" for e in scope)


def test_emit_includes_tag_catalog_matching_helper(codebook):
    raw = load_codebook_file(CODEBOOK_YAML)
    payload = emit_codebook_json(raw)
    assert "tag_catalog" in payload
    helper = canonical_tag_entries(codebook)
    assert [e["hashtag"] for e in payload["tag_catalog"]] == [
        e["hashtag"] for e in helper
    ]


def test_tags_page_wires_catalog_ui():
    html = TAGS_HTML.read_text(encoding="utf-8")
    assert 'href="css/site.css"' in html
    assert "alpinejs" in html.lower()
    assert 'x-data="tagPicker"' in html
    assert 'src="js/codebook.js"' in html
    assert 'src="js/tags.js"' in html
    assert "tag_catalog" in (SITE / "js" / "tags.js").read_text(encoding="utf-8")
    index = (SITE / "index.html").read_text(encoding="utf-8")
    projects = (SITE / "projects.html").read_text(encoding="utf-8")
    assert 'href="tags.html"' in index
    assert 'class="stub" href="tags.html"' not in index
    assert 'class="stub" href="tags.html"' not in projects


def test_site_codebook_json_embeds_catalog():
    payload = __import__("json").loads(
        (SITE / "data" / "codebook.json").read_text(encoding="utf-8")
    )
    assert payload["tag_catalog"]
    assert all("hashtag" in e for e in payload["tag_catalog"])
