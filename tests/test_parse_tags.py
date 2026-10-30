"""Parse codebook hashtag grammar from comment bodies (raw fields only)."""

from open_research_tagging.tags import parse_tags


def test_parse_slash_form():
    tags = parse_tags("#stance/ban")
    assert tags == [
        {
            "raw": "#stance/ban",
            "namespace": "stance",
            "value": "ban",
        }
    ]


def test_parse_colon_slip():
    tags = parse_tags("#disclosure:required")
    assert len(tags) == 1
    assert tags[0]["namespace"] == "disclosure"
    assert tags[0]["value"] == "required"
    assert tags[0]["raw"] == "#disclosure:required"
    assert "qualifier" not in tags[0]


def test_parse_scope_with_qualifier():
    tags = parse_tags("#scope/code:restricted")
    assert tags == [
        {
            "raw": "#scope/code:restricted",
            "namespace": "scope",
            "value": "code",
            "qualifier": "restricted",
        }
    ]


def test_parse_multiple_tags_in_order():
    body = "#stance/ban\n#disclosure/required\nSome note."
    tags = parse_tags(body)
    assert [t["namespace"] for t in tags] == ["stance", "disclosure"]
    assert [t["value"] for t in tags] == ["ban", "required"]


def test_parse_lowercases_mixed_case():
    tags = parse_tags("#Stance/Ban")
    assert tags[0]["raw"] == "#stance/ban"
    assert tags[0]["namespace"] == "stance"
    assert tags[0]["value"] == "ban"


def test_parse_empty_and_none_return_empty_list():
    assert parse_tags("") == []
    assert parse_tags(None) == []


def test_parse_prose_without_tags():
    assert parse_tags("No hashtags here, just a note.") == []


def test_bare_hash_word_is_not_a_parsed_tag():
    """Incomplete #stance alone is not valid grammar; warnings come in 3c."""
    assert parse_tags("#stance") == []
    assert parse_tags("#Disclosure") == []


def test_parse_accepts_underscores_and_canonicalizes_to_hyphens():
    """13h: #scope/code:not_addressed must not stop at the underscore."""
    tags = parse_tags("#scope/code:not_addressed")
    assert len(tags) == 1
    assert tags[0]["value"] == "code"
    assert tags[0]["qualifier"] == "not-addressed"
    assert tags[0]["raw"] == "#scope/code:not_addressed"


def test_parse_hyphen_form_unchanged():
    tags = parse_tags("#scope/code:not-addressed")
    assert tags[0]["qualifier"] == "not-addressed"


def test_parse_dedupes_identical_tags_keeping_first():
    """13i: same hashtag twice → one entry; first-seen order."""
    tags = parse_tags("#stance/ban\n#disclosure/required\n#stance/ban")
    assert [t["namespace"] for t in tags] == ["stance", "disclosure"]
    assert [t["value"] for t in tags] == ["ban", "required"]


def test_parse_dedupes_slash_and_colon_forms():
    tags = parse_tags("#stance/ban #stance:ban")
    assert len(tags) == 1
    assert tags[0]["raw"] == "#stance/ban"


def test_parse_dedupes_underscore_and_hyphen_scope_ids():
    tags = parse_tags(
        "#scope/code:not_addressed\nnote\n#scope/code:not-addressed"
    )
    assert len(tags) == 1
    assert tags[0]["qualifier"] == "not-addressed"
