"""Coding view shell (10a): resolve ?project= and empty states."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
HELPERS = SITE / "js" / "coding_resolve.js"
CODING_JS = SITE / "js" / "coding.js"
CODING_HTML = SITE / "coding.html"


def test_coding_page_wires_shell_and_modules():
    html = CODING_HTML.read_text(encoding="utf-8")
    assert 'href="css/site.css"' in html
    assert "alpinejs" in html.lower()
    assert 'x-data="codingView"' in html
    assert 'src="js/coding_resolve.js"' in html
    assert 'src="js/coding.js"' in html
    assert 'id="coding-empty"' in html or "empty" in html.lower()
    assert 'href="coding.html"' in (SITE / "projects.html").read_text(encoding="utf-8")
    # Real nav link, not stub-only
    for name in ("index.html", "projects.html", "tags.html"):
        page = (SITE / name).read_text(encoding="utf-8")
        assert 'class="stub" href="coding.html"' not in page


def _run_node(script: str) -> str:
    if not HELPERS.is_file():
        pytest.fail(f"missing {HELPERS}")
    prelude = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync({json.dumps(str(HELPERS))}, 'utf8');
const sandbox = {{ console, URLSearchParams }};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const R = sandbox.OrtCodingResolve;
if (!R) throw new Error('OrtCodingResolve missing');
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


def test_resolve_project_missing_unknown_and_hit():
    out = _run_node(
        r"""
const projects = [
  { slug: 'pyopensci', display_name: 'pyOpenSci' },
  { slug: 'other', display_name: 'Other' },
];
const comments = [
  { project: 'pyopensci', id: 1 },
  { project: 'pyopensci', id: 2 },
  { project: 'other', id: 3 },
];

let r = R.resolveCodingView(new URLSearchParams(''), projects, comments);
if (r.state !== 'missing') throw new Error('missing');
if (r.project !== null) throw new Error('no project');

r = R.resolveCodingView(new URLSearchParams('project=nope'), projects, comments);
if (r.state !== 'unknown') throw new Error('unknown');
if (r.slug !== 'nope') throw new Error('slug');

r = R.resolveCodingView(new URLSearchParams('project=pyopensci'), projects, comments);
if (r.state !== 'ready') throw new Error('ready');
if (r.project.display_name !== 'pyOpenSci') throw new Error('name');
if (r.comments.length !== 2) throw new Error('comments');
console.log('ok');
"""
    )
    assert out == "ok"


def test_coding_js_registers_alpine_component():
    js = CODING_JS.read_text(encoding="utf-8")
    assert "alpine:init" in js
    assert "codingView" in js
    assert "OrtCodingResolve" in js


def test_resolve_empty_project_list_unknown():
    out = _run_node(
        r"""
const r = R.resolveCodingView(
  new URLSearchParams('project=pyopensci'),
  [],
  [{ project: 'pyopensci', id: 1 }]
);
if (r.state !== 'unknown') throw new Error(r.state);
if (r.comments.length !== 0) throw new Error('no comments without project');
console.log('ok');
"""
    )
    assert out == "ok"
