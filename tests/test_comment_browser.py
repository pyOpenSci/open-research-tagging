"""Comment browser (8b): page wiring + pure filter/URL helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"
FILTERS_JS = SITE / "js" / "comments_filters.js"
COMMENTS_JS = SITE / "js" / "comments.js"
INDEX = SITE / "index.html"


def test_comment_browser_page_wires_controls_and_modules():
    html = INDEX.read_text(encoding="utf-8")
    assert 'href="css/site.css"' in html
    assert 'src="js/codebook.js"' in html
    assert 'src="js/comments_filters.js"' in html
    assert 'src="js/comments.js"' in html
    assert "alpinejs" in html.lower()
    assert 'x-data="commentBrowser"' in html
    assert 'id="fixture-banner"' in html
    assert 'id="url-filter-banner"' in html
    assert 'id="filter-tag-review"' in html
    assert 'id="clear-filters"' in html
    assert 'id="dim-filters"' in html
    assert 'id="q"' in html
    assert 'id="project"' in html
    assert 'id="pr"' in html
    assert 'id="commentstable"' in html
    assert "datatables.net" in html.lower()
    assert "FILTER_DIMS" not in html
    assert "Shell page for shared assets" not in html


def test_comments_filter_module_files_exist():
    assert FILTERS_JS.is_file()
    assert COMMENTS_JS.is_file()
    filters = FILTERS_JS.read_text(encoding="utf-8")
    assert "parseUrlFilters" in filters
    assert "rowMatchesFilters" in filters
    assert "valueChipsForDimension" in filters
    assert "OrtCommentsFilters" in filters
    comments = COMMENTS_JS.read_text(encoding="utf-8")
    assert "OrtCommentsFilters" in comments
    assert "alpine:init" in comments
    assert "commentBrowser" in comments
    assert "is_fixture" in comments
    assert "needs_tag_review" in comments


def _run_filter_node(script: str) -> str:
    """Load comments_filters.js in Node and run an assertion script."""
    if not FILTERS_JS.is_file():
        pytest.fail(f"missing {FILTERS_JS}")
    prelude = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync({json.dumps(str(FILTERS_JS))}, 'utf8');
const sandbox = {{ console, URLSearchParams }};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const F = sandbox.OrtCommentsFilters;
if (!F) throw new Error('OrtCommentsFilters missing');
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


def test_parse_url_filters_project_filter_and_review():
    out = _run_filter_node(
        r"""
const u = new URLSearchParams('project=pyopensci&filter=stance:allow&needs_tag_review=1');
const parsed = F.parseUrlFilters(u);
if (parsed.project !== 'pyopensci') throw new Error('project');
if (parsed.needsTagReview !== true) throw new Error('review');
if (!parsed.activeByDim.stance || !parsed.activeByDim.stance.has('stance:allow')) {
  throw new Error('filter key');
}
console.log('ok');
"""
    )
    assert out == "ok"


def test_parse_url_filters_dimension_any_and_scope_pair():
    out = _run_filter_node(
        r"""
const u = new URLSearchParams('project=demo&dimension=stance');
let parsed = F.parseUrlFilters(u);
if (!parsed.activeByDim.stance.has('dimension-any:stance')) throw new Error('dim-any');

const u2 = new URLSearchParams('scope_type=code&scope_position=restricted');
parsed = F.parseUrlFilters(u2);
if (!parsed.activeByDim.scope.has('scope:code:restricted')) throw new Error('scope pair');
console.log('ok');
"""
    )
    assert out == "ok"


def test_row_matches_filters_and_or_semantics():
    """OR within a dimension, AND across dimensions; project/PR/review gates."""
    out = _run_filter_node(
        r"""
const rowA = {
  project: 'demo',
  pr_number: 1,
  needs_tag_review: false,
  filter_keys: ['stance:allow', 'disclosure:required'],
  tags: [
    { dimension: 'stance', kind: 'value' },
    { dimension: 'disclosure', kind: 'value' },
  ],
};
const rowB = {
  project: 'other',
  pr_number: 2,
  needs_tag_review: true,
  filter_keys: ['stance:forbid'],
  tags: [{ dimension: 'stance', kind: 'value' }],
};

const active = { stance: new Set(['stance:allow', 'stance:forbid']) };
if (!F.rowMatchesFilters(rowA, { activeByDim: active })) throw new Error('OR allow');
if (!F.rowMatchesFilters(rowB, { activeByDim: active })) throw new Error('OR forbid');

active.disclosure = new Set(['disclosure:required']);
if (!F.rowMatchesFilters(rowA, { activeByDim: active })) throw new Error('AND ok');
if (F.rowMatchesFilters(rowB, { activeByDim: active })) throw new Error('AND fail');

if (F.rowMatchesFilters(rowA, { project: 'other', activeByDim: {} })) {
  throw new Error('project gate');
}
if (!F.rowMatchesFilters(rowB, { onlyTagReview: true, activeByDim: {} })) {
  throw new Error('review gate');
}
if (F.rowMatchesFilters(rowA, { onlyTagReview: true, activeByDim: {} })) {
  throw new Error('review exclude');
}

const dimAny = { stance: new Set(['dimension-any:stance']) };
if (!F.rowMatchesFilters(rowA, { activeByDim: dimAny })) throw new Error('dim-any');

const empty = { project: 'missing', activeByDim: {} };
if (F.rowMatchesFilters(rowA, empty)) throw new Error('empty project');
console.log('ok');
"""
    )
    assert out == "ok"


def test_row_matches_scope_partial_and_full():
    out = _run_filter_node(
        r"""
const row = {
  project: 'demo',
  pr_number: 1,
  needs_tag_review: false,
  filter_keys: ['scope:code:restricted'],
  tags: [{
    kind: 'scope',
    dimension: 'scope',
    contribution_type: 'code',
    position: 'restricted',
  }],
};
const full = { scope: new Set(['scope:code:restricted']) };
if (!F.rowMatchesFilters(row, { activeByDim: full })) throw new Error('full');

const partialType = { scope: new Set(['scope-partial:code:*']) };
if (!F.rowMatchesFilters(row, { activeByDim: partialType })) throw new Error('partial type');

const partialPos = { scope: new Set(['scope-partial:*:restricted']) };
if (!F.rowMatchesFilters(row, { activeByDim: partialPos })) throw new Error('partial pos');

const miss = { scope: new Set(['scope:docs:restricted']) };
if (F.rowMatchesFilters(row, { activeByDim: miss })) throw new Error('miss');
console.log('ok');
"""
    )
    assert out == "ok"


def test_deep_link_shapes_from_build_project_appear_in_comments_js():
    """Phase 5 hrefs must be understood by the browser URL parser."""
    src = FILTERS_JS.read_text(encoding="utf-8")
    for needle in (
        "project",
        "dimension",
        "filter",
        "scope_type",
        "scope_position",
        "needs_tag_review",
        "dimension-any:",
        "scope-partial:",
    ):
        assert needle in src


def test_parse_url_filters_empty_and_unknown_filter_key():
    out = _run_filter_node(
        r"""
const empty = F.parseUrlFilters(new URLSearchParams(''));
if (empty.project !== null) throw new Error('project null');
if (empty.needsTagReview !== false) throw new Error('review false');
if (Object.keys(empty.activeByDim).length !== 0) throw new Error('no dims');

const weird = F.parseUrlFilters(new URLSearchParams('filter=not-a-pair'));
if (Object.keys(weird.activeByDim).length !== 0) throw new Error('ignore bad filter');

const unknown = F.parseUrlFilters(
  new URLSearchParams('filter=stance:does-not-exist-in-data')
);
if (!unknown.activeByDim.stance.has('stance:does-not-exist-in-data')) {
  throw new Error('unknown key still applied');
}
const row = {
  project: 'demo',
  filter_keys: ['stance:allow'],
  tags: [{ dimension: 'stance', kind: 'value' }],
};
if (F.rowMatchesFilters(row, { activeByDim: unknown.activeByDim })) {
  throw new Error('unknown key should not match');
}
if (!F.rowMatchesFilters(row, { activeByDim: {} })) throw new Error('empty active');
console.log('ok');
"""
    )
    assert out == "ok"


def test_row_matches_empty_tags_and_pr_gate():
    out = _run_filter_node(
        r"""
const bare = {
  project: 'demo',
  pr_number: 9,
  needs_tag_review: false,
  filter_keys: [],
  tags: [],
};
if (!F.rowMatchesFilters(bare, { activeByDim: {} })) throw new Error('bare ok');
if (F.rowMatchesFilters(bare, { pr: '8', activeByDim: {} })) throw new Error('pr');
if (!F.rowMatchesFilters(bare, { pr: '9', activeByDim: {} })) throw new Error('pr ok');

const dimAny = { stance: new Set(['dimension-any:stance']) };
if (F.rowMatchesFilters(bare, { activeByDim: dimAny })) throw new Error('no dim');
console.log('ok');
"""
    )
    assert out == "ok"


def test_describe_url_filters_bits():
    out = _run_filter_node(
        r"""
const bits = F.describeUrlFilters(
  new URLSearchParams('project=demo&dimension=stance&needs_tag_review=1')
);
if (bits.indexOf('project=demo') < 0) throw new Error('project bit');
if (bits.indexOf('all stance') < 0) throw new Error('dim bit');
if (bits.indexOf('needs_tag_review') < 0) throw new Error('review bit');
if (F.describeUrlFilters(new URLSearchParams('')).length !== 0) {
  throw new Error('empty');
}
console.log('ok');
"""
    )
    assert out == "ok"


def test_value_chips_and_scope_options_helpers():
    out = _run_filter_node(
        r"""
const rows = [
  {
    filter_keys: ['stance:allow', 'scope:code:restricted'],
    tags: [
      { kind: 'value', dimension: 'stance' },
      { kind: 'scope', contribution_type: 'code', position: 'restricted' },
    ],
  },
  {
    filter_keys: ['stance:allow'],
    tags: [{ kind: 'value', dimension: 'stance' }],
  },
];
const chips = F.valueChipsForDimension(rows, 'stance', {
  allow: 'Allow',
  forbid: 'Forbid',
});
if (chips.length !== 1 || chips[0].id !== 'allow' || chips[0].count !== 2) {
  throw new Error('chips ' + JSON.stringify(chips));
}
const types = F.appearingScopeOptions(
  rows,
  'contribution_type',
  { code: 'Code', docs: 'Docs' }
);
if (types.length !== 1 || types[0].id !== 'code') throw new Error('types');
const empty = F.valueChipsForDimension([], 'stance', { allow: 'Allow' });
if (empty.length !== 0) throw new Error('empty chips');

const sets = { stance: new Set(['stance:allow']) };
const arrays = F.activeSetsToArrays(sets);
if (arrays.stance[0] !== 'stance:allow') throw new Error('to arrays');
const back = F.activeArraysToSets(arrays);
if (!back.stance.has('stance:allow')) throw new Error('to sets');
console.log('ok');
"""
    )
    assert out == "ok"
