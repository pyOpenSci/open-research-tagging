"""Emit projects.json from project.yaml files + comments.json."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from open_research_tagging.codebook import Codebook, validate_codebook
from open_research_tagging.projects import (
    build_projects_payload,
    collect_project_rows,
    write_projects_json,
)

from codebook_fixtures import minimal_codebook


def _codebook() -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook()))


def _write_project(root: Path, slug: str, coding: dict | None = None) -> Path:
    proj = root / "projects" / slug
    proj.mkdir(parents=True)
    path = proj / "project.yaml"
    path.write_text(
        yaml.dump(
            {
                "slug": slug,
                "display_name": slug.title(),
                "provenance": {"source_repo": "https://example.com/r"},
                "coding": coding
                or {"stance": "allow", "context": {"domain": "test"}},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_collect_skips_template_and_builds_rows(tmp_path: Path):
    _write_project(tmp_path, "acme")
    _write_project(tmp_path, "_template", coding={})
    comments = [
        {
            "id": 1,
            "project": "acme",
            "tags": [{"dimension": "stance", "filter_key": "stance:allow"}],
        }
    ]
    rows = collect_project_rows(
        projects_dir=tmp_path / "projects",
        codebook=_codebook(),
        comments=comments,
        repo_root=tmp_path,
    )
    assert len(rows) == 1
    assert rows[0]["slug"] == "acme"
    assert rows[0]["comment_count"] == 1


def test_build_and_write_projects_payload(tmp_path: Path):
    _write_project(tmp_path, "acme")
    codebook = _codebook()
    rows = collect_project_rows(
        projects_dir=tmp_path / "projects",
        codebook=codebook,
        comments=[],
        repo_root=tmp_path,
    )
    comments_path = tmp_path / "site" / "data" / "comments.json"
    payload = build_projects_payload(
        rows,
        comments_source=comments_path,
        codebook=codebook,
        repo_root=tmp_path,
    )
    assert payload["meta"]["count"] == 1
    assert payload["meta"]["codebook_version"] == "test-0.1"
    assert "comments.json" in payload["meta"]["comments_source"]

    out = tmp_path / "site" / "data" / "projects.json"
    write_projects_json(payload, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["meta"]["count"] == 1
    assert loaded["data"][0]["slug"] == "acme"


def test_process_projects_cli(tmp_path: Path):
    from open_research_tagging.process_projects import main

    _write_project(tmp_path, "acme")
    codebook_path = tmp_path / "codebook.yaml"
    codebook_path.write_text(
        yaml.dump(minimal_codebook()),
        encoding="utf-8",
    )
    comments_path = tmp_path / "comments.json"
    comments_path.write_text(
        json.dumps({"meta": {"count": 0}, "data": []}),
        encoding="utf-8",
    )
    out = tmp_path / "projects.json"
    main(
        [
            "--comments",
            str(comments_path),
            "--out",
            str(out),
            "--codebook",
            str(codebook_path),
            "--projects-dir",
            str(tmp_path / "projects"),
            "--repo-root",
            str(tmp_path),
        ]
    )
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["meta"]["count"] == 1
    assert loaded["data"][0]["slug"] == "acme"
    assert loaded["meta"]["codebook_version"] == "test-0.1"


def test_process_projects_cli_missing_comments(tmp_path: Path):
    from open_research_tagging.process_projects import main

    _write_project(tmp_path, "acme")
    codebook_path = tmp_path / "codebook.yaml"
    codebook_path.write_text(yaml.dump(minimal_codebook()), encoding="utf-8")
    out = tmp_path / "projects.json"
    main(
        [
            "--comments",
            str(tmp_path / "missing-comments.json"),
            "--out",
            str(out),
            "--codebook",
            str(codebook_path),
            "--projects-dir",
            str(tmp_path / "projects"),
            "--repo-root",
            str(tmp_path),
        ]
    )
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["meta"]["count"] == 1
    assert loaded["data"][0]["comment_count"] == 0
