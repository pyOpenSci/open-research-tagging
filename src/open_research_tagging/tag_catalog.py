"""Canonical hashtag catalog for the passage tag picker.

Python is the source of truth; site/data/codebook.json embeds the same list
as ``tag_catalog`` so the browser does not invent strings.
"""

from __future__ import annotations

from typing import Any

from open_research_tagging.codebook import Codebook, NamespaceInfo


def canonical_tag_entries(codebook: Codebook) -> list[dict[str, Any]]:
    """
    Ordered catalog of every valid codebook hashtag.

    Each entry: hashtag, label, dimension, dimension_label, namespace, kind.
    Value tags use ``#namespace/value``; scope uses ``#scope/type:position``
    for every contribution-type × position pair.
    """
    entries: list[dict[str, Any]] = []
    # Stable order: namespaces as indexed, then scope pairs
    for namespace in sorted(codebook.known_namespaces()):
        info = codebook.namespace_info(namespace)
        if info is None or info.kind == "scope":
            continue
        entries.extend(_value_entries(codebook, namespace, info))

    scope_ns = _scope_namespace(codebook)
    if scope_ns is not None:
        ns_name, info = scope_ns
        entries.extend(_scope_entries(codebook, ns_name, info))
    return entries


def canonical_tag_strings(codebook: Codebook) -> list[str]:
    """Hashtag strings only, same order as canonical_tag_entries."""
    return [entry["hashtag"] for entry in canonical_tag_entries(codebook)]


def _value_entries(
    codebook: Codebook, namespace: str, info: NamespaceInfo
) -> list[dict[str, Any]]:
    values = codebook._values.get(info.dimension) or {}
    out: list[dict[str, Any]] = []
    for value_id in sorted(values.keys()):
        label = values[value_id]
        out.append(
            {
                "hashtag": f"#{namespace}/{value_id}",
                "label": label,
                "dimension": info.dimension,
                "dimension_label": info.label,
                "namespace": namespace,
                "kind": "value",
            }
        )
    return out


def _scope_namespace(codebook: Codebook) -> tuple[str, NamespaceInfo] | None:
    for namespace in sorted(codebook.known_namespaces()):
        info = codebook.namespace_info(namespace)
        if info is not None and info.kind == "scope":
            return namespace, info
    return None


def _scope_entries(
    codebook: Codebook, namespace: str, info: NamespaceInfo
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for type_id in sorted(codebook._scope_types.keys()):
        type_label = codebook.scope_type_label(type_id) or type_id
        for pos_id in sorted(codebook._scope_positions.keys()):
            pos_label = codebook.scope_position_label(pos_id) or pos_id
            out.append(
                {
                    "hashtag": f"#{namespace}/{type_id}:{pos_id}",
                    "label": f"{type_label} → {pos_label}",
                    "dimension": info.dimension,
                    "dimension_label": info.label,
                    "namespace": namespace,
                    "kind": "scope",
                }
            )
    return out
