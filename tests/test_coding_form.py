"""Coding view form helpers + page wiring (10c)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
FORM_JS = SITE / "js" / "coding_form.js"
CODING_HTML = SITE / "coding.html"


def test_coding_page_wires_form_sections():
    html = CODING_HTML.read_text(encoding="utf-8")
    assert "coding-form" in html or 'id="coding-form"' in html
    for needle in (
        "stance",
        "scope",
        "stated_rationale",
        "guidance_on_use",
        "accountability",
        "context",
    ):
        assert needle in html
    assert "coding_form.js" in html
    assert "section-evidence-btn" in html
    assert "focusSection(" in html
    assert FORM_JS.is_file()
    src = FORM_JS.read_text(encoding="utf-8")
    assert "emptyCoding" in src
    assert "prefillCoding" in src
    assert "evidenceDimForSection" in src


def _run_node(script: str) -> str:
    if not FORM_JS.is_file():
        pytest.fail(f"missing {FORM_JS}")
    prelude = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync({json.dumps(str(FORM_JS))}, 'utf8');
const sandbox = {{ console }};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const F = sandbox.OrtCodingForm;
if (!F) throw new Error('OrtCodingForm missing');
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


def test_empty_coding_defaults_and_prefill():
    out = _run_node(
        r"""
const empty = F.emptyCoding();
if (empty.stance.explicit !== null) throw new Error('stance');
if (!empty.scope.explicit || empty.scope.explicit.code !== 'not_addressed') {
  throw new Error('scope');
}
if (!Array.isArray(empty.stated_rationale.explicit) || empty.stated_rationale.explicit.length !== 0) {
  throw new Error('rationale');
}
if (empty.guidance_on_use.explicit.level !== null) throw new Error('glevel');
if (empty.accountability.explicit.disclosure !== 'none') throw new Error('disclosure');
if (empty.context.explicit.notes !== '') throw new Error('notes');

const raw = {
  stance: 'permissive-with-conditions',
  scope: { code: 'restricted', tests: 'not_addressed', docs_and_text: 'restricted' },
  stated_rationale: ['security'],
  guidance_on_use: { level: 'some-guidance', types: ['design'] },
  accountability: {
    human_responsibility: 'yes',
    disclosure: 'required',
    disclosure_format: ['free-text'],
    enforcement: ['other'],
  },
  context: { governance: 'community', domain: 'sci', project_size: 'big', notes: 'n' },
};
const filled = F.prefillCoding(raw);
if (filled.stance.explicit !== 'permissive-with-conditions') throw new Error('pref stance');
if (filled.scope.explicit.code !== 'restricted') throw new Error('pref scope');
if (filled.scope.explicit.docs_and_text !== 'restricted') throw new Error('pref docs');
if (filled.stated_rationale.explicit[0] !== 'security') throw new Error('pref rat');
if (filled.accountability.explicit.disclosure_format[0] !== 'free-text') throw new Error('pref df');
if (filled.context.explicit.notes !== 'n') throw new Error('pref notes');

const fromNull = F.prefillCoding(null);
if (fromNull.stance.explicit !== null) throw new Error('null pref');
const fromEmpty = F.prefillCoding({});
if (fromEmpty.accountability.explicit.disclosure !== 'none') throw new Error('empty pref');
console.log('ok');
"""
    )
    assert out == "ok"


def test_toggle_multi_and_scope_key_helpers():
    out = _run_node(
        r"""
let list = [];
list = F.toggleMulti(list, 'a', true);
list = F.toggleMulti(list, 'b', true);
list = F.toggleMulti(list, 'a', false);
if (list.join(',') !== 'b') throw new Error('toggle: ' + list);
const y = F.yamlScopeKey('docs-and-text');
if (y !== 'docs_and_text') throw new Error('yaml key');
const h = F.hashtagScopeKey('docs_and_text');
if (h !== 'docs-and-text') throw new Error('hash key');
if (F.evidenceDimForSection('stance') !== 'stance') throw new Error('ev stance');
if (F.evidenceDimForSection('context') !== '') throw new Error('ev context');
if (F.valueOptions(null, 'stance').length !== 0) throw new Error('opts null');
if (F.valueOptions({ values: { stance: { ban: 'Ban' } } }, 'stance')[0].id !== 'ban') {
  throw new Error('opts');
}
console.log('ok');
"""
    )
    assert out == "ok"
