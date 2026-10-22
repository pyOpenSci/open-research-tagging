"""Emit site codebook.json from validated YAML codebook data."""

import json
from pathlib import Path

import pytest

from open_research_tagging.codebook import (
    CodebookValidationError,
    load_codebook,
    load_codebook_file,
    validate_codebook,
)
from open_research_tagging.codebook_emit import emit_codebook_json, write_codebook_json

from codebook_fixtures import REAL_CODEBOOK_PATH, minimal_codebook


def test_emit_has_expected_top_level_keys():
    payload = emit_codebook_json(validate_codebook(minimal_codebook()))
    assert set(payload.keys()) == {
        "version",
        "namespaces",
        "values",
        "scope",
        "filter_order",
    }
    assert payload["version"] == "test-0.1"
    assert payload["values"]["stance"]["ban"] == "Ban"
    assert payload["scope"]["contribution_types"]["code"] == "Code"
    assert payload["namespaces"]["stance"]["dimension"] == "stance"
    assert payload["filter_order"][0] == "stance"
    assert "scope" in payload["filter_order"]


def test_emit_derives_filter_order_when_omitted():
    data = minimal_codebook()
    del data["filter_order"]
    payload = emit_codebook_json(validate_codebook(data))
    assert payload["filter_order"][0] == "stance"
    assert "scope" in payload["filter_order"]


def test_emit_rejects_unknown_filter_order_dimension():
    data = minimal_codebook(filter_order=["stance", "not-a-dimension"])
    with pytest.raises(CodebookValidationError, match="filter_order"):
        validate_codebook(data)


def test_emit_matches_codebook_lookups_for_real_draft():
    raw = load_codebook_file(REAL_CODEBOOK_PATH)
    codebook = load_codebook(REAL_CODEBOOK_PATH)
    payload = emit_codebook_json(raw)
    assert payload["version"] == codebook.version
    for dimension, values in payload["values"].items():
        for value_id, label in values.items():
            assert codebook.label_for(dimension, value_id) == label
    for namespace, info in payload["namespaces"].items():
        assert codebook.dimension_for_namespace(namespace) == info["dimension"]
    assert payload["values"]["stance"]["ban"] == "Ban"
    assert payload["namespaces"]["rationale"]["dimension"] == "stated_rationale"
    assert "code" in payload["scope"]["contribution_types"]


def test_write_codebook_json_round_trips_through_disk(tmp_path: Path):
    raw = validate_codebook(minimal_codebook())
    out = tmp_path / "codebook.json"
    write_codebook_json(out, raw)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == emit_codebook_json(raw)
