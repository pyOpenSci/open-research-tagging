"""Coding view evidence filter helpers (10b)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
HELPERS = SITE / "js" / "coding_resolve.js"
CODING_HTML = SITE / "coding.html"


def test_coding_page_wires_evidence_pane():
    html = CODING_HTML.read_text(encoding="utf-8")
    assert 'id="evidence-dim"' in html or "evidenceDim" in html
    assert "evidence" in html.lower()
    assert "commentsForDimension" in HELPERS.read_text(encoding="utf-8")


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


def test_comments_for_dimension_all_and_filter():
    out = _run_node(
        r"""
const comments = [
  { id: 1, tags: [{ dimension: 'stance' }], quote: 'a' },
  { id: 2, tags: [{ dimension: 'scope' }], quote: 'b' },
  { id: 3, tags: [{ dimension: 'stance' }, { dimension: 'disclosure' }], quote: 'c' },
  { id: 4, tags: [], quote: 'd' },
];
const all = R.commentsForDimension(comments, null);
if (all.length !== 4) throw new Error('all');
const stance = R.commentsForDimension(comments, 'stance');
if (stance.length !== 2 || stance[0].id !== 1) throw new Error('stance');
const empty = R.commentsForDimension(comments, 'enforcement');
if (empty.length !== 0) throw new Error('empty');
const none = R.commentsForDimension([], 'stance');
if (none.length !== 0) throw new Error('none');
console.log('ok');
"""
    )
    assert out == "ok"


def test_evidence_excerpt_prefers_quote_and_truncates():
    out = _run_node(
        r"""
const short = R.evidenceExcerpt({ quote: '  hello   world  ' });
if (short !== 'hello world') throw new Error('quote normalize: ' + short);
const longQ = 'x'.repeat(200);
const trunc = R.evidenceExcerpt({ quote: longQ }, 40);
if (trunc.length !== 40 || !trunc.endsWith('…')) throw new Error('trunc');
const fromBody = R.evidenceExcerpt({
  body: '#stance/allow\nFirst line of evidence.\n#scope/code:open',
});
if (!fromBody.includes('First line') || fromBody.includes('#')) {
  throw new Error('body strip: ' + fromBody);
}
if (R.evidenceExcerpt(null) !== '') throw new Error('null');
if (R.evidenceExcerpt({}) !== '') throw new Error('empty');
console.log('ok');
"""
    )
    assert out == "ok"
