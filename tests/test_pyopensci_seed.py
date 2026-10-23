"""Seed project pyopensci + regenerated site JSON."""

from __future__ import annotations

import json
from pathlib import Path

from open_research_tagging.codebook import load_codebook
from open_research_tagging.comments import load_raw_comments, normalize
from open_research_tagging.projects import build_project, comment_index

REPO_ROOT = Path(__file__).resolve().parents[1]
PYOPENSCI_YAML = REPO_ROOT / "projects" / "pyopensci" / "project.yaml"
POLICY = REPO_ROOT / "projects" / "pyopensci" / "generative-ai-policy.md"
CHECKLIST = REPO_ROOT / "projects" / "pyopensci" / "gen-ai-checklist.md"
COMMENTS_JSON = REPO_ROOT / "site" / "data" / "comments.json"
PROJECTS_JSON = REPO_ROOT / "site" / "data" / "projects.json"
FIXTURE = REPO_ROOT / "site" / "data" / "raw_comments.fixture.json"
CODEBOOK = REPO_ROOT / "codebook" / "codebook.yaml"


def test_pyopensci_seed_files_exist():
    assert PYOPENSCI_YAML.is_file()
    assert POLICY.is_file()
    assert CHECKLIST.is_file()


def test_build_project_from_seed_yaml():
    codebook = load_codebook(CODEBOOK)
    comments = json.loads(COMMENTS_JSON.read_text(encoding="utf-8")).get("data") or []
    cidx = comment_index(comments)
    row = build_project(PYOPENSCI_YAML, codebook, cidx, repo_root=REPO_ROOT)
    assert row is not None
    assert row["slug"] == "pyopensci"
    assert "stance" in row["overall"]
    assert row["comment_count"] >= 1


def test_committed_projects_json_includes_pyopensci():
    payload = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
    assert payload["meta"]["count"] >= 1
    slugs = [p["slug"] for p in payload["data"]]
    assert "pyopensci" in slugs


def test_fixture_comments_prefer_local_file_quotes():
    codebook = load_codebook(CODEBOOK)
    raw = load_raw_comments(FIXTURE)
    sources = {
        normalize(c, codebook, repo_root=REPO_ROOT)["quote_source"] for c in raw
    }
    assert "paragraph" in sources or "selection" in sources
