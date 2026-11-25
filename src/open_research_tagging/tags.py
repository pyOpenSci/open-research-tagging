"""Parse and enrich codebook hashtags from PR review comment bodies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Mapping

from open_research_tagging.codebook import Codebook

WarningKind = Literal["malformed", "unknown"]


@dataclass(frozen=True)
class TagWarning:
    """One hashtag issue; kind drives draft-codebook CI hard-fail policy."""

    message: str
    kind: WarningKind

# #namespace/value or #namespace:value; optional :qualifier (scope type:position).
# Underscores are accepted then canonicalized to hyphens (13h).
TAG_RE = re.compile(
    r"#(?P<ns>[a-z0-9_-]+)[/:](?P<val>[a-z0-9_-]+)(?::(?P<qual>[a-z0-9_-]+))?",
    re.IGNORECASE,
)
# Any #Word token — used to flag malformed tags like #Disclosure with no /value
HASH_TOKEN_RE = re.compile(r"#([A-Za-z][\w-]*)")


def canonicalize_tag_id(part: str) -> str:
    """Lowercase and map underscores to hyphens for codebook lookup."""
    return part.lower().replace("_", "-")


def _tag_identity(tag: Mapping[str, Any]) -> tuple[str, str, str]:
    """Canonical identity for dedupe (slash/colon and _/- variants match)."""
    return (
        str(tag.get("namespace") or ""),
        str(tag.get("value") or ""),
        str(tag.get("qualifier") or ""),
    )


def parse_tags(body: str | None) -> list[dict[str, Any]]:
    """Extract raw tag dicts from a comment body (no codebook enrichment).

    Duplicate hashtags (same namespace/value/qualifier after canonicalize) are
    kept once, first-seen order (13i).
    """
    tags: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for match in TAG_RE.finditer(body or ""):
        raw = {
            "raw": match.group(0).lower(),
            "namespace": canonicalize_tag_id(match.group("ns")),
            "value": canonicalize_tag_id(match.group("val")),
        }
        qualifier = match.group("qual")
        if qualifier:
            raw["qualifier"] = canonicalize_tag_id(qualifier)
        key = _tag_identity(raw)
        if key in seen:
            continue
        seen.add(key)
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
        position = str(qualifier) if qualifier else "not-addressed"
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


def collect_tag_warnings(
    body: str | None,
    tags: list[dict[str, Any]],
    codebook: Codebook,
) -> list[TagWarning]:
    """
    Flag malformed or unknown codebook hashtags.

    malformed — shape problems (bare #Word, unparseable #…).
    unknown — well-formed tags not in the current codebook.
    """
    text = body or ""
    warnings: list[TagWarning] = []
    warnings.extend(_bare_token_warnings(text))
    if not tags and not warnings and text.strip().startswith("#"):
        warnings.append(
            TagWarning(
                "Comment starts with # but no tags parsed. "
                "Use #namespace/value — see codebook/COMMENTING.md",
                "malformed",
            )
        )
    warnings.extend(_codebook_tag_warnings(tags, codebook))
    return warnings


def tag_warnings(
    body: str | None,
    tags: list[dict[str, Any]],
    codebook: Codebook,
) -> list[str]:
    """Flag malformed or unknown codebook hashtags (for needs_tag_review)."""
    return [w.message for w in collect_tag_warnings(body, tags, codebook)]


def _bare_token_warnings(text: str) -> list[TagWarning]:
    covered: set[int] = set()
    for match in TAG_RE.finditer(text):
        covered.update(range(match.start(), match.end()))
    warnings: list[TagWarning] = []
    for match in HASH_TOKEN_RE.finditer(text):
        if any(index in covered for index in range(match.start(), match.end())):
            continue
        token = match.group(0)
        warnings.append(
            TagWarning(
                f"{token} looks like a tag but needs #namespace/value "
                f"(e.g. #disclosure/required). See codebook/COMMENTING.md",
                "malformed",
            )
        )
    return warnings


def _codebook_tag_warnings(
    tags: list[dict[str, Any]], codebook: Codebook
) -> list[TagWarning]:
    warnings: list[TagWarning] = []
    known_ns = codebook.known_namespaces()
    for tag in tags:
        ns = tag.get("namespace") or ""
        raw = tag.get("raw") or f"#{ns}"
        if ns not in known_ns:
            known = ", ".join(sorted(known_ns))
            warnings.append(
                TagWarning(
                    f"{raw} uses unknown namespace '{ns}'. "
                    f"Known namespaces: {known}",
                    "unknown",
                )
            )
            continue
        if tag.get("kind") == "scope":
            warnings.extend(_scope_warnings(raw, tag, codebook))
            continue
        warnings.extend(_value_warnings(raw, tag, codebook))
    return warnings


def _scope_warnings(
    raw: str, tag: Mapping[str, Any], codebook: Codebook
) -> list[TagWarning]:
    warnings: list[TagWarning] = []
    ctype = tag.get("contribution_type") or tag.get("value")
    pos = tag.get("position") or tag.get("qualifier")
    if ctype and not codebook.has_scope_type(str(ctype)):
        warnings.append(
            TagWarning(
                f"{raw} has unknown scope type '{ctype}'. "
                f"Example: #scope/code:restricted",
                "unknown",
            )
        )
    if pos and not codebook.has_scope_position(str(pos)):
        known = ", ".join(sorted(codebook.known_scope_positions()))
        warnings.append(
            TagWarning(
                f"{raw} has unknown scope position '{pos}'. Use one of: {known}",
                "unknown",
            )
        )
    return warnings


def _value_warnings(
    raw: str, tag: Mapping[str, Any], codebook: Codebook
) -> list[TagWarning]:
    dim = str(tag.get("dimension") or "")
    val = str(tag.get("value") or "")
    ns = str(tag.get("namespace") or "")
    if not dim or codebook.has_value(dim, val):
        return []
    sample = codebook.sample_value_id(dim) or "…"
    return [
        TagWarning(
            f"{raw} has unknown value '{val}' for {dim}. Example: #{ns}/{sample}",
            "unknown",
        )
    ]
