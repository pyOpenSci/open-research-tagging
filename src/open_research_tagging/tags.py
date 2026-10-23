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
# Any #Word token — used to flag malformed tags like #Disclosure with no /value
HASH_TOKEN_RE = re.compile(r"#([A-Za-z][\w-]*)")


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


def codes_by_dimension(tags: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group enriched tags for site filters: dimension → list of entries."""
    out: dict[str, list[dict[str, Any]]] = {}
    for tag in tags:
        dim = str(tag["dimension"])
        if tag.get("kind") == "scope":
            entry = {
                "contribution_type": tag["contribution_type"],
                "position": tag["position"],
                "filter_key": tag["filter_key"],
                "display": tag["display"],
            }
        else:
            entry = {
                "value": tag["value"],
                "filter_key": tag["filter_key"],
                "display": tag["display"],
            }
        out.setdefault(dim, []).append(entry)
    return out


def tag_warnings(
    body: str | None,
    tags: list[dict[str, Any]],
    codebook: Codebook,
) -> list[str]:
    """Flag malformed or unknown codebook hashtags (for needs_tag_review)."""
    text = body or ""
    warnings: list[str] = []
    warnings.extend(_bare_token_warnings(text))
    if not tags and not warnings and text.strip().startswith("#"):
        warnings.append(
            "Comment starts with # but no tags parsed. "
            "Use #namespace/value — see codebook/COMMENTING.md"
        )
    warnings.extend(_codebook_tag_warnings(tags, codebook))
    return warnings


def _bare_token_warnings(text: str) -> list[str]:
    covered: set[int] = set()
    for match in TAG_RE.finditer(text):
        covered.update(range(match.start(), match.end()))
    warnings: list[str] = []
    for match in HASH_TOKEN_RE.finditer(text):
        if any(index in covered for index in range(match.start(), match.end())):
            continue
        token = match.group(0)
        warnings.append(
            f"{token} looks like a tag but needs #namespace/value "
            f"(e.g. #disclosure/required). See codebook/COMMENTING.md"
        )
    return warnings


def _codebook_tag_warnings(
    tags: list[dict[str, Any]], codebook: Codebook
) -> list[str]:
    warnings: list[str] = []
    known_ns = codebook.known_namespaces()
    for tag in tags:
        ns = tag.get("namespace") or ""
        raw = tag.get("raw") or f"#{ns}"
        if ns not in known_ns:
            known = ", ".join(sorted(known_ns))
            warnings.append(
                f"{raw} uses unknown namespace '{ns}'. Known namespaces: {known}"
            )
            continue
        if tag.get("kind") == "scope":
            warnings.extend(_scope_warnings(raw, tag, codebook))
            continue
        warnings.extend(_value_warnings(raw, tag, codebook))
    return warnings


def _scope_warnings(
    raw: str, tag: Mapping[str, Any], codebook: Codebook
) -> list[str]:
    warnings: list[str] = []
    ctype = tag.get("contribution_type") or tag.get("value")
    pos = tag.get("position") or tag.get("qualifier")
    if ctype and not codebook.has_scope_type(str(ctype)):
        warnings.append(
            f"{raw} has unknown scope type '{ctype}'. "
            f"Example: #scope/code:restricted"
        )
    if pos and not codebook.has_scope_position(str(pos)):
        known = ", ".join(sorted(codebook.known_scope_positions()))
        warnings.append(
            f"{raw} has unknown scope position '{pos}'. Use one of: {known}"
        )
    return warnings


def _value_warnings(
    raw: str, tag: Mapping[str, Any], codebook: Codebook
) -> list[str]:
    dim = str(tag.get("dimension") or "")
    val = str(tag.get("value") or "")
    ns = str(tag.get("namespace") or "")
    if not dim or codebook.has_value(dim, val):
        return []
    sample = codebook.sample_value_id(dim) or "…"
    return [
        f"{raw} has unknown value '{val}' for {dim}. Example: #{ns}/{sample}"
    ]
