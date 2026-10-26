"""Load, structurally validate, and index codebook YAML for lookups."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping

import yaml


class CodebookValidationError(ValueError):
    """Codebook YAML is missing required structure or has invalid ids."""


@dataclass(frozen=True)
class NamespaceInfo:
    """Hashtag namespace metadata from the codebook."""

    dimension: str
    kind: str
    label: str


@dataclass(frozen=True)
class Codebook:
    """Indexed codebook: lookups by dimension / namespace / value id."""

    version: str
    _values: Mapping[str, Mapping[str, str]]
    _namespaces: Mapping[str, NamespaceInfo]
    _scope_types: Mapping[str, str]
    _scope_positions: Mapping[str, str]

    @classmethod
    def from_validated(cls, data: Mapping[str, Any]) -> Codebook:
        """Build indexes from an already-validated codebook mapping."""
        values: dict[str, dict[str, str]] = {}
        namespaces: dict[str, NamespaceInfo] = {}
        scope_types: dict[str, str] = {}
        scope_positions: dict[str, str] = {}
        dimensions = data["dimensions"]
        for namespace, info in data["namespaces"].items():
            dimension = str(info["dimension"])
            kind = str(info["kind"])
            label = str(info.get("label") or dimension)
            namespaces[str(namespace)] = NamespaceInfo(
                dimension=dimension, kind=kind, label=label
            )
            path = str(info.get("path") or dimension)
            if kind == "scope":
                scope_body = _resolve_path(dimensions, path)
                scope_types, scope_positions = _index_scope(scope_body)
                continue
            leaf = _resolve_path(dimensions, path)
            values[dimension] = _index_values(leaf.get("values", []))
        return cls(
            version=str(data["version"]),
            _values=values,
            _namespaces=namespaces,
            _scope_types=scope_types,
            _scope_positions=scope_positions,
        )

    def label_for(self, dimension: str, value_id: str) -> str | None:
        return self._values.get(dimension, {}).get(value_id)

    def has_value(self, dimension: str, value_id: str) -> bool:
        return value_id in self._values.get(dimension, {})

    def dimension_for_namespace(self, namespace: str) -> str | None:
        info = self._namespaces.get(namespace)
        return None if info is None else info.dimension

    def namespace_info(self, namespace: str) -> NamespaceInfo | None:
        return self._namespaces.get(namespace)

    def known_namespaces(self) -> set[str]:
        return set(self._namespaces)

    def sample_value_id(self, dimension: str) -> str | None:
        values = self._values.get(dimension) or {}
        return next(iter(values), None)

    def known_scope_positions(self) -> set[str]:
        return set(self._scope_positions)

    def has_scope_type(self, type_id: str) -> bool:
        return type_id in self._scope_types

    def has_scope_position(self, position_id: str) -> bool:
        return position_id in self._scope_positions

    def scope_type_label(self, type_id: str) -> str | None:
        return self._scope_types.get(type_id)

    def scope_position_label(self, position_id: str) -> str | None:
        return self._scope_positions.get(position_id)


def load_codebook(path: str | Path) -> Codebook:
    """Load, validate, and index a codebook YAML file."""
    return Codebook.from_validated(load_codebook_file(path))


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
    namespaces = data.get("namespaces")
    _validate_namespaces(namespaces, dimensions)
    _validate_filter_order(data.get("filter_order"), namespaces)
    return dict(data)


def _validate_namespaces(namespaces: Any, dimensions: Mapping[str, Any]) -> None:
    if not isinstance(namespaces, Mapping) or len(namespaces) == 0:
        raise CodebookValidationError("codebook must include a namespaces mapping")
    for name, info in namespaces.items():
        _validate_namespace_entry(str(name), info, dimensions)


def _validate_filter_order(filter_order: Any, namespaces: Mapping[str, Any]) -> None:
    if filter_order is None:
        return
    if not isinstance(filter_order, list) or len(filter_order) == 0:
        raise CodebookValidationError("filter_order must be a non-empty list when set")
    known_dimensions = {
        str(info["dimension"]) for info in namespaces.values() if isinstance(info, Mapping)
    }
    for item in filter_order:
        if not isinstance(item, str) or item.strip() == "":
            raise CodebookValidationError(
                "filter_order entries must be non-empty dimension id strings"
            )
        if item not in known_dimensions:
            raise CodebookValidationError(
                f"filter_order contains unknown dimension id {item!r}"
            )


def _validate_namespace_entry(
    name: str, info: Any, dimensions: Mapping[str, Any]
) -> None:
    if not isinstance(info, Mapping):
        raise CodebookValidationError(f"namespace {name!r} must be a mapping")
    dimension = info.get("dimension")
    if not isinstance(dimension, str) or dimension.strip() == "":
        raise CodebookValidationError(
            f"namespace {name!r} must include a non-empty string dimension"
        )
    kind = info.get("kind")
    if kind not in {"value", "scope"}:
        raise CodebookValidationError(
            f"namespace {name!r} kind must be 'value' or 'scope'"
        )
    path = info.get("path", dimension)
    if not isinstance(path, str) or path.strip() == "":
        raise CodebookValidationError(
            f"namespace {name!r} path must be a non-empty string when set"
        )
    try:
        leaf = _resolve_path(dimensions, path)
    except KeyError as exc:
        raise CodebookValidationError(
            f"namespace {name!r} path {path!r} not found under dimensions"
        ) from exc
    if kind == "scope":
        if "contribution_types" not in leaf or "positions" not in leaf:
            raise CodebookValidationError(
                f"namespace {name!r} path {path!r} must be a scope dimension"
            )
        return
    if "values" not in leaf:
        raise CodebookValidationError(
            f"namespace {name!r} path {path!r} must have a values list"
        )


def resolve_dimension_path(
    dimensions: Mapping[str, Any], path: str
) -> Mapping[str, Any]:
    """Walk a dotted path under ``dimensions`` (e.g. ``scope.explicit``)."""
    node: Any = dimensions
    for part in path.split("."):
        if not isinstance(node, Mapping) or part not in node:
            raise KeyError(path)
        node = node[part]
    if not isinstance(node, Mapping):
        raise KeyError(path)
    return node


# Back-compat for callers/tests that used the private name.
_resolve_path = resolve_dimension_path


def index_value_labels(values: list[Any]) -> dict[str, str]:
    """Map value entry ids → labels."""
    indexed: dict[str, str] = {}
    for entry in values:
        entry_id = str(entry["id"])
        label = entry.get("label")
        if not isinstance(label, str) or label.strip() == "":
            label = entry_id
        indexed[entry_id] = label
    return indexed


_index_values = index_value_labels


def index_scope_labels(
    body: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    """Index contribution_types and positions from a scope leaf body."""
    types = index_value_labels(list(body["contribution_types"]))
    positions: dict[str, str] = {}
    for item in body["positions"]:
        if isinstance(item, str):
            positions[item] = _titleize_id(item)
        else:
            entry_id = str(item["id"])
            label = item.get("label")
            positions[entry_id] = (
                label if isinstance(label, str) and label.strip() else entry_id
            )
    return types, positions


_index_scope = index_scope_labels


def _titleize_id(entry_id: str) -> str:
    return entry_id.replace("_", " ").replace("-", " ").title()


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
    return _coerce_id(path, entry.get("id"))


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
