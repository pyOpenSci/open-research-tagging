"""Emit browser-facing codebook.json from a validated codebook mapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from open_research_tagging.codebook import (
    Codebook,
    index_scope_labels,
    resolve_dimension_path,
)
from open_research_tagging.tag_catalog import canonical_tag_entries


def emit_codebook_json(data: Mapping[str, Any]) -> dict[str, Any]:
    """Build the site codebook.json payload from validated codebook YAML data."""
    codebook = Codebook.from_validated(data)
    namespaces_out: dict[str, dict[str, str]] = {}
    for namespace, info in data["namespaces"].items():
        namespaces_out[str(namespace)] = {
            "dimension": str(info["dimension"]),
            "label": str(info.get("label") or info["dimension"]),
            "kind": str(info["kind"]),
        }
    values_out = {dim: dict(labels) for dim, labels in codebook._values.items()}
    scope_out = {
        "contribution_types": dict(codebook._scope_types),
        "positions": dict(codebook._scope_positions),
    }
    payload: dict[str, Any] = {
        "version": codebook.version,
        "namespaces": namespaces_out,
        "values": values_out,
        "scope": scope_out,
        "filter_order": _filter_order(data),
        "tag_catalog": canonical_tag_entries(codebook),
    }
    implicit_scope = _optional_scope_leaf(data, "scope.implicit")
    if implicit_scope is not None:
        payload["scope_implicit"] = implicit_scope
    return payload


def _optional_scope_leaf(
    data: Mapping[str, Any], path: str
) -> dict[str, dict[str, str]] | None:
    """Emit a second scope block (e.g. implicit seen/not_seen) when present."""
    try:
        leaf = resolve_dimension_path(data["dimensions"], path)
    except (KeyError, TypeError):
        return None
    if "contribution_types" not in leaf or "positions" not in leaf:
        return None
    types, positions = index_scope_labels(leaf)
    return {"contribution_types": types, "positions": positions}


def write_codebook_json(path: str | Path, data: Mapping[str, Any]) -> None:
    """Write emit_codebook_json(data) as UTF-8 JSON with stable formatting."""
    payload = emit_codebook_json(data)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _filter_order(data: Mapping[str, Any]) -> list[str]:
    explicit = data.get("filter_order")
    if isinstance(explicit, list):
        return [str(item) for item in explicit]
    order: list[str] = []
    seen: set[str] = set()
    for info in data["namespaces"].values():
        dimension = str(info["dimension"])
        if dimension not in seen:
            seen.add(dimension)
            order.append(dimension)
    return order
