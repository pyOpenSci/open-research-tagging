"""Index normalized comments by project for evidence links."""

from open_research_tagging.projects import comment_index, normalize_scope_key


def test_normalize_scope_key_underscores_to_hyphens():
    assert normalize_scope_key("docs_and_text") == "docs-and-text"
    assert normalize_scope_key("issues_and_pr_descriptions") == (
        "issues-and-pr-descriptions"
    )
    assert normalize_scope_key("code") == "code"
    assert normalize_scope_key("docs-and-text") == "docs-and-text"


def test_comment_index_groups_by_project_dimension_and_filter():
    comments = [
        {
            "id": 1,
            "project": "pyopensci",
            "tags": [
                {
                    "dimension": "stance",
                    "filter_key": "stance:permissive-with-conditions",
                }
            ],
        },
        {
            "id": 2,
            "project": "pyopensci",
            "tags": [
                {"dimension": "disclosure", "filter_key": "disclosure:required"}
            ],
        },
        {
            "id": 3,
            "project": "acme",
            "tags": [
                {
                    "dimension": "scope",
                    "filter_key": "scope:docs-and-text:restricted",
                }
            ],
        },
        {"id": 4, "project": None, "tags": []},
        {"id": 5, "project": "", "tags": []},
    ]
    idx = comment_index(comments)
    assert set(idx) == {"pyopensci", "acme"}
    assert idx["pyopensci"]["all_ids"] == [1, 2]
    assert idx["pyopensci"]["by_dimension"]["stance"] == [1]
    assert idx["pyopensci"]["by_dimension"]["disclosure"] == [2]
    assert idx["pyopensci"]["by_filter_key"]["disclosure:required"] == [2]
    assert idx["acme"]["all_ids"] == [3]
    assert idx["acme"]["by_filter_key"]["scope:docs-and-text:restricted"] == [3]


def test_comment_index_dedupes_ids_preserving_order():
    comments = [
        {
            "id": 1,
            "project": "p",
            "tags": [
                {"dimension": "stance", "filter_key": "stance:ban"},
                {"dimension": "stance", "filter_key": "stance:allow"},
            ],
        },
        {
            "id": 1,
            "project": "p",
            "tags": [{"dimension": "stance", "filter_key": "stance:ban"}],
        },
    ]
    idx = comment_index(comments)
    assert idx["p"]["all_ids"] == [1]
    assert idx["p"]["by_dimension"]["stance"] == [1]
    assert idx["p"]["by_filter_key"]["stance:ban"] == [1]
    assert idx["p"]["by_filter_key"]["stance:allow"] == [1]


def test_comment_index_empty_input():
    assert comment_index([]) == {}
