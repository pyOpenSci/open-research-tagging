"""Projects overview (8c): page wiring + pure overall-code filter helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"
FILTERS_JS = SITE / "js" / "projects_filters.js"
PROJECTS_JS = SITE / "js" / "projects.js"
PAGE = SITE / "projects.html"
PROJECTS_JSON = SITE / "data" / "projects.json"


def test_projects_page_wires_alpine_table_and_modules():
    html = PAGE.read_text(encoding="utf-8")
    assert 'href="css/site.css"' in html
    assert 'src="js/codebook.js"' in html
    assert 'src="js/projects_filters.js"' in html
    assert 'src="js/projects.js"' in html
    assert "alpinejs" in html.lower()
    assert 'x-data="projectsOverview"' in html
    assert 'id="projectstable"' in html
    assert 'id="dim-filters"' in html
    assert 'id="clear-filters"' in html
    assert "datatables.net" in html.lower()
    assert "FILTER_DIMS" not in html
    assert "Shell page proving" not in html
    assert 'href="tags.html"' in html
    assert 'href="coding.html"' in html


def test_projects_modules_exist_and_avoid_hardcoded_filter_dims():
    assert FILTERS_JS.is_file()
    assert PROJECTS_JS.is_file()
    filters = FILTERS_JS.read_text(encoding="utf-8")
    assert "FILTER_DIMS" not in filters
    assert "projectMatchesFilters" in filters
    assert "codesPresent" in filters
    assert "OrtProjectsFilters" in filters
    projects = PROJECTS_JS.read_text(encoding="utf-8")
    assert "FILTER_DIMS" not in projects
    assert "alpine:init" in projects
    assert "projectsOverview" in projects
    assert "OrtCodebook" in projects


def _run_filter_node(script: str) -> str:
    if not FILTERS_JS.is_file():
        pytest.fail(f"missing {FILTERS_JS}")
    prelude = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync({json.dumps(str(FILTERS_JS))}, 'utf8');
const sandbox = {{ console }};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const F = sandbox.OrtProjectsFilters;
if (!F) throw new Error('OrtProjectsFilters missing');
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


def test_project_matches_filters_or_within_and_across_dims():
    out = _run_filter_node(
        r"""
const rowA = {
  overall: {
    stance: { values: [{ id: 'allow', label: 'Allow' }] },
    disclosure: { values: [{ id: 'required', label: 'Required' }] },
  },
};
const rowB = {
  overall: {
    stance: { values: [{ id: 'forbid', label: 'Forbid' }] },
  },
};
const active = { stance: ['allow', 'forbid'] };
if (!F.projectMatchesFilters(rowA, active)) throw new Error('OR allow');
if (!F.projectMatchesFilters(rowB, active)) throw new Error('OR forbid');
active.disclosure = ['required'];
if (!F.projectMatchesFilters(rowA, active)) throw new Error('AND ok');
if (F.projectMatchesFilters(rowB, active)) throw new Error('AND fail');
if (!F.projectMatchesFilters(rowA, {})) throw new Error('empty');
console.log('ok');
"""
    )
    assert out == "ok"


def test_codes_present_counts_labels_from_rows():
    out = _run_filter_node(
        r"""
const rows = [
  { overall: { stance: { values: [{ id: 'allow', label: 'Allow' }] } } },
  { overall: { stance: { values: [{ id: 'allow', label: 'Allow' }] } } },
  { overall: { stance: { values: [{ id: 'forbid', label: 'Forbid' }] } } },
];
const present = F.codesPresent(rows, 'stance');
if (present.allow.count !== 2) throw new Error('allow count');
if (present.forbid.label !== 'Forbid') throw new Error('label');
if (Object.keys(F.codesPresent(rows, 'missing')).length !== 0) {
  throw new Error('missing dim');
}
if (Object.keys(F.codesPresent([], 'stance')).length !== 0) throw new Error('empty');
console.log('ok');
"""
    )
    assert out == "ok"


def test_seed_projects_json_has_evidence_hrefs_for_browser():
    payload = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
    assert payload["data"]
    row = payload["data"][0]
    stance = row["overall"]["stance"]["values"][0]
    links = stance["links"]
    assert "index.html?project=" in links["all"]["href"]
    assert "dimension=" in links["all"]["href"]
    assert "filter=" in links["matching"]["href"]
    scope = row["overall"]["scope"]["values"][0]
    assert "scope_type=" in scope["links"]["matching"]["href"]
    assert "scope_position=" in scope["links"]["matching"]["href"]


def test_projects_js_renders_evidence_pop_links():
    src = PROJECTS_JS.read_text(encoding="utf-8")
    assert "code-pill" in src
    assert "links.all" in src or "links.matching" in src or "matching" in src
    assert "comments_href" in src
