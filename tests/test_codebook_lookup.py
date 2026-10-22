"""Codebook lookup API: dimension / namespace / value id → label (soft miss)."""

import pytest

from open_research_tagging.codebook import (
    Codebook,
    CodebookValidationError,
    load_codebook,
    validate_codebook,
)

from codebook_fixtures import REAL_CODEBOOK_PATH, minimal_codebook


def _codebook(**overrides) -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook(**overrides)))


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
    codebook = load_codebook(REAL_CODEBOOK_PATH)
    assert codebook.version == "draft-0.1"
    assert codebook.label_for("stance", "ban") == "Ban"
    assert codebook.dimension_for_namespace("rationale") == "stated_rationale"
    assert codebook.has_scope_type("code") is True


def test_missing_namespaces_raises():
    data = minimal_codebook()
    del data["namespaces"]
    with pytest.raises(CodebookValidationError, match="namespaces"):
        validate_codebook(data)


def test_namespace_missing_dimension_raises():
    data = minimal_codebook()
    data["namespaces"]["stance"] = {"kind": "value", "label": "Stance"}
    with pytest.raises(CodebookValidationError, match="dimension"):
        validate_codebook(data)
