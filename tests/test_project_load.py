"""Load project.yaml and discover project dirs (skip _-prefixed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from open_research_tagging.projects import (
    ProjectYamlError,
    iter_project_yaml_paths,
    load_project_yaml,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "projects" / "_template" / "project.yaml"


def test_template_project_yaml_exists():
    assert TEMPLATE.is_file()


def test_template_loads_as_mapping():
    data = load_project_yaml(TEMPLATE)
    assert data["slug"] == "example-project"
    assert "coding" in data
    assert "provenance" in data
    assert "files" in data


def test_iter_skips_underscore_prefixed_slugs(tmp_path: Path):
    (tmp_path / "_template").mkdir()
    (tmp_path / "_template" / "project.yaml").write_text("slug: t\n", encoding="utf-8")
    (tmp_path / "_scratch").mkdir()
    (tmp_path / "_scratch" / "project.yaml").write_text("slug: s\n", encoding="utf-8")
    real = tmp_path / "acme"
    real.mkdir()
    (real / "project.yaml").write_text("slug: acme\n", encoding="utf-8")

    paths = list(iter_project_yaml_paths(tmp_path))
    assert paths == [real / "project.yaml"]


def test_iter_empty_when_no_projects(tmp_path: Path):
    assert list(iter_project_yaml_paths(tmp_path)) == []


def test_load_rejects_non_mapping(tmp_path: Path):
    path = tmp_path / "project.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ProjectYamlError, match="mapping"):
        load_project_yaml(path)


def test_load_rejects_missing_file(tmp_path: Path):
    with pytest.raises(ProjectYamlError, match="Missing"):
        load_project_yaml(tmp_path / "nope.yaml")
