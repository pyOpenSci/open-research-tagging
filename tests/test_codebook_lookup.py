"""Codebook lookup API: dimension / namespace / value id → label (soft miss)."""

from pathlib import Path

import pytest

from open_research_tagging.codebook import (
    Codebook,
    CodebookValidationError,
    load_codebook,
    validate_codebook,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_CODEBOOK = REPO_ROOT / "codebook" / "codebook.yaml"


def _minimal_codebook(**overrides):
    data = {
        "version": "test-0.1",
        "dimensions": {
            "stance": {
                "select": "single",
                "values": [
                    {"id": "ban", "label": "Ban"},
                    {"id": "allow", "label": "Allow"},
                ],
            },
            "stated_rationale": {
                "select": "multi",
                "values": [{"id": "security", "label": "Security"}],
            },
            "scope": {
                "select": "multi",
                "contribution_types": [{"id": "code", "label": "Code"}],
                "positions": ["allowed", "banned"],
            },
            "guidance_on_use": {
                "level": {
                    "select": "single",
                    "values": [{"id": "none", "label": "None"}],
                },
                "types": {
                    "select": "multi",
                    "values": [{"id": "design", "label": "Design"}],
                },
            },
            "accountability": {
                "disclosure": {
                    "select": "single",
                    "values": [{"id": "required", "label": "Required"}],
                },
            },
            "context": {
                "fields": [{"id": "domain", "label": "Domain"}],
            },
        },
        "comment_tags": {
            "stance": "#stance/<value-id>",
            "rationale": "#rationale/<value-id>",
        },
        "namespaces": {
            "stance": {
                "dimension": "stance",
                "kind": "value",
                "label": "Stance",
            },
            "rationale": {
                "dimension": "stated_rationale",
                "kind": "value",
                "label": "Stated rationale",
            },
            "guidance-level": {
                "dimension": "guidance_level",
                "path": "guidance_on_use.level",
                "kind": "value",
                "label": "Guidance level",
            },
            "guidance": {
                "dimension": "guidance_type",
                "path": "guidance_on_use.types",
                "kind": "value",
                "label": "Guidance type",
            },
            "disclosure": {
                "dimension": "disclosure",
                "path": "accountability.disclosure",
                "kind": "value",
                "label": "Disclosure",
            },
            "scope": {
                "dimension": "scope",
                "kind": "scope",
                "label": "Scope",
            },
        },
    }
    data.update(overrides)
    return data


def _codebook(**overrides) -> Codebook:
    return Codebook.from_validated(validate_codebook(_minimal_codebook(**overrides)))


def test_label_for_known_value():
    assert _codebook().label_for("stance", "ban") == "Ban"


def test_label_for_unknown_value_returns_none():
    assert _codebook().label_for("stance", "not-a-real-id") is None


def test_has_value():
    codebook = _codebook()
    assert codebook.has_value("stance", "ban") is True
    assert codebook.has_value("stance", "missing") is False


def test_namespace_rationale_maps_to_stated_rationale():
    codebook = _codebook()
    assert codebook.dimension_for_namespace("rationale") == "stated_rationale"
    assert codebook.label_for("stated_rationale", "security") == "Security"


def test_nested_path_dimensions_via_namespace():
    codebook = _codebook()
    assert codebook.dimension_for_namespace("guidance-level") == "guidance_level"
    assert codebook.label_for("guidance_level", "none") == "None"
    assert codebook.label_for("guidance_type", "design") == "Design"
    assert codebook.label_for("disclosure", "required") == "Required"


def test_unknown_namespace_returns_none():
    assert _codebook().dimension_for_namespace("nope") is None


def test_scope_membership():
    codebook = _codebook()
    assert codebook.has_scope_type("code") is True
    assert codebook.has_scope_type("docs") is False
    assert codebook.has_scope_position("allowed") is True
    assert codebook.has_scope_position("restricted") is False
    assert codebook.scope_type_label("code") == "Code"


def test_load_codebook_real_draft():
    codebook = load_codebook(REAL_CODEBOOK)
    assert codebook.version == "draft-0.1"
    assert codebook.label_for("stance", "ban") == "Ban"
    assert codebook.dimension_for_namespace("rationale") == "stated_rationale"
    assert codebook.has_scope_type("code") is True


def test_missing_namespaces_raises():
    data = _minimal_codebook()
    del data["namespaces"]
    with pytest.raises(CodebookValidationError, match="namespaces"):
        validate_codebook(data)


def test_namespace_missing_dimension_raises():
    data = _minimal_codebook()
    data["namespaces"]["stance"] = {"kind": "value", "label": "Stance"}
    with pytest.raises(CodebookValidationError, match="dimension"):
        validate_codebook(data)
