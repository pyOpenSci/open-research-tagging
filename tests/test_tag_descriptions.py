"""13d: tag catalog descriptions + picker search/UI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from open_research_tagging.codebook import load_codebook
from open_research_tagging.tag_catalog import canonical_tag_entries

REPO = Path(__file__).resolve().parents[1]
CODEBOOK_YAML = REPO / "codebook" / "codebook.yaml"
SITE = REPO / "site"
HELPERS_JS = SITE / "js" / "tags_stage.js"
TAGS_HTML = SITE / "tags.html"


@pytest.fixture
def codebook():
    return load_codebook(CODEBOOK_YAML)


def test_stance_ban_catalog_entry_includes_description(codebook):
    entries = {e["hashtag"]: e for e in canonical_tag_entries(codebook)}
    ban = entries["#stance/ban"]
    assert "description" in ban
    assert "prohibited" in ban["description"].lower()


def test_rationale_falls_back_to_leaf_description_when_value_has_none(codebook):
    entries = {e["hashtag"]: e for e in canonical_tag_entries(codebook)}
    row = entries["#rationale/code-quality"]
    assert row["description"]
    assert "policy states" in row["description"].lower() or "stated" in row[
        "description"
    ].lower()


def test_tags_page_shows_definition_line():
    html = TAGS_HTML.read_text(encoding="utf-8")
    assert "tag-definition" in html
    assert "Definition:" in html
    assert "tag.description" in html
    assert "<details" not in html
    search = html[html.find("tag-search") : html.find("tag-search") + 200]
    assert "definition" in search.lower() or "description" in search.lower()


def _run_node(script: str) -> str:
    prelude = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync({json.dumps(str(HELPERS_JS))}, 'utf8');
const sandbox = {{ console }};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const S = sandbox.OrtTagsStage;
if (!S) throw new Error('OrtTagsStage missing');
"""
    proc = subprocess.run(
        ["node", "-e", prelude + script],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.fail(proc.stderr or proc.stdout or f"exit {proc.returncode}")
    return proc.stdout.strip()


def test_tag_matches_query_includes_description():
    out = _run_node(
        r"""
const tag = {
  hashtag: '#stance/ban',
  label: 'Ban',
  namespace: 'stance',
  dimension: 'stance',
  dimension_label: 'Stance',
  description: 'AI-generated contributions prohibited',
};
if (!S.tagMatchesQuery(tag, 'prohibited')) throw new Error('desc');
if (S.tagMatchesQuery(tag, 'zzz-nope')) throw new Error('miss');
console.log('ok');
"""
    )
    assert out == "ok"
