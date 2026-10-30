"""12f: coding_schema emitted from codebook drives empty coding + form shape."""

from __future__ import annotations

import copy
from pathlib import Path

from open_research_tagging.codebook import load_codebook_file, validate_codebook
from open_research_tagging.codebook_emit import emit_codebook_json
from open_research_tagging.coding_schema import build_coding_schema, empty_coding_from_schema
from open_research_tagging.coding_yaml import empty_coding, emit_coding_block

from codebook_fixtures import REAL_CODEBOOK_PATH


def test_emit_includes_coding_schema_with_layers():
    raw = load_codebook_file(REAL_CODEBOOK_PATH)
    payload = emit_codebook_json(raw)
    schema = payload["coding_schema"]
    ids = [d["id"] for d in schema["dimensions"]]
    assert ids == [
        "stance",
        "scope",
        "stated_rationale",
        "guidance_on_use",
        "accountability",
        "context",
    ]
    stance = schema["dimensions"][0]
    layer_ids = [layer["id"] for layer in stance["layers"]]
    assert layer_ids == ["explicit", "implicit"]
    explicit_field = stance["layers"][0]["fields"][0]
    assert explicit_field["kind"] == "single"
    assert any(o["id"] == "ban" for o in explicit_field["options"])


def test_empty_coding_matches_schema_defaults():
    raw = load_codebook_file(REAL_CODEBOOK_PATH)
    schema = build_coding_schema(raw)
    from_schema = empty_coding_from_schema(schema)
    # Contract: coding_yaml.empty_coding uses the schema
    assert empty_coding() == from_schema
    assert from_schema["stance"]["explicit"] is None
    assert from_schema["stance"]["implicit"] == []
    assert from_schema["scope"]["explicit"]["code"] == "not-addressed"
    assert from_schema["scope"]["implicit"]["code"] == "not-seen"
    assert from_schema["accountability"]["explicit"]["disclosure"] == "none"


def test_template_coding_keys_align_with_schema():
    """_template coding skeleton should match schema dimension/layer keys."""
    import yaml

    raw = load_codebook_file(REAL_CODEBOOK_PATH)
    schema = build_coding_schema(raw)
    template_path = (
        Path(__file__).resolve().parents[1]
        / "projects"
        / "_template"
        / "project.yaml"
    )
    coding = yaml.safe_load(template_path.read_text(encoding="utf-8"))["coding"]
    for dim in schema["dimensions"]:
        assert dim["id"] in coding
        for layer in dim["layers"]:
            assert layer["id"] in coding[dim["id"]]


def test_new_context_text_field_appears_without_form_hardcoding():
    """Success check: YAML-only add shows up in schema + empty coding."""
    raw = load_codebook_file(REAL_CODEBOOK_PATH)
    mutated = copy.deepcopy(raw)
    fields = mutated["dimensions"]["context"]["implicit"]["fields"]
    fields.append(
        {
            "id": "schema_probe_field",
            "label": "Schema probe (test only)",
        }
    )
    validate_codebook(mutated)
    schema = build_coding_schema(mutated)
    ctx_impl = next(
        layer
        for layer in next(d for d in schema["dimensions"] if d["id"] == "context")[
            "layers"
        ]
        if layer["id"] == "implicit"
    )
    ids = [f["id"] for f in ctx_impl["fields"]]
    assert "schema_probe_field" in ids
    empty = empty_coding_from_schema(schema)
    assert "schema_probe_field" in empty["context"]["implicit"]
    assert empty["context"]["implicit"]["schema_probe_field"] == ""
    # Emit still round-trips the new key when given the mutated schema
    text = emit_coding_block(empty, schema=schema)
    assert "schema_probe_field:" in text
