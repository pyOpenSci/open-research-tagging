"""Evolution: content edits flow through lookup and emit without code changes."""

from open_research_tagging.codebook import Codebook, validate_codebook
from open_research_tagging.codebook_emit import emit_codebook_json

from codebook_fixtures import minimal_codebook


def test_adding_value_id_appears_in_lookup_and_emit():
    data = minimal_codebook()
    data["dimensions"]["stance"]["values"].append(
        {"id": "new-code", "label": "New Code"}
    )
    validated = validate_codebook(data)
    codebook = Codebook.from_validated(validated)
    payload = emit_codebook_json(validated)
    assert codebook.label_for("stance", "new-code") == "New Code"
    assert payload["values"]["stance"]["new-code"] == "New Code"


def test_label_change_keeps_same_id_key_in_emit():
    data = minimal_codebook()
    data["dimensions"]["stance"]["values"] = [
        {"id": "ban", "label": "Banned Completely"},
        {"id": "allow", "label": "Allow"},
    ]
    validated = validate_codebook(data)
    codebook = Codebook.from_validated(validated)
    payload = emit_codebook_json(validated)
    assert codebook.label_for("stance", "ban") == "Banned Completely"
    assert "ban" in payload["values"]["stance"]
    assert payload["values"]["stance"]["ban"] == "Banned Completely"
    assert set(payload["values"]["stance"].keys()) == {"ban", "allow"}


def test_unknown_value_id_is_soft_miss():
    codebook = Codebook.from_validated(validate_codebook(minimal_codebook()))
    assert codebook.label_for("stance", "does-not-exist") is None
    assert codebook.has_value("stance", "does-not-exist") is False
