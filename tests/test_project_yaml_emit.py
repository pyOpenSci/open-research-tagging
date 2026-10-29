"""13e: full project.yaml emit for coding-view Copy."""

from __future__ import annotations

from pathlib import Path

import yaml

from open_research_tagging.codebook import load_codebook
from open_research_tagging.coding_yaml import emit_coding_block
from open_research_tagging.project_yaml import (
    PROVENANCE_KEYS,
    empty_meta,
    emit_project_yaml,
    normalize_meta,
)

REPO = Path(__file__).resolve().parents[1]
CODEBOOK = REPO / "codebook" / "codebook.yaml"
PYOPENSCI = REPO / "projects" / "pyopensci" / "project.yaml"


def test_emit_project_yaml_includes_meta_coding_and_files():
    text = emit_project_yaml(
        slug="acme",
        display_name="Acme",
        provenance={
            "source_repo": "https://example.com/r",
            "source_commit": "abc",
            "source_url": "https://example.com/r/blob/abc/p.md",
            "retrieved_at": "2026-01-01",
            "notes": "hi",
        },
        coding={"stance": {"explicit": "ban", "implicit": []}},
        files=[{"path": "policy.md", "description": "Primary"}],
        codebook_path=CODEBOOK,
    )
    assert text.startswith("slug: acme\n")
    assert "display_name: Acme\n" in text
    assert "provenance:\n" in text
    assert "coding:\n" in text
    assert "files:\n" in text
    assert "  - path: policy.md\n" in text
    parsed = yaml.safe_load(text)
    assert parsed["slug"] == "acme"
    assert parsed["files"][0]["path"] == "policy.md"
    assert parsed["coding"]["stance"]["explicit"] == "ban"


def test_emit_project_yaml_coding_matches_emit_coding_block():
    data = yaml.safe_load(PYOPENSCI.read_text(encoding="utf-8"))
    full = emit_project_yaml(
        slug=data["slug"],
        display_name=data["display_name"],
        provenance=data["provenance"],
        coding=data["coding"],
        files=data.get("files") or [],
        codebook_path=CODEBOOK,
    )
    coding_only = emit_coding_block(data["coding"], codebook_path=CODEBOOK)
    assert "\n" + coding_only in full or full.endswith(coding_only)
    # coding block inside full file matches standalone (same normalize)
    assert yaml.safe_load(full)["coding"] == yaml.safe_load(coding_only)["coding"]


def test_normalize_meta_fills_provenance_keys():
    meta = normalize_meta({"slug": "x", "provenance": {"source_repo": "https://a"}})
    assert meta["slug"] == "x"
    assert meta["display_name"] == "x"
    for key in PROVENANCE_KEYS:
        assert key in meta["provenance"]
    assert meta["provenance"]["source_repo"] == "https://a"
    assert isinstance(meta["files"], list)


def test_empty_meta_defaults():
    meta = empty_meta()
    assert meta["slug"] == ""
    assert set(meta["provenance"]) == set(PROVENANCE_KEYS)
