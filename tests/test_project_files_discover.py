"""13l: discover project folder files and merge YAML descriptions by path."""

from __future__ import annotations

from pathlib import Path

import yaml

from open_research_tagging.codebook import Codebook, validate_codebook
from open_research_tagging.projects import (
    build_project,
    discover_project_file_paths,
    merge_project_files,
)

from codebook_fixtures import minimal_codebook


def _codebook() -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook()))


def test_discover_project_file_paths_recursive_excludes_yaml_and_dotfiles(
    tmp_path: Path,
):
    proj = tmp_path / "demo"
    proj.mkdir()
    (proj / "project.yaml").write_text("slug: demo\n", encoding="utf-8")
    (proj / "policy.md").write_text("# p\n", encoding="utf-8")
    (proj / ".hidden").write_text("x\n", encoding="utf-8")
    nested = proj / "extra"
    nested.mkdir()
    (nested / "checklist.md").write_text("# c\n", encoding="utf-8")
    (nested / ".skip").write_text("x\n", encoding="utf-8")

    paths = discover_project_file_paths(proj)
    assert paths == ["extra/checklist.md", "policy.md"]


def test_merge_project_files_keeps_description_adds_new_drops_orphan():
    discovered = ["a.md", "b.md", "nested/c.md"]
    yaml_files = [
        {"path": "a.md", "description": "Primary", "notes": "n"},
        {"path": "gone.md", "description": "Orphan"},
    ]
    merged = merge_project_files(discovered, yaml_files)
    assert [r["path"] for r in merged] == discovered
    assert merged[0]["description"] == "Primary"
    assert merged[0]["notes"] == "n"
    assert merged[1].get("description", "") == ""
    assert merged[2].get("description", "") == ""
    assert not any(r["path"] == "gone.md" for r in merged)


def test_build_project_merges_disk_files_with_yaml_descriptions(tmp_path: Path):
    proj = tmp_path / "projects" / "demo"
    proj.mkdir(parents=True)
    (proj / "policy.md").write_text("x\n", encoding="utf-8")
    (proj / "new.md").write_text("y\n", encoding="utf-8")
    (proj / "project.yaml").write_text(
        yaml.dump(
            {
                "slug": "demo",
                "display_name": "Demo",
                "coding": {},
                "files": [
                    {"path": "policy.md", "description": "Primary"},
                    {"path": "missing.md", "description": "Gone"},
                ],
            }
        ),
        encoding="utf-8",
    )
    row = build_project(
        proj / "project.yaml", _codebook(), {}, repo_root=tmp_path
    )
    assert row is not None
    assert [f["path"] for f in row["files"]] == ["new.md", "policy.md"]
    by_path = {f["path"]: f for f in row["files"]}
    assert by_path["policy.md"]["description"] == "Primary"
    assert by_path["new.md"].get("description", "") == ""
    assert "missing.md" not in by_path
