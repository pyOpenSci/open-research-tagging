"""Enrich raw parsed tags with codebook dimension, labels, display, filter_key."""

from open_research_tagging.codebook import Codebook, validate_codebook
from open_research_tagging.tags import enrich_tag, parse_and_enrich, parse_tags

from codebook_fixtures import minimal_codebook


def _codebook() -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook()))


def test_enrich_known_stance_tag():
    raw = parse_tags("#stance/ban")[0]
    tag = enrich_tag(raw, _codebook())
    assert tag["dimension"] == "stance"
    assert tag["dimension_label"] == "Stance"
    assert tag["kind"] == "value"
    assert tag["value_label"] == "Ban"
    assert tag["display"] == "Stance: Ban"
    assert tag["filter_key"] == "stance:ban"
    assert tag["raw"] == "#stance/ban"


def test_enrich_rationale_namespace_maps_dimension():
    tag = parse_and_enrich("#rationale/security", _codebook())[0]
    assert tag["namespace"] == "rationale"
    assert tag["dimension"] == "stated_rationale"
    assert tag["filter_key"] == "stated_rationale:security"
    assert tag["value_label"] == "Security"


def test_enrich_scope_tag():
    tag = parse_and_enrich("#scope/code:banned", _codebook())[0]
    assert tag["kind"] == "scope"
    assert tag["contribution_type"] == "code"
    assert tag["position"] == "banned"
    assert tag["filter_key"] == "scope:code:banned"
    assert "Code" in tag["display"]
    assert "Banned" in tag["display"] or "banned" in tag["position_label"].lower()


def test_enrich_unknown_value_uses_humanized_fallback():
    tag = parse_and_enrich("#stance/not-in-codebook", _codebook())[0]
    assert tag["dimension"] == "stance"
    assert tag["value_label"] == "Not in codebook"
    assert tag["filter_key"] == "stance:not-in-codebook"
    assert tag["display"] == "Stance: Not in codebook"


def test_enrich_unknown_namespace_fallback_dimension():
    tag = parse_and_enrich("#weird-ns/some-val", _codebook())[0]
    assert tag["namespace"] == "weird-ns"
    assert tag["dimension"] == "weird_ns"
    assert tag["filter_key"] == "weird_ns:some-val"
    assert "qualifier" not in tag


def test_parse_and_enrich_multiple_tags():
    tags = parse_and_enrich("#stance/ban\n#disclosure/required", _codebook())
    assert [t["filter_key"] for t in tags] == [
        "stance:ban",
        "disclosure:required",
    ]
