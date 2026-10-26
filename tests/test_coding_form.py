"""Coding view form helpers + page wiring (schema-driven, 12f)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from open_research_tagging.codebook import load_codebook_file
from open_research_tagging.codebook_emit import emit_codebook_json

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
FORM_JS = SITE / "js" / "coding_form.js"
CODING_HTML = SITE / "coding.html"
CODEBOOK_YAML = REPO / "codebook" / "codebook.yaml"


def test_coding_page_wires_schema_form():
    html = CODING_HTML.read_text(encoding="utf-8")
    assert "coding-form" in html or 'id="coding-form"' in html
    assert "schemaDimensions" in html
    assert "coding_form.js" in html
    assert "section-evidence-btn" in html
    assert FORM_JS.is_file()
    src = FORM_JS.read_text(encoding="utf-8")
    assert "emptyCoding" in src
    assert "prefillCoding" in src
    assert "coding_schema" in src or "schemaFrom" in src


def _codebook_json() -> dict:
    return emit_codebook_json(load_codebook_file(CODEBOOK_YAML))


def _run_node(script: str, codebook: dict | None = None) -> str:
    if not FORM_JS.is_file():
        pytest.fail(f"missing {FORM_JS}")
    cb = codebook if codebook is not None else _codebook_json()
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
const codebook = {json.dumps(cb)};
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
const empty = F.emptyCoding(codebook);
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
const filled = F.prefillCoding(raw, codebook);
if (filled.stance.explicit !== 'permissive-with-conditions') throw new Error('pref stance');
if (filled.scope.explicit.code !== 'restricted') throw new Error('pref scope');
if (filled.scope.explicit.docs_and_text !== 'restricted') throw new Error('pref docs');
if (filled.stated_rationale.explicit[0] !== 'security') throw new Error('pref rat');
if (filled.accountability.explicit.disclosure_format[0] !== 'free-text') throw new Error('pref df');
if (filled.context.explicit.notes !== 'n') throw new Error('pref notes');

const fromNull = F.prefillCoding(null, codebook);
if (fromNull.stance.explicit !== null) throw new Error('null pref');
const fromEmpty = F.prefillCoding({}, codebook);
if (fromEmpty.accountability.explicit.disclosure !== 'none') throw new Error('empty pref');
console.log('ok');
"""
    )
    assert out == "ok"


def test_toggle_multi_and_evidence_from_schema():
    out = _run_node(
        r"""
let list = [];
list = F.toggleMulti(list, 'a', true);
list = F.toggleMulti(list, 'b', true);
list = F.toggleMulti(list, 'a', false);
if (list.join(',') !== 'b') throw new Error('toggle: ' + list);
const y = F.yamlScopeKey('docs-and-text');
if (y !== 'docs_and_text') throw new Error('yaml key');
if (F.evidenceDimForSection('stance', codebook) !== 'stance') throw new Error('ev stance');
if (F.evidenceDimForSection('context', codebook) !== '') throw new Error('ev context');
console.log('ok');
"""
    )
    assert out == "ok"
