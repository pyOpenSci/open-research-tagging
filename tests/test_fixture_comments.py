"""Offline fixture: raw_comments.fixture.json → comments.json shape + join coherence.

Committed site/data/comments.json may be live after Update comment data.
Playwright uses a temp site tree filled from this fixture (see conftest
site_under_test). These tests do not require the committed file to be
fixture-shaped.
"""

from __future__ import annotations

from pathlib import Path

from open_research_tagging.codebook import load_codebook
from open_research_tagging.comments import (
    build_comments_payload,
    is_bot_login,
    load_raw_comments,
    normalize,
)
from open_research_tagging.projects import collect_project_rows

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "site" / "data" / "raw_comments.fixture.json"
CODEBOOK = REPO_ROOT / "codebook" / "codebook.yaml"
PROJECTS_DIR = REPO_ROOT / "projects"


def test_fixture_file_exists():
    assert FIXTURE.is_file(), f"missing offline fixture: {FIXTURE}"


def test_process_fixture_end_to_end():
    codebook = load_codebook(CODEBOOK)
    raw = load_raw_comments(FIXTURE)
    assert len(raw) >= 1
    rows = [normalize(c, codebook, repo_root=REPO_ROOT) for c in raw]
    payload = build_comments_payload(
        rows,
        source_file=FIXTURE,
        codebook=codebook,
        repo_root=REPO_ROOT,
    )
    assert payload["meta"]["is_fixture"] is True
    assert payload["meta"]["count"] == len(raw)
    assert payload["meta"]["codebook_version"]
    for row in payload["data"]:
        assert "filter_keys" in row
        assert "needs_tag_review" in row
        assert isinstance(row["needs_tag_review"], bool)
        assert row["project"] == "pyopensci"
        assert not is_bot_login(row.get("user"))


def _collect_evidence_ids(project_row: dict) -> set:
    found: set = set()
    for dim_block in (project_row.get("overall") or {}).values():
        if not isinstance(dim_block, dict):
            continue
        for value in dim_block.get("values") or []:
            if not isinstance(value, dict):
                continue
            for link in (value.get("links") or {}).values():
                if not isinstance(link, dict):
                    continue
                for cid in link.get("comment_ids") or []:
                    found.add(cid)
    return found


def test_fixture_pipeline_projects_evidence_ids_resolve():
    """12a: fixture comments + projects join stay coherent (evidence ⊆ comments)."""
    codebook = load_codebook(CODEBOOK)
    raw = load_raw_comments(FIXTURE)
    rows = [normalize(c, codebook, repo_root=REPO_ROOT) for c in raw]
    comment_ids = {row["id"] for row in rows}
    assert comment_ids

    projects = collect_project_rows(
        projects_dir=PROJECTS_DIR,
        codebook=codebook,
        comments=rows,
        repo_root=REPO_ROOT,
    )
    slugs = [p["slug"] for p in projects]
    assert "pyopensci" in slugs
    py = next(p for p in projects if p["slug"] == "pyopensci")
    assert py["comment_count"] >= 1

    referenced = _collect_evidence_ids(py)
    assert referenced
    assert referenced <= comment_ids, (
        f"projects evidence ids not in fixture comments: "
        f"{sorted(referenced - comment_ids)}"
    )
