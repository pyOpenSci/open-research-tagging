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
