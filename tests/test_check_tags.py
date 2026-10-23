"""Library helpers for Actions tag-check (check_body / format_reply)."""

from open_research_tagging.check_tags import check_body, format_reply
from open_research_tagging.codebook import Codebook, validate_codebook

from codebook_fixtures import minimal_codebook


def _codebook() -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook()))


def test_check_body_valid_tags_no_warnings():
    body = "#stance/ban\n#disclosure/required\nnote"
    assert check_body(body, _codebook()) == []


def test_check_body_bare_hash_warns():
    warns = check_body("#Design", _codebook())
    assert warns
    assert any("needs #namespace/value" in w for w in warns)


def test_check_body_unknown_value_warns():
    warns = check_body("#stance/nope", _codebook())
    assert any("unknown value" in w for w in warns)


def test_check_body_empty_ok():
    assert check_body("", _codebook()) == []
    assert check_body(None, _codebook()) == []  # type: ignore[arg-type]


def test_format_reply_includes_warnings_and_guide():
    text = format_reply(
        ["#Design looks like a tag but needs #namespace/value"],
        guide_repo="acme/open-research-tagging",
    )
    assert "Tag format check" in text
    assert "#Design" in text
    assert "#disclosure/required" in text
    assert "acme/open-research-tagging" in text
    assert "codebook/COMMENTING.md" in text
