"""Shared synthetic codebook builders for tests."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_CODEBOOK_PATH = REPO_ROOT / "codebook" / "codebook.yaml"

_MINIMAL_CODEBOOK_BASE: dict[str, Any] = {
    "version": "test-0.1",
    "dimensions": {
        "stance": {
            "select": "single",
            "values": [
                {"id": "ban", "label": "Ban"},
                {"id": "allow", "label": "Allow"},
            ],
        },
        "stated_rationale": {
            "select": "multi",
            "values": [{"id": "security", "label": "Security"}],
        },
        "scope": {
            "select": "multi",
            "contribution_types": [{"id": "code", "label": "Code"}],
            "positions": ["allowed", "banned"],
        },
        "guidance_on_use": {
            "level": {
                "select": "single",
                "values": [{"id": "none", "label": "None"}],
            },
            "types": {
                "select": "multi",
                "values": [{"id": "design", "label": "Design"}],
            },
        },
        "accountability": {
            "disclosure": {
                "select": "single",
                "values": [{"id": "required", "label": "Required"}],
            },
        },
        "context": {
            "fields": [{"id": "domain", "label": "Domain"}],
        },
    },
    "comment_tags": {
        "stance": "#stance/<value-id>",
        "rationale": "#rationale/<value-id>",
    },
    "namespaces": {
        "stance": {
            "dimension": "stance",
            "kind": "value",
            "label": "Stance",
        },
        "rationale": {
            "dimension": "stated_rationale",
            "kind": "value",
            "label": "Stated rationale",
        },
        "guidance-level": {
            "dimension": "guidance_level",
            "path": "guidance_on_use.level",
            "kind": "value",
            "label": "Guidance level",
        },
        "guidance": {
            "dimension": "guidance_type",
            "path": "guidance_on_use.types",
            "kind": "value",
            "label": "Guidance type",
        },
        "disclosure": {
            "dimension": "disclosure",
            "path": "accountability.disclosure",
            "kind": "value",
            "label": "Disclosure",
        },
        "scope": {
            "dimension": "scope",
            "kind": "scope",
            "label": "Scope",
        },
    },
    "filter_order": [
        "stance",
        "stated_rationale",
        "scope",
        "guidance_level",
        "guidance_type",
        "disclosure",
    ],
}


def minimal_codebook(**overrides: Any) -> dict[str, Any]:
    """Synthetic codebook mapping for tests; override top-level keys as needed."""
    data = copy.deepcopy(_MINIMAL_CODEBOOK_BASE)
    data.update(overrides)
    return data
