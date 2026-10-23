"""Parse codebook hashtags from PR review comment bodies."""

from __future__ import annotations

import re
from typing import Any

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
