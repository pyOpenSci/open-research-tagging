"""Parse and enrich codebook hashtags from PR review comment bodies."""

from __future__ import annotations

import re
from typing import Any, Mapping

from open_research_tagging.codebook import Codebook

# #namespace/value or #namespace:value; optional :qualifier (scope type:position)
TAG_RE = re.compile(
    r"#(?P<ns>[a-z0-9-]+)[/:](?P<val>[a-z0-9-]+)(?::(?P<qual>[a-z0-9-]+))?",
    re.IGNORECASE,
)


def parse_tags(body: str | None) -> list[dict[str, Any]]:
    """Extract raw tag dicts from a comment body (no codebook enrichment)."""
    tags: list[dict[str, Any]] = []
    for match in TAG_RE.finditer(body or ""):
        raw = {
            "raw": match.group(0).lower(),
            "namespace": match.group("ns").lower(),
            "value": match.group("val").lower(),
        }
        qualifier = match.group("qual")
        if qualifier:
            raw["qualifier"] = qualifier.lower()
        tags.append(raw)
    return tags


def humanize(slug: str) -> str:
    """Fallback display label when the codebook has no entry for a slug."""
    return slug.replace("-", " ").replace("_", " ").strip().capitalize()


def enrich_tag(raw_tag: Mapping[str, Any], codebook: Codebook) -> dict[str, Any]:
    """Attach dimension, labels, display, and filter_key using the codebook."""
    namespace = str(raw_tag["namespace"])
    value = str(raw_tag["value"])
    qualifier = raw_tag.get("qualifier")
    ns_info = codebook.namespace_info(namespace)
    if ns_info is None:
        dimension = namespace.replace("-", "_")
        dim_label = humanize(dimension)
        kind = "value"
    else:
        dimension = ns_info.dimension
        dim_label = ns_info.label
        kind = ns_info.kind

    tag: dict[str, Any] = {
        **dict(raw_tag),
        "dimension": dimension,
        "dimension_label": dim_label,
        "kind": kind,
    }

    if kind == "scope":
        contribution = value
        position = str(qualifier) if qualifier else "not_addressed"
        contrib_label = codebook.scope_type_label(contribution) or humanize(
            contribution
        )
        pos_label = codebook.scope_position_label(position) or humanize(position)
        tag["contribution_type"] = contribution
        tag["contribution_type_label"] = contrib_label
        tag["position"] = position
        tag["position_label"] = pos_label
        tag["value_label"] = f"{contrib_label}: {pos_label}"
        tag["display"] = f"{dim_label}: {contrib_label} → {pos_label}"
        tag["filter_key"] = f"scope:{contribution}:{position}"
        return tag

    value_label = codebook.label_for(dimension, value) or humanize(value)
    tag["value_label"] = value_label
    tag["display"] = f"{dim_label}: {value_label}"
    tag["filter_key"] = f"{dimension}:{value}"
    return tag


def parse_and_enrich(body: str | None, codebook: Codebook) -> list[dict[str, Any]]:
    """Parse tags from a body and enrich each with the codebook."""
    return [enrich_tag(tag, codebook) for tag in parse_tags(body)]
