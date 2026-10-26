"""12e: real codebook uses Explicit / Implicit subsections under each dimension."""

from __future__ import annotations

from open_research_tagging.codebook import load_codebook, load_codebook_file
from open_research_tagging.codebook_emit import emit_codebook_json

from codebook_fixtures import REAL_CODEBOOK_PATH


def test_real_codebook_has_explicit_implicit_subsections():
    raw = load_codebook_file(REAL_CODEBOOK_PATH)
    assert raw["version"] == "draft-0.2"
    dims = raw["dimensions"]
    for name in (
        "stance",
        "scope",
        "stated_rationale",
        "guidance_on_use",
        "accountability",
        "context",
    ):
        assert "explicit" in dims[name], f"{name} missing explicit"
        assert "implicit" in dims[name], f"{name} missing implicit"


def test_passage_namespaces_resolve_to_explicit_leaves():
    codebook = load_codebook(REAL_CODEBOOK_PATH)
    assert codebook.label_for("stance", "ban") == "Ban"
    assert codebook.label_for("stated_rationale", "security") == "Security"
    assert codebook.has_scope_type("code") is True
    assert codebook.has_scope_position("allowed") is True
    # Implicit stance signals are indexed under a separate dimension id
    assert codebook.has_value("stance_implicit", "outside-ai-assisted-accepted")


def test_emit_includes_implicit_stance_and_scope_implicit():
    raw = load_codebook_file(REAL_CODEBOOK_PATH)
    payload = emit_codebook_json(raw)
    assert "stance_implicit" in payload["values"]
    assert "outside-ai-assisted-accepted" in payload["values"]["stance_implicit"]
    assert "scope_implicit" in payload
    assert "seen" in payload["scope_implicit"]["positions"]
