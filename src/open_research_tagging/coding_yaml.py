"""Emit the nested ``coding:`` YAML block for the coding-view Copy action.

Python is the contract (emit-drift); the browser mirrors this formatting.
Defaults and key order come from ``coding_schema`` (12f).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from open_research_tagging.codebook import load_codebook_file
from open_research_tagging.coding_schema import (
    build_coding_schema,
    empty_coding_from_schema,
)

_YAML_SPECIAL = re.compile(r"""[\s:#\[\]{},&*!|>'"%@`]""")
_QUOTE_WORDS = frozenset(
    {
        "yes",
        "no",
        "true",
        "false",
        "null",
        "on",
        "off",
        "y",
        "n",
    }
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CODEBOOK = _REPO_ROOT / "codebook" / "codebook.yaml"

# Backward-compatible alias (older tests / imports).
SCOPE_KEYS: tuple[str, ...] = (
    "code",
    "tests",
    "docs_and_text",
    "issues_and_pr_descriptions",
    "review",
    "autonomous_agents",
    "contribution_types_not_defined",
)


@lru_cache(maxsize=4)
def _schema_for_path(path_str: str) -> dict[str, Any]:
    raw = load_codebook_file(path_str)
    return build_coding_schema(raw)


def coding_schema(*, codebook_path: str | Path | None = None) -> dict[str, Any]:
    """Load coding_schema for the real (or given) codebook."""
    path = Path(codebook_path) if codebook_path else _DEFAULT_CODEBOOK
    return _schema_for_path(str(path.resolve()))


def empty_coding(
    *,
    codebook_path: str | Path | None = None,
    schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Default nested coding shape from coding_schema."""
    sch = schema if schema is not None else coding_schema(codebook_path=codebook_path)
    return empty_coding_from_schema(sch)


def normalize_coding(
    raw: Mapping[str, Any] | None,
    *,
    codebook_path: str | Path | None = None,
    schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge raw form/YAML coding into a complete nested dict."""
    sch = schema if schema is not None else coding_schema(codebook_path=codebook_path)
    base = empty_coding_from_schema(sch)
    if not raw:
        return base
    lifted = _lift_flat_coding(dict(raw))
    return _merge_by_schema(base, lifted, sch)


def emit_coding_block(
    coding: Mapping[str, Any] | None,
    *,
    codebook_path: str | Path | None = None,
    schema: Mapping[str, Any] | None = None,
) -> str:
    """
    Return a paste-ready ``coding:`` YAML fragment (trailing newline).

    Does not include provenance or files. Key order follows coding_schema.
    """
    sch = schema if schema is not None else coding_schema(codebook_path=codebook_path)
    c = normalize_coding(coding, codebook_path=codebook_path, schema=sch)
    lines: list[str] = ["coding:"]
    for dim in sch["dimensions"]:
        dim_id = dim["id"]
        dim_val = c.get(dim_id) or {}
        lines.append(f"  {dim_id}:")
        for layer in dim["layers"]:
            layer_id = layer["id"]
            storage = layer.get("storage") or "object"
            layer_val = dim_val.get(layer_id)
            _emit_layer(lines, "    ", layer_id, storage, layer, layer_val)
    return "\n".join(lines) + "\n"


def _emit_layer(
    lines: list[str],
    indent: str,
    layer_id: str,
    storage: str,
    layer: Mapping[str, Any],
    layer_val: Any,
) -> None:
    fields = layer.get("fields") or []
    if storage == "scalar":
        field = fields[0] if fields else {}
        kind = field.get("kind")
        if kind == "multi":
            _append_list_field(
                lines, f"{indent}{layer_id}", _str_list(layer_val)
            )
        else:
            lines.append(f"{indent}{layer_id}: {_scalar(layer_val)}")
        return

    lines.append(f"{indent}{layer_id}:")
    inner = indent + "  "
    if storage == "scope_map":
        field = fields[0] if fields else {}
        scope = layer_val if isinstance(layer_val, Mapping) else {}
        seen: set[str] = set()
        for t in field.get("contribution_types") or []:
            key = t["yaml_key"]
            lines.append(f"{inner}{key}: {_scalar(scope.get(key))}")
            seen.add(key)
        for key, val in scope.items():
            if key not in seen:
                lines.append(f"{inner}{key}: {_scalar(val)}")
        return

    obj = layer_val if isinstance(layer_val, Mapping) else {}
    for field in fields:
        fid = field["id"]
        kind = field.get("kind")
        val = obj.get(fid)
        if kind == "multi":
            _append_list_field(lines, f"{inner}{fid}", _str_list(val))
        else:
            lines.append(f"{inner}{fid}: {_scalar(val)}")


def _merge_by_schema(
    base: dict[str, Any],
    raw: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> dict[str, Any]:
    for dim in schema.get("dimensions") or []:
        dim_id = dim["id"]
        raw_dim = raw.get(dim_id)
        if not isinstance(raw_dim, Mapping):
            continue
        for layer in dim.get("layers") or []:
            layer_id = layer["id"]
            if layer_id not in raw_dim:
                continue
            storage = layer.get("storage") or "object"
            raw_layer = raw_dim[layer_id]
            if storage == "scalar":
                field = (layer.get("fields") or [{}])[0]
                if field.get("kind") == "multi":
                    base[dim_id][layer_id] = _str_list(raw_layer)
                elif raw_layer not in (None, ""):
                    base[dim_id][layer_id] = str(raw_layer)
                else:
                    base[dim_id][layer_id] = None
            elif storage == "scope_map" and isinstance(raw_layer, Mapping):
                dest = base[dim_id][layer_id]
                for key, val in raw_layer.items():
                    yaml_key = str(key).replace("-", "_")
                    if val not in (None, ""):
                        dest[yaml_key] = str(val)
            elif storage == "object" and isinstance(raw_layer, Mapping):
                dest = base[dim_id][layer_id]
                for field in layer.get("fields") or []:
                    fid = field["id"]
                    if fid not in raw_layer:
                        continue
                    val = raw_layer[fid]
                    kind = field.get("kind")
                    if kind == "multi":
                        dest[fid] = _str_list(val)
                    elif kind == "text":
                        if val is not None:
                            dest[fid] = str(val)
                    elif kind == "single":
                        if val in (None, ""):
                            dest[fid] = None
                        else:
                            dest[fid] = _boolish_id(val)
                    elif val not in (None, ""):
                        dest[fid] = _boolish_id(val)
    return base


def _lift_flat_coding(raw: dict[str, Any]) -> dict[str, Any]:
    """Wrap draft-0.1 flat leaves under ``explicit`` when nested keys are absent."""
    stance = raw.get("stance")
    if stance is not None and not isinstance(stance, Mapping):
        raw["stance"] = {"explicit": stance, "implicit": []}

    scope = raw.get("scope")
    if isinstance(scope, Mapping) and "explicit" not in scope and "implicit" not in scope:
        raw["scope"] = {"explicit": dict(scope), "implicit": {}}

    rationale = raw.get("stated_rationale")
    if isinstance(rationale, list):
        raw["stated_rationale"] = {"explicit": rationale, "implicit": []}

    guid = raw.get("guidance_on_use")
    if isinstance(guid, Mapping) and "explicit" not in guid and "level" in guid:
        raw["guidance_on_use"] = {
            "explicit": {"level": guid.get("level"), "types": guid.get("types") or []},
            "implicit": {},
        }

    acct = raw.get("accountability")
    if isinstance(acct, Mapping) and "explicit" not in acct and (
        "disclosure" in acct or "human_responsibility" in acct
    ):
        raw["accountability"] = {"explicit": dict(acct), "implicit": {}}

    ctx = raw.get("context")
    if isinstance(ctx, Mapping) and "explicit" not in ctx and "implicit" not in ctx:
        raw["context"] = {"explicit": dict(ctx), "implicit": {}}

    return raw


def _append_list_field(lines: list[str], key_line: str, items: list[str]) -> None:
    if not items:
        lines.append(f"{key_line}: []")
        return
    lines.append(f"{key_line}:")
    item_indent = " " * (len(key_line) - len(key_line.lstrip()) + 2)
    for item in items:
        lines.append(f"{item_indent}- {_scalar(item)}")


def _str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    return [str(value)]


def _boolish_id(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value)


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    s = str(value)
    if s == "":
        return '""'
    if s.lower() in _QUOTE_WORDS or _YAML_SPECIAL.search(s):
        return json.dumps(s, ensure_ascii=False)
    return s
