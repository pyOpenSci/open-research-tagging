"""Build a coding/form schema from validated codebook YAML (12f).

The schema is the shared shape for empty_coding defaults, template stubs, and
the browser coding form. Python emit_coding_block remains the YAML contract.
"""

from __future__ import annotations

from typing import Any, Mapping

# Passage evidence dimension when focusing a coding-view section.
_EVIDENCE_DIM: dict[str, str] = {
    "stance": "stance",
    "scope": "scope",
    "stated_rationale": "stated_rationale",
    "guidance_on_use": "guidance_level",
    "accountability": "disclosure",
    "context": "",
}

# Free-text leaves used by the coding form but not yet modeled as codebook
# `fields:` entries. One place to extend until they move into the YAML.
_TEXT_EXTRAS: dict[tuple[str, str], list[dict[str, str]]] = {
    ("guidance_on_use", "implicit"): [
        {"id": "notes", "label": "Notes (files / sources)"},
        {"id": "written_for", "label": "Written for"},
        {"id": "not_ai_specific", "label": "Not AI-specific contributing advice"},
    ],
    ("accountability", "implicit"): [
        {
            "id": "notes",
            "label": (
                "Notes (responsibility / new contributors / "
                "enforcement in practice)"
            ),
        },
    ],
    ("context", "explicit"): [
        {"id": "notes", "label": "Notes"},
    ],
    ("context", "implicit"): [
        {"id": "notes", "label": "Notes"},
    ],
}

_LAYER_ORDER = ("explicit", "implicit")


def build_coding_schema(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return ``{"dimensions": [...]}`` for coding view + empty_coding."""
    dimensions = data["dimensions"]
    out: list[dict[str, Any]] = []
    for dim_id, body in dimensions.items():
        if not isinstance(body, Mapping):
            continue
        dim: dict[str, Any] = {
            "id": str(dim_id),
            "label": _dimension_label(str(dim_id), body),
            "evidence_dimension": _EVIDENCE_DIM.get(str(dim_id), ""),
            "layers": [],
        }
        for layer_id in _LAYER_ORDER:
            layer_body = body.get(layer_id)
            if not isinstance(layer_body, Mapping):
                continue
            layer = _build_layer(str(dim_id), layer_id, layer_body)
            if layer["fields"]:
                dim["layers"].append(layer)
        if dim["layers"]:
            out.append(dim)
    return {"dimensions": out}


def empty_coding_from_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Nested coding dict with schema defaults (template-compatible)."""
    coding: dict[str, Any] = {}
    for dim in schema.get("dimensions") or []:
        dim_id = dim["id"]
        dim_obj: dict[str, Any] = {}
        for layer in dim.get("layers") or []:
            dim_obj[layer["id"]] = _empty_layer_value(layer)
        coding[dim_id] = dim_obj
    return coding


def _empty_layer_value(layer: Mapping[str, Any]) -> Any:
    storage = layer.get("storage") or "object"
    fields = layer.get("fields") or []
    if storage == "scalar":
        field = fields[0] if fields else {}
        return _default_for_field(field)
    if storage == "scope_map":
        field = fields[0] if fields else {}
        default_pos = field.get("default_position") or "not_addressed"
        types = field.get("contribution_types") or []
        return {t["yaml_key"]: default_pos for t in types}
    # object: named fields
    obj: dict[str, Any] = {}
    for field in fields:
        obj[field["id"]] = _default_for_field(field)
    return obj


def _default_for_field(field: Mapping[str, Any]) -> Any:
    if "default" in field:
        return field["default"]
    kind = field.get("kind")
    if kind == "multi":
        return []
    if kind == "text":
        return ""
    if kind == "single":
        return None
    return None


def _build_layer(
    dim_id: str, layer_id: str, body: Mapping[str, Any]
) -> dict[str, Any]:
    label = str(layer_id).replace("_", " ").title()
    layer: dict[str, Any] = {
        "id": layer_id,
        "label": label,
        "storage": "object",
        "fields": [],
    }

    if "contribution_types" in body and "positions" in body:
        layer["storage"] = "scope_map"
        layer["fields"] = [_scope_field(body)]
        return layer

    if "values" in body and "select" in body:
        layer["storage"] = "scalar"
        layer["fields"] = [
            _select_field(
                field_id="_",
                label=label,
                body=body,
                default=_scalar_default(body),
            )
        ]
        _append_text_extras(layer, dim_id, layer_id)
        return layer

    if "fields" in body:
        layer["storage"] = "object"
        for entry in body["fields"]:
            if not isinstance(entry, Mapping):
                continue
            layer["fields"].append(_context_field(entry))
        _append_text_extras(layer, dim_id, layer_id)
        return layer

    # Nested named leaves (guidance level/types, accountability subfields)
    layer["storage"] = "object"
    for key, sub in body.items():
        if key in {"description", "select"} or not isinstance(sub, Mapping):
            continue
        if "values" in sub:
            layer["fields"].append(
                _select_field(
                    field_id=str(key),
                    label=_titleize(str(key)),
                    body=sub,
                    default=_named_default(dim_id, layer_id, str(key), sub),
                )
            )
    _append_text_extras(layer, dim_id, layer_id)
    return layer


def _append_text_extras(
    layer: dict[str, Any], dim_id: str, layer_id: str
) -> None:
    existing = {f["id"] for f in layer["fields"]}
    for extra in _TEXT_EXTRAS.get((dim_id, layer_id), []):
        if extra["id"] in existing:
            continue
        layer["fields"].append(
            {
                "id": extra["id"],
                "label": extra["label"],
                "kind": "text",
                "options": [],
                "default": "",
            }
        )


def _scope_field(body: Mapping[str, Any]) -> dict[str, Any]:
    types_out: list[dict[str, str]] = []
    for entry in body["contribution_types"]:
        entry_id = str(entry["id"])
        label = entry.get("label")
        if not isinstance(label, str) or not label.strip():
            label = entry_id
        types_out.append(
            {
                "id": entry_id,
                "label": label,
                "yaml_key": entry_id.replace("-", "_"),
            }
        )
    positions_out: list[dict[str, str]] = []
    for item in body["positions"]:
        if isinstance(item, str):
            positions_out.append({"id": item, "label": _titleize(item)})
        else:
            pid = str(item["id"])
            plabel = item.get("label")
            positions_out.append(
                {
                    "id": pid,
                    "label": plabel
                    if isinstance(plabel, str) and plabel.strip()
                    else _titleize(pid),
                }
            )
    default_pos = "not_addressed"
    pos_ids = {p["id"] for p in positions_out}
    if "not_seen" in pos_ids and "not_addressed" not in pos_ids:
        default_pos = "not_seen"
    elif "not_addressed" in pos_ids:
        default_pos = "not_addressed"
    elif positions_out:
        default_pos = positions_out[-1]["id"]
    return {
        "id": "_",
        "label": "Scope",
        "kind": "scope",
        "options": [],
        "contribution_types": types_out,
        "positions": positions_out,
        "default_position": default_pos,
        "default": None,
    }


def _select_field(
    *,
    field_id: str,
    label: str,
    body: Mapping[str, Any],
    default: Any,
) -> dict[str, Any]:
    select = body.get("select") or "single"
    kind = "multi" if select == "multi" else "single"
    options: list[dict[str, str]] = []
    for entry in body.get("values") or []:
        if not isinstance(entry, Mapping):
            continue
        raw_id = entry.get("id")
        if isinstance(raw_id, bool):
            eid = "yes" if raw_id else "no"
        else:
            eid = str(raw_id)
        elabel = entry.get("label")
        if isinstance(elabel, bool):
            elabel = "Yes" if elabel else "No"
        elif not isinstance(elabel, str) or not elabel.strip():
            elabel = eid
        options.append({"id": eid, "label": elabel})
    return {
        "id": field_id,
        "label": label,
        "kind": kind,
        "options": options,
        "default": default,
    }


def _context_field(entry: Mapping[str, Any]) -> dict[str, Any]:
    field_id = str(entry["id"])
    label = entry.get("label")
    if not isinstance(label, str) or not label.strip():
        label = _titleize(field_id)
    values = entry.get("values")
    if isinstance(values, list) and values:
        options: list[dict[str, str]] = []
        for item in values:
            if isinstance(item, str):
                options.append({"id": item, "label": _titleize(item)})
            elif isinstance(item, Mapping):
                oid = str(item["id"])
                olabel = item.get("label")
                options.append(
                    {
                        "id": oid,
                        "label": olabel
                        if isinstance(olabel, str) and olabel.strip()
                        else _titleize(oid),
                    }
                )
        return {
            "id": field_id,
            "label": label,
            "kind": "single",
            "options": options,
            "default": None,
        }
    return {
        "id": field_id,
        "label": label,
        "kind": "text",
        "options": [],
        "default": "",
    }


def _scalar_default(body: Mapping[str, Any]) -> Any:
    if body.get("select") == "multi":
        return []
    return None


def _named_default(
    dim_id: str, layer_id: str, key: str, body: Mapping[str, Any]
) -> Any:
    if body.get("select") == "multi":
        return []
    # Match prior template defaults for common accountability leaves
    if dim_id == "accountability" and layer_id == "explicit":
        if key == "human_responsibility":
            return "not_stated"
        if key == "disclosure":
            return "none"
        if key == "new_contributors":
            return "not_stated"
    if dim_id == "accountability" and layer_id == "implicit":
        if key == "disclosure_in_practice":
            return "none-seen"
    return None


def _dimension_label(dim_id: str, body: Mapping[str, Any]) -> str:
    desc = body.get("description")
    if isinstance(desc, str) and desc.strip():
        # First sentence fragment only for short UI labels — use titleized id
        pass
    return _titleize(dim_id)


def _titleize(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()
