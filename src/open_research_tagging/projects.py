"""Discover/load project.yaml and index comments for evidence links."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, Mapping

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


def normalize_scope_key(key: str) -> str:
    """Map project.yaml scope keys to hashtag form (docs_and_text → docs-and-text)."""
    return key.replace("_", "-")


def comment_index(
    comments: list[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Build per-project comment buckets for evidence links.

    Each project maps to:
      all_ids, by_dimension, by_filter_key
    (ids deduped, first-seen order preserved).
    """
    idx: dict[str, dict[str, Any]] = {}
    for row in comments:
        project = row.get("project")
        if not project:
            continue
        project_key = str(project)
        bucket = idx.setdefault(
            project_key,
            {"by_dimension": {}, "by_filter_key": {}, "all_ids": []},
        )
        cid = row.get("id")
        bucket["all_ids"].append(cid)
        for tag in row.get("tags") or []:
            if not isinstance(tag, Mapping):
                continue
            dim = tag.get("dimension")
            key = tag.get("filter_key")
            if dim:
                bucket["by_dimension"].setdefault(str(dim), []).append(cid)
            if key:
                bucket["by_filter_key"].setdefault(str(key), []).append(cid)

    for bucket in idx.values():
        bucket["all_ids"] = list(dict.fromkeys(bucket["all_ids"]))
        for dim, ids in bucket["by_dimension"].items():
            bucket["by_dimension"][dim] = list(dict.fromkeys(ids))
        for key, ids in bucket["by_filter_key"].items():
            bucket["by_filter_key"][key] = list(dict.fromkeys(ids))
    return idx
