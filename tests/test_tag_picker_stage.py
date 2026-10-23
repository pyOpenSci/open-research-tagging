"""Tag picker search + staging helpers (9b)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"
HELPERS_JS = SITE / "js" / "tags_stage.js"
TAGS_JS = SITE / "js" / "tags.js"
TAGS_HTML = SITE / "tags.html"


def test_tags_page_wires_search_and_staged_panel():
    html = TAGS_HTML.read_text(encoding="utf-8")
    assert 'id="tag-search"' in html
    assert 'id="staged-list"' in html or "staged" in html
    assert 'src="js/tags_stage.js"' in html
    assert "Shell page" not in html
    js = TAGS_JS.read_text(encoding="utf-8")
    assert "OrtTagsStage" in js
    assert "stageTag" in js or "addTag" in js
    assert "tagMatchesQuery" in HELPERS_JS.read_text(encoding="utf-8")


def _run_node(script: str) -> str:
    if not HELPERS_JS.is_file():
        pytest.fail(f"missing {HELPERS_JS}")
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
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.fail(proc.stderr or proc.stdout or f"exit {proc.returncode}")
    return proc.stdout.strip()


def test_tag_matches_query_fields_and_empty():
    out = _run_node(
        r"""
const tag = {
  hashtag: '#stance/allow',
  label: 'Allow',
  namespace: 'stance',
  dimension: 'stance',
  dimension_label: 'Stance',
};
if (!S.tagMatchesQuery(tag, '')) throw new Error('empty');
if (!S.tagMatchesQuery(tag, '  ')) throw new Error('blank');
if (!S.tagMatchesQuery(tag, 'ALLOW')) throw new Error('label');
if (!S.tagMatchesQuery(tag, 'stance/allow')) throw new Error('hashtag');
if (!S.tagMatchesQuery(tag, 'Stance')) throw new Error('dim label');
if (S.tagMatchesQuery(tag, 'zzz-nope')) throw new Error('miss');
console.log('ok');
"""
    )
    assert out == "ok"


def test_filter_catalog_hides_non_matches():
    out = _run_node(
        r"""
const catalog = [
  { hashtag: '#stance/allow', label: 'Allow', namespace: 'stance',
    dimension: 'stance', dimension_label: 'Stance' },
  { hashtag: '#disclosure/required', label: 'Required', namespace: 'disclosure',
    dimension: 'disclosure', dimension_label: 'Disclosure' },
];
const filtered = S.filterCatalog(catalog, 'disclos');
if (filtered.length !== 1 || filtered[0].hashtag !== '#disclosure/required') {
  throw new Error(JSON.stringify(filtered));
}
if (S.filterCatalog(catalog, '').length !== 2) throw new Error('all');
console.log('ok');
"""
    )
    assert out == "ok"


def test_stage_dedupe_remove_clear():
    out = _run_node(
        r"""
const a = { hashtag: '#stance/allow', label: 'Allow' };
const b = { hashtag: '#disclosure/required', label: 'Required' };
let staged = [];
staged = S.stageTag(staged, a);
staged = S.stageTag(staged, b);
staged = S.stageTag(staged, a); // dedupe
if (staged.length !== 2) throw new Error('dedupe ' + staged.length);
if (staged[0].hashtag !== '#stance/allow') throw new Error('order');
staged = S.removeStaged(staged, '#stance/allow');
if (staged.length !== 1 || staged[0].hashtag !== '#disclosure/required') {
  throw new Error('remove');
}
staged = S.clearStaged(staged);
if (staged.length !== 0) throw new Error('clear');
staged = S.stageTag(staged, null);
staged = S.stageTag(staged, {});
if (staged.length !== 0) throw new Error('bad tag');
console.log('ok');
"""
    )
    assert out == "ok"


def test_group_by_dimension_skips_empty_after_filter():
    out = _run_node(
        r"""
const catalog = [
  { hashtag: '#stance/allow', label: 'Allow', dimension: 'stance',
    dimension_label: 'Stance', namespace: 'stance' },
  { hashtag: '#disclosure/required', label: 'Required', dimension: 'disclosure',
    dimension_label: 'Disclosure', namespace: 'disclosure' },
];
const filtered = S.filterCatalog(catalog, 'allow');
const groups = S.groupByDimension(filtered);
if (groups.length !== 1 || groups[0].dimension !== 'stance') {
  throw new Error(JSON.stringify(groups));
}
console.log('ok');
"""
    )
    assert out == "ok"
