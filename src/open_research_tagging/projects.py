"""Discover and load projects/<slug>/project.yaml files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import yaml


class ProjectYamlError(ValueError):
    """project.yaml is missing or not a mapping."""


def iter_project_yaml_paths(projects_dir: str | Path) -> Iterator[Path]:
    """
    Yield projects/*/project.yaml paths, skipping _-prefixed slugs.

    `_template` (and any future `_scratch`) must not become site rows.
    """
    root = Path(projects_dir)
    if not root.is_dir():
        return
    for yaml_path in sorted(root.glob("*/project.yaml")):
        if yaml_path.parent.name.startswith("_"):
            continue
        yield yaml_path


def load_project_yaml(path: str | Path) -> dict[str, Any]:
    """Load a project.yaml file; must be a YAML mapping."""
    path = Path(path)
    if not path.is_file():
        raise ProjectYamlError(f"Missing project.yaml: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProjectYamlError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectYamlError(f"Expected mapping in {path}")
    return data
