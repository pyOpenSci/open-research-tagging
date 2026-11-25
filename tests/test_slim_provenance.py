"""13f: provenance only keeps essential fields."""

from __future__ import annotations

from pathlib import Path

import yaml

from open_research_tagging.project_yaml import (
    PROVENANCE_KEYS,
    emit_project_yaml,
    normalize_meta,
)

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "projects" / "_template" / "project.yaml"
PYOPENSCI = REPO / "projects" / "pyopensci" / "project.yaml"
FORM_JS = REPO / "site" / "js" / "coding_form.js"


def test_provenance_keys_are_slim():
    assert PROVENANCE_KEYS == (
        "source_repo",
        "source_commit",
        "source_url",
        "retrieved_at",
        "notes",
    )
    assert "source_path" not in PROVENANCE_KEYS
    assert "policy_location" not in PROVENANCE_KEYS
    assert "policy_date" not in PROVENANCE_KEYS


def test_normalize_meta_drops_retired_provenance_keys():
    meta = normalize_meta(
        {
            "slug": "acme",
            "provenance": {
                "source_repo": "https://example.com/r",
                "source_path": "old/path.md",
                "source_commit": "abc",
                "source_url": "https://example.com/r/blob/abc/p.md",
                "retrieved_at": "2026-01-01",
                "policy_location": "standalone-file",
                "policy_date": "2020-01-01",
                "notes": "keep",
            },
        }
    )
    assert set(meta["provenance"]) == set(PROVENANCE_KEYS)
    assert "source_path" not in meta["provenance"]
    assert meta["provenance"]["notes"] == "keep"
    text = emit_project_yaml(
        slug="acme",
        provenance=meta["provenance"],
        coding={},
        files=[],
    )
    # Only the provenance block — policy_location may still appear under coding.context
    prov_block = text.split("coding:", 1)[0]
    assert "source_path:" not in prov_block
    assert "policy_location:" not in prov_block
    assert "policy_date:" not in prov_block
    assert "source_repo:" in prov_block


def test_template_and_seed_use_slim_provenance():
    for path in (TEMPLATE, PYOPENSCI):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        prov = data["provenance"]
        assert set(prov) == set(PROVENANCE_KEYS), path.name


def test_js_provenance_keys_match_python():
    src = FORM_JS.read_text(encoding="utf-8")
    assert 'PROVENANCE_KEYS = [' in src
    for key in PROVENANCE_KEYS:
        assert f'"{key}"' in src
    assert '"source_path"' not in src
    assert '"policy_location"' not in src
    assert '"policy_date"' not in src
