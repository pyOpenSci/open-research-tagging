"""Warnings for malformed or codebook-unknown hashtags."""

from open_research_tagging.codebook import Codebook, validate_codebook
from open_research_tagging.tags import parse_and_enrich, tag_warnings

from codebook_fixtures import minimal_codebook


def _codebook() -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook()))


def _warn(body: str) -> list[str]:
    codebook = _codebook()
    tags = parse_and_enrich(body, codebook)
    return tag_warnings(body, tags, codebook)


def test_bare_hash_word_warns():
    warnings = _warn("#Disclosure")
    assert len(warnings) == 1
    assert "#Disclosure" in warnings[0]
    assert "#namespace/value" in warnings[0]


def test_bare_stance_without_value_warns():
    warnings = _warn("#stance")
    assert any("needs #namespace/value" in w for w in warnings)


def test_known_good_tag_has_no_warnings():
    assert _warn("#stance/ban") == []


def test_unknown_namespace_warns():
    warnings = _warn("#weird-ns/foo")
    assert len(warnings) == 1
    assert "unknown namespace" in warnings[0]
    assert "weird-ns" in warnings[0]


def test_unknown_value_warns():
    warnings = _warn("#stance/not-a-real-id")
    assert len(warnings) == 1
    assert "unknown value" in warnings[0]
    assert "not-a-real-id" in warnings[0]


def test_unknown_scope_type_warns():
    warnings = _warn("#scope/not-a-type:allowed")
    assert any("unknown scope type" in w for w in warnings)


def test_unknown_scope_position_warns():
    warnings = _warn("#scope/code:not-a-position")
    assert any("unknown scope position" in w for w in warnings)


def test_underscore_scope_position_canonicalizes_without_warning():
    """13h: underscore ids normalize to hyphen codebook ids."""
    from pathlib import Path

    from open_research_tagging.codebook import load_codebook
    from open_research_tagging.tags import parse_and_enrich, tag_warnings

    root = Path(__file__).resolve().parents[1]
    codebook = load_codebook(root / "codebook" / "codebook.yaml")
    body = "#scope/code:not_addressed"
    tags = parse_and_enrich(body, codebook)
    assert tags[0]["position"] == "not-addressed"
    assert tag_warnings(body, tags, codebook) == []


def test_good_tag_plus_bare_token_warns_only_on_bare():
    warnings = _warn("#stance/ban\n#Disclosure")
    assert len(warnings) == 1
    assert "#Disclosure" in warnings[0]


def test_plain_prose_has_no_warnings():
    assert _warn("Just a note with no hashtags.") == []


def test_hash_start_with_no_parseable_tags():
    warnings = _warn("#")
    assert len(warnings) >= 1
