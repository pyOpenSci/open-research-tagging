"""Structural validation for codebook YAML (ids + shape, not demo-specific values)."""

from pathlib import Path

import pytest

from open_research_tagging.codebook import (
    CodebookValidationError,
    load_codebook_file,
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
            "scope": {
                "select": "multi",
                "contribution_types": [
                    {"id": "code", "label": "Code"},
                ],
                "positions": ["allowed", "banned"],
            },
            "guidance_on_use": {
                "level": {
                    "select": "single",
                    "values": [{"id": "none", "label": "None"}],
                },
            },
            "context": {
                "fields": [
                    {"id": "domain", "label": "Domain"},
                ],
            },
        },
        "comment_tags": {
            "stance": "#stance/<value-id>",
        },
    }
    data.update(overrides)
    return data


def test_minimal_synthetic_codebook_validates():
    out = validate_codebook(_minimal_codebook())
    assert out["version"] == "test-0.1"
    assert "stance" in out["dimensions"]


def test_real_draft_codebook_file_loads():
    data = load_codebook_file(REAL_CODEBOOK)
    assert isinstance(data["version"], str)
    assert data["version"]
    assert "dimensions" in data
    assert "comment_tags" in data


def test_missing_version_raises():
    data = _minimal_codebook()
    del data["version"]
    with pytest.raises(CodebookValidationError, match="version"):
        validate_codebook(data)


def test_empty_version_raises():
    with pytest.raises(CodebookValidationError, match="version"):
        validate_codebook(_minimal_codebook(version=""))


def test_value_missing_id_raises():
    data = _minimal_codebook()
    data["dimensions"]["stance"]["values"] = [{"label": "Ban"}]
    with pytest.raises(CodebookValidationError, match="id"):
        validate_codebook(data)


def test_duplicate_id_in_same_values_list_raises():
    data = _minimal_codebook()
    data["dimensions"]["stance"]["values"] = [
        {"id": "ban", "label": "Ban"},
        {"id": "ban", "label": "Ban again"},
    ]
    with pytest.raises(CodebookValidationError, match="duplicate"):
        validate_codebook(data)


def test_same_id_in_different_dimensions_is_allowed():
    """Draft codebook reuses ids like 'other' across dimensions; uniqueness is per list."""
    data = _minimal_codebook()
    data["dimensions"]["stated_rationale"] = {
        "select": "multi",
        "values": [{"id": "ban", "label": "Same id as stance, different dimension"}],
    }
    validate_codebook(data)


def test_empty_values_list_raises():
    data = _minimal_codebook()
    data["dimensions"]["stance"]["values"] = []
    with pytest.raises(CodebookValidationError, match="empty"):
        validate_codebook(data)


def test_missing_comment_tags_raises():
    data = _minimal_codebook()
    del data["comment_tags"]
    with pytest.raises(CodebookValidationError, match="comment_tags"):
        validate_codebook(data)


def test_load_missing_file_raises():
    missing = REPO_ROOT / "codebook" / "does-not-exist.yaml"
    with pytest.raises(FileNotFoundError):
        load_codebook_file(missing)


def test_load_rejects_non_mapping_yaml(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("- just a list\n", encoding="utf-8")
    with pytest.raises(CodebookValidationError, match="mapping"):
        load_codebook_file(path)


def test_yaml_boolean_yes_no_ids_normalized_to_strings():
    data = _minimal_codebook()
    data["dimensions"]["human_responsibility"] = {
        "select": "single",
        "values": [
            {"id": True, "label": "Yes"},
            {"id": False, "label": "No"},
        ],
    }
    out = validate_codebook(data)
    ids = [v["id"] for v in out["dimensions"]["human_responsibility"]["values"]]
    assert ids == ["yes", "no"]
