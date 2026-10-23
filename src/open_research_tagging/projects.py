"""Discover/load project.yaml, index comments, and build site project rows."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping

import yaml

from open_research_tagging.codebook import Codebook
from open_research_tagging.coding_yaml import normalize_coding
from open_research_tagging.tags import humanize


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


def as_list(value: Any) -> list[Any]:
    """Normalize null / scalar / list into a list of values."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def jsonable(value: Any) -> Any:
    """Convert YAML date objects to ISO strings for JSON output."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def coerce_code_id(value: Any) -> str:
    """YAML may turn bare yes/no into booleans; map those to codebook ids."""
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value)


def _dimension_label(codebook: Codebook, dimension: str) -> str:
    for namespace in codebook.known_namespaces():
        info = codebook.namespace_info(namespace)
        if info is not None and info.dimension == dimension:
            return info.label
    return humanize(dimension)


def _value_label(codebook: Codebook, dimension: str, value_id: str) -> str:
    return codebook.label_for(dimension, value_id) or humanize(value_id)


def _value_known(codebook: Codebook, dimension: str, value_id: str) -> bool:
    return codebook.has_value(dimension, value_id)


def link_payload(
    project: str,
    dimension: str,
    value: str | None,
    codebook: Codebook,
    cidx: Mapping[str, Any],
) -> dict[str, Any]:
    """Hover-link targets: all comments for a dimension, and matching value."""
    pb = cidx.get(project) or {"by_dimension": {}, "by_filter_key": {}}
    all_ids = list(pb.get("by_dimension", {}).get(dimension, []))
    result: dict[str, Any] = {
        "dimension": dimension,
        "dimension_label": _dimension_label(codebook, dimension),
        "all": {
            "label": f"All {dimension.replace('_', ' ')} comments",
            "count": len(all_ids),
            "comment_ids": all_ids,
            "href": f"index.html?project={project}&dimension={dimension}",
        },
    }
    if value is not None:
        filter_key = f"{dimension}:{value}"
        match_ids = list(pb.get("by_filter_key", {}).get(filter_key, []))
        label = _value_label(codebook, dimension, value)
        result["value"] = value
        result["value_label"] = label
        result["matching"] = {
            "label": label,
            "count": len(match_ids),
            "comment_ids": match_ids,
            "href": f"index.html?project={project}&filter={filter_key}",
        }
    return result


def _overall_value(
    *,
    value_id: str,
    dimension: str,
    project: str,
    codebook: Codebook,
    cidx: Mapping[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    known = _value_known(codebook, dimension, value_id)
    if not known:
        warnings.append(
            f"Unknown overall id '{value_id}' for dimension '{dimension}'"
        )
    return {
        "id": value_id,
        "label": _value_label(codebook, dimension, value_id),
        "unknown_id": not known,
        "links": link_payload(project, dimension, value_id, codebook, cidx),
    }


def build_overall(
    coding: Mapping[str, Any],
    project: str,
    codebook: Codebook,
    cidx: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """
    Map nested project.yaml coding → site overall block.

    Explicit adapter for the known YAML shape (not a generic codebook walker).
    Omits scope positions that are null or not_addressed.
    """
    overall: dict[str, Any] = {}
    warnings: list[str] = []

    stance = coding.get("stance")
    if stance:
        overall["stance"] = {
            "values": [
                _overall_value(
                    value_id=coerce_code_id(stance),
                    dimension="stance",
                    project=project,
                    codebook=codebook,
                    cidx=cidx,
                    warnings=warnings,
                )
            ]
        }

    rationales = [coerce_code_id(r) for r in as_list(coding.get("stated_rationale"))]
    if rationales:
        overall["stated_rationale"] = {
            "values": [
                _overall_value(
                    value_id=r,
                    dimension="stated_rationale",
                    project=project,
                    codebook=codebook,
                    cidx=cidx,
                    warnings=warnings,
                )
                for r in rationales
            ]
        }

    guidance = coding.get("guidance_on_use") or {}
    if isinstance(guidance, Mapping):
        level = guidance.get("level")
        if level:
            overall["guidance_level"] = {
                "values": [
                    _overall_value(
                        value_id=coerce_code_id(level),
                        dimension="guidance_level",
                        project=project,
                        codebook=codebook,
                        cidx=cidx,
                        warnings=warnings,
                    )
                ]
            }
        gtypes = [coerce_code_id(t) for t in as_list(guidance.get("types"))]
        if gtypes:
            overall["guidance_type"] = {
                "values": [
                    _overall_value(
                        value_id=t,
                        dimension="guidance_type",
                        project=project,
                        codebook=codebook,
                        cidx=cidx,
                        warnings=warnings,
                    )
                    for t in gtypes
                ]
            }

    acct = coding.get("accountability") or {}
    if isinstance(acct, Mapping):
        for field, dim in (
            ("human_responsibility", "human_responsibility"),
            ("disclosure", "disclosure"),
        ):
            val = acct.get(field)
            if val is not None:
                overall[dim] = {
                    "values": [
                        _overall_value(
                            value_id=coerce_code_id(val),
                            dimension=dim,
                            project=project,
                            codebook=codebook,
                            cidx=cidx,
                            warnings=warnings,
                        )
                    ]
                }
        enforcement = [coerce_code_id(e) for e in as_list(acct.get("enforcement"))]
        if enforcement:
            overall["enforcement"] = {
                "values": [
                    _overall_value(
                        value_id=e,
                        dimension="enforcement",
                        project=project,
                        codebook=codebook,
                        cidx=cidx,
                        warnings=warnings,
                    )
                    for e in enforcement
                ]
            }

    scope = coding.get("scope") or {}
    scope_values: list[dict[str, Any]] = []
    if isinstance(scope, Mapping):
        for raw_type, position in scope.items():
            if position in (None, "not_addressed"):
                continue
            ctype = normalize_scope_key(str(raw_type))
            pos = coerce_code_id(position)
            filter_key = f"scope:{ctype}:{pos}"
            pb = cidx.get(project) or {"by_dimension": {}, "by_filter_key": {}}
            all_scope = list(pb.get("by_dimension", {}).get("scope", []))
            match_ids = list(pb.get("by_filter_key", {}).get(filter_key, []))
            type_known = codebook.has_scope_type(ctype)
            pos_known = codebook.has_scope_position(pos)
            unknown = not (type_known and pos_known)
            if unknown:
                warnings.append(
                    f"Unknown overall scope '{ctype}:{pos}'"
                )
            type_label = codebook.scope_type_label(ctype) or humanize(ctype)
            pos_label = codebook.scope_position_label(pos) or humanize(pos)
            scope_values.append(
                {
                    "id": f"{ctype}:{pos}",
                    "contribution_type": ctype,
                    "position": pos,
                    "label": f"{type_label} → {pos_label}",
                    "unknown_id": unknown,
                    "links": {
                        "dimension": "scope",
                        "dimension_label": _dimension_label(codebook, "scope"),
                        "all": {
                            "label": "All scope comments",
                            "count": len(all_scope),
                            "comment_ids": all_scope,
                            "href": (
                                f"index.html?project={project}&dimension=scope"
                            ),
                        },
                        "matching": {
                            "label": f"{type_label} → {pos_label}",
                            "count": len(match_ids),
                            "comment_ids": match_ids,
                            "href": (
                                f"index.html?project={project}"
                                f"&scope_type={ctype}&scope_position={pos}"
                            ),
                        },
                    },
                }
            )
    if scope_values:
        overall["scope"] = {"values": scope_values}

    return overall, warnings


def build_project(
    path: str | Path,
    codebook: Codebook,
    cidx: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any] | None:
    """Build one projects.json row from a project.yaml path."""
    path = Path(path)
    root = repo_root if repo_root is not None else path.parents[1]
    data = load_project_yaml(path)
    slug = str(data.get("slug") or path.parent.name)
    if slug.startswith("_"):
        return None
    coding = data.get("coding") or {}
    if not isinstance(coding, Mapping):
        coding = {}
    provenance = data.get("provenance") or {}
    if not isinstance(provenance, Mapping):
        provenance = {}
    context = coding.get("context") or {}
    if not isinstance(context, Mapping):
        context = {}
    overall, warnings = build_overall(coding, slug, codebook, cidx)
    pb = cidx.get(slug) or {"all_ids": []}
    try:
        yaml_rel = str(path.resolve().relative_to(Path(root).resolve()))
    except ValueError:
        yaml_rel = str(path)
    return {
        "slug": slug,
        "display_name": data.get("display_name") or slug,
        "provenance": {
            "source_repo": provenance.get("source_repo"),
            "source_commit": provenance.get("source_commit"),
            "source_url": provenance.get("source_url"),
            "policy_location": provenance.get("policy_location"),
            "retrieved_at": jsonable(provenance.get("retrieved_at")),
        },
        "context": {
            "governance": context.get("governance"),
            "domain": context.get("domain"),
        },
        # Nested project.yaml coding for coding-view form pre-fill (not the
        # processed overall block used by the projects table). Normalize so
        # YAML 1.1 bare yes/no become string ids ("yes"/"no"), not JSON bools.
        "coding": normalize_coding(coding),
        "overall": overall,
        "comment_count": len(pb.get("all_ids") or []),
        "comments_href": f"index.html?project={slug}",
        "yaml_path": yaml_rel,
        "coding_warnings": warnings,
    }


def collect_project_rows(
    *,
    projects_dir: str | Path,
    codebook: Codebook,
    comments: list[Mapping[str, Any]],
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Build site rows for every discoverable project.yaml under projects_dir."""
    cidx = comment_index(comments)
    rows: list[dict[str, Any]] = []
    for yaml_path in iter_project_yaml_paths(projects_dir):
        row = build_project(
            yaml_path, codebook, cidx, repo_root=repo_root
        )
        if row is not None:
            rows.append(row)
    return rows


def build_projects_payload(
    rows: list[Mapping[str, Any]],
    *,
    comments_source: str | Path,
    codebook: Codebook,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Build the {meta, data} envelope for projects.json."""
    root = repo_root
    source = Path(comments_source)
    if root is not None:
        try:
            relative = str(source.resolve().relative_to(Path(root).resolve()))
        except ValueError:
            relative = str(source)
    else:
        relative = str(source)
    return {
        "meta": {
            "count": len(rows),
            "comments_source": relative,
            "codebook_version": codebook.version,
        },
        "data": list(rows),
    }


def write_projects_json(payload: Mapping[str, Any], path: str | Path) -> None:
    """Write projects.json with trailing newline (dates already jsonable)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    def _default(obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(
            f"Object of type {obj.__class__.__name__} is not JSON serializable"
        )

    out.write_text(
        json.dumps(payload, indent=2, default=_default) + "\n",
        encoding="utf-8",
    )
