"""Load and structurally validate codebook YAML (shape + id uniqueness per list)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, MutableMapping

import yaml


class CodebookValidationError(ValueError):
    """Codebook YAML is missing required structure or has invalid ids."""


def load_codebook_file(path: str | Path) -> dict[str, Any]:
    """Read YAML from disk and validate structure. Raises FileNotFoundError if missing."""
    codebook_path = Path(path)
    raw = yaml.safe_load(codebook_path.read_text(encoding="utf-8"))
    return validate_codebook(raw)


def validate_codebook(data: Any) -> dict[str, Any]:
    """Validate codebook structure; return data unchanged if valid."""
    if not isinstance(data, MutableMapping):
        raise CodebookValidationError("codebook must be a YAML mapping at the top level")
    _require_nonempty_string(data, "version")
    dimensions = data.get("dimensions")
    if not isinstance(dimensions, Mapping):
        raise CodebookValidationError("codebook must include a dimensions mapping")
    for name, body in dimensions.items():
        _validate_dimension(str(name), body)
    comment_tags = data.get("comment_tags")
    if not isinstance(comment_tags, Mapping):
        raise CodebookValidationError("codebook must include a comment_tags mapping")
    return dict(data)


def _require_nonempty_string(data: Mapping[str, Any], key: str) -> None:
    value = data.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise CodebookValidationError(f"codebook must include a non-empty string {key}")


def _validate_dimension(name: str, body: Any) -> None:
    if not isinstance(body, Mapping):
        raise CodebookValidationError(f"dimension {name!r} must be a mapping")
    if "values" in body:
        _validate_values_list(name, body["values"])
        return
    if "contribution_types" in body or "positions" in body:
        _validate_scope_dimension(name, body)
        return
    if "fields" in body:
        _validate_context_fields(name, body["fields"])
        return
    # Nested group (e.g. guidance_on_use, accountability): each subkey is a leaf or nested.
    for sub_name, sub_body in body.items():
        if sub_name in {"description", "select"}:
            continue
        if isinstance(sub_body, Mapping):
            _validate_dimension(f"{name}.{sub_name}", sub_body)


def _validate_scope_dimension(name: str, body: Mapping[str, Any]) -> None:
    types = body.get("contribution_types")
    positions = body.get("positions")
    if not isinstance(types, list) or not isinstance(positions, list):
        raise CodebookValidationError(
            f"dimension {name!r} scope must include contribution_types and positions lists"
        )
    _validate_values_list(f"{name}.contribution_types", types)
    _validate_id_string_list(f"{name}.positions", positions)


def _validate_context_fields(name: str, fields: Any) -> None:
    if not isinstance(fields, list) or len(fields) == 0:
        raise CodebookValidationError(f"dimension {name!r} fields must be a non-empty list")
    seen: set[str] = set()
    for index, field in enumerate(fields):
        path = f"{name}.fields[{index}]"
        if not isinstance(field, MutableMapping):
            raise CodebookValidationError(f"{path} must be a mapping with an id")
        field_id = _require_entry_id(path, field)
        field["id"] = field_id
        _reject_duplicate(path, field_id, seen)
        if "values" in field:
            _validate_id_string_list(f"{path}.values", field["values"])


def _validate_values_list(path: str, values: Any) -> None:
    if not isinstance(values, list):
        raise CodebookValidationError(f"{path} values must be a list")
    if len(values) == 0:
        raise CodebookValidationError(f"{path} values must not be an empty list")
    seen: set[str] = set()
    for index, entry in enumerate(values):
        entry_path = f"{path}[{index}]"
        if not isinstance(entry, MutableMapping):
            raise CodebookValidationError(f"{entry_path} must be a mapping with an id")
        entry_id = _require_entry_id(entry_path, entry)
        entry["id"] = entry_id
        _reject_duplicate(entry_path, entry_id, seen)


def _validate_id_string_list(path: str, items: Any) -> None:
    """Positions or enum values may be bare id strings (or mappings with id)."""
    if not isinstance(items, list):
        raise CodebookValidationError(f"{path} must be a list")
    if len(items) == 0:
        raise CodebookValidationError(f"{path} must not be an empty list")
    seen: set[str] = set()
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        if isinstance(item, str):
            entry_id = item.strip()
            if entry_id == "":
                raise CodebookValidationError(f"{item_path} id must be a non-empty string")
        elif isinstance(item, Mapping):
            entry_id = _require_entry_id(item_path, item)
        else:
            raise CodebookValidationError(
                f"{item_path} must be an id string or a mapping with an id"
            )
        _reject_duplicate(item_path, entry_id, seen)


def _require_entry_id(path: str, entry: Mapping[str, Any]) -> str:
    entry_id = _coerce_id(path, entry.get("id"))
    return entry_id


def _coerce_id(path: str, entry_id: Any) -> str:
    """Normalize ids; bare YAML yes/no become booleans unless quoted."""
    if isinstance(entry_id, bool):
        return "yes" if entry_id else "no"
    if isinstance(entry_id, str) and entry_id.strip() != "":
        return entry_id
    raise CodebookValidationError(f"{path} must include a non-empty string id")


def _reject_duplicate(path: str, entry_id: str, seen: set[str]) -> None:
    if entry_id in seen:
        raise CodebookValidationError(f"duplicate id {entry_id!r} at {path}")
    seen.add(entry_id)
