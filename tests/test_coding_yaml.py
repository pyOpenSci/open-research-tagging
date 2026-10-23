"""Emit coding: YAML block for coding-view Copy (10d). Python is the contract."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from open_research_tagging.coding_yaml import emit_coding_block

REPO = Path(__file__).resolve().parents[1]
FORM_JS = REPO / "site" / "js" / "coding_form.js"
CODING_HTML = REPO / "site" / "coding.html"

SAMPLE = {
    "stance": "permissive-with-conditions",
    "scope": {
        "code": "restricted",
        "tests": "restricted",
        "docs_and_text": "restricted",
        "issues_and_pr_descriptions": "restricted",
        "review": "not_addressed",
        "autonomous_agents": "not_addressed",
        "contribution_types_not_defined": "not_addressed",
    },
    "stated_rationale": [
        "code-quality",
        "maintainer-and-reviewer-burden",
        "social-and-ethical",
    ],
    "guidance_on_use": {
        "level": "substantive-guidance",
        "types": ["scoping", "design", "evaluation", "iteration"],
    },
    "accountability": {
        "human_responsibility": "yes",
        "disclosure": "required",
        "disclosure_format": ["free-text"],
        "enforcement": ["contributor-blocked", "other"],
    },
    "context": {
        "project_size": "Peer-review org for scientific Python packages; size not coded for demo",
        "governance": "community",
        "domain": "scientific Python / peer review",
        "notes": "Foundation-adjacent community; policy co-developed with community input.",
    },
}


def test_emit_coding_block_starts_with_coding_key():
    text = emit_coding_block(SAMPLE)
    assert text.startswith("coding:\n")
    assert "provenance:" not in text
    assert "files:" not in text
    parsed = yaml.safe_load(text)
    assert parsed["coding"]["stance"] == "permissive-with-conditions"
    # Quoted yes stays a string (or bool — coerce handles either)
    hr = parsed["coding"]["accountability"]["human_responsibility"]
    assert hr in ("yes", True)


def test_emit_coding_block_empty_and_none():
    text = emit_coding_block(None)
    assert text.startswith("coding:\n")
    parsed = yaml.safe_load(text)
    assert parsed["coding"]["stance"] is None
    assert parsed["coding"]["stated_rationale"] == []
    assert emit_coding_block({}) == text


def test_emit_round_trips_yaml_shape():
    text = emit_coding_block(SAMPLE)
    coding = yaml.safe_load(text)["coding"]
    assert coding["scope"]["code"] == "restricted"
    assert coding["guidance_on_use"]["types"] == [
        "scoping",
        "design",
        "evaluation",
        "iteration",
    ]
    assert coding["context"]["governance"] == "community"
    # Empty list still present for paste into template-shaped files
    empty = yaml.safe_load(emit_coding_block({}))["coding"]
    assert empty["stated_rationale"] == []
    assert empty["accountability"]["disclosure"] == "none"


def test_coding_page_wires_copy_yaml():
    html = CODING_HTML.read_text(encoding="utf-8")
    assert "copy-yaml" in html or "copyYaml" in html or "Copy YAML" in html
    src = FORM_JS.read_text(encoding="utf-8")
    assert "emitCodingYaml" in src


def _run_js_emit(coding: dict) -> str:
    if not FORM_JS.is_file():
        pytest.fail(f"missing {FORM_JS}")
    script = f"""
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync({json.dumps(str(FORM_JS))}, 'utf8');
const sandbox = {{ console }};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const F = sandbox.OrtCodingForm;
if (!F || !F.emitCodingYaml) throw new Error('emitCodingYaml missing');
const text = F.emitCodingYaml({json.dumps(coding)});
process.stdout.write(text);
"""
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.fail(proc.stderr or proc.stdout or f"exit {proc.returncode}")
    return proc.stdout


def test_browser_emit_matches_python_golden():
    py = emit_coding_block(SAMPLE)
    js = _run_js_emit(SAMPLE)
    assert js == py


def test_browser_emit_matches_python_empty():
    assert _run_js_emit({}) == emit_coding_block({})
