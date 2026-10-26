"""Emit the nested ``coding:`` YAML block for the coding-view Copy action.

Python is the contract (emit-drift); the browser mirrors this formatting.

Shape (draft-0.2): each dimension has ``explicit`` / ``implicit`` subsections.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

# Match projects/_template/project.yaml key order (explicit scope).
SCOPE_KEYS_EXPLICIT: tuple[str, ...] = (
    "code",
    "tests",
    "docs_and_text",
    "issues_and_pr_descriptions",
    "review",
    "autonomous_agents",
    "contribution_types_not_defined",
)

SCOPE_KEYS_IMPLICIT: tuple[str, ...] = (
    "code",
    "comments",
    "tests",
    "docs_and_text",
    "issues_and_pr_descriptions",
    "review",
    "autonomous_agents",
)

# Backward-compatible alias used by older tests / imports.
SCOPE_KEYS = SCOPE_KEYS_EXPLICIT

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


def empty_coding() -> dict[str, Any]:
    """Default nested coding shape (template-compatible, draft-0.2)."""
    return {
        "stance": {"explicit": None, "implicit": []},
        "scope": {
            "explicit": {key: "not_addressed" for key in SCOPE_KEYS_EXPLICIT},
            "implicit": {key: "not_seen" for key in SCOPE_KEYS_IMPLICIT},
        },
        "stated_rationale": {"explicit": [], "implicit": []},
        "guidance_on_use": {
            "explicit": {"level": None, "types": []},
            "implicit": {
                "level": None,
                "types": [],
                "notes": "",
                "written_for": "",
                "not_ai_specific": "",
            },
        },
        "accountability": {
            "explicit": {
                "human_responsibility": "not_stated",
                "disclosure": "none",
                "disclosure_format": [],
                "enforcement": [],
                "new_contributors": "not_stated",
            },
            "implicit": {
                "disclosure_in_practice": "none-seen",
                "notes": "",
            },
        },
        "context": {
            "explicit": {
                "project_size": "",
                "governance": None,
                "decision_process": "",
                "domain": "",
                "policy_date": "",
                "policy_location": None,
                "notes": "",
            },
            "implicit": {
                "contributors": "",
                "who_decides": "",
                "outside_activity": "",
                "when_ai_began": "",
                "ai_file_locations": "",
                "notes": "",
            },
        },
    }


def normalize_coding(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Merge raw form/YAML coding into a complete nested dict.

    Accepts draft-0.2 nested shape. Also lifts a flat draft-0.1-style block
    into ``*.explicit`` so older seeds/tests keep working until migrated.
    """
    base = empty_coding()
    if not raw:
        return base
    raw = _lift_flat_coding(dict(raw))

    stance = raw.get("stance")
    if isinstance(stance, Mapping):
        if stance.get("explicit") not in (None, ""):
            base["stance"]["explicit"] = str(stance["explicit"])
        base["stance"]["implicit"] = _str_list(stance.get("implicit"))

    scope = raw.get("scope")
    if isinstance(scope, Mapping):
        _merge_scope_map(base["scope"]["explicit"], scope.get("explicit"))
        _merge_scope_map(base["scope"]["implicit"], scope.get("implicit"))

    rationale = raw.get("stated_rationale")
    if isinstance(rationale, Mapping):
        base["stated_rationale"]["explicit"] = _str_list(rationale.get("explicit"))
        base["stated_rationale"]["implicit"] = _str_list(rationale.get("implicit"))

    guid = raw.get("guidance_on_use")
    if isinstance(guid, Mapping):
        _merge_guidance(base["guidance_on_use"]["explicit"], guid.get("explicit"))
        _merge_guidance(base["guidance_on_use"]["implicit"], guid.get("implicit"))
        if isinstance(guid.get("implicit"), Mapping):
            impl = guid["implicit"]
            for key in ("notes", "written_for", "not_ai_specific"):
                if impl.get(key) is not None:
                    base["guidance_on_use"]["implicit"][key] = str(impl[key])

    acct = raw.get("accountability")
    if isinstance(acct, Mapping):
        _merge_accountability_explicit(
            base["accountability"]["explicit"], acct.get("explicit")
        )
        impl = acct.get("implicit")
        if isinstance(impl, Mapping):
            if impl.get("disclosure_in_practice") not in (None, ""):
                base["accountability"]["implicit"]["disclosure_in_practice"] = str(
                    impl["disclosure_in_practice"]
                )
            if impl.get("notes") is not None:
                base["accountability"]["implicit"]["notes"] = str(impl["notes"])

    ctx = raw.get("context")
    if isinstance(ctx, Mapping):
        _merge_context(base["context"]["explicit"], ctx.get("explicit"))
        _merge_context(base["context"]["implicit"], ctx.get("implicit"))

    return base


def emit_coding_block(coding: Mapping[str, Any] | None) -> str:
    """
    Return a paste-ready ``coding:`` YAML fragment (trailing newline).

    Does not include provenance or files.
    """
    c = normalize_coding(coding)
    lines: list[str] = ["coding:"]

    lines.append("  stance:")
    lines.append(f"    explicit: {_scalar(c['stance']['explicit'])}")
    _append_list_field(lines, "    implicit", c["stance"]["implicit"])

    lines.append("  scope:")
    lines.append("    explicit:")
    _append_scope_map(lines, "      ", c["scope"]["explicit"], SCOPE_KEYS_EXPLICIT)
    lines.append("    implicit:")
    _append_scope_map(lines, "      ", c["scope"]["implicit"], SCOPE_KEYS_IMPLICIT)

    lines.append("  stated_rationale:")
    _append_list_field(lines, "    explicit", c["stated_rationale"]["explicit"])
    _append_list_field(lines, "    implicit", c["stated_rationale"]["implicit"])

    lines.append("  guidance_on_use:")
    for layer in ("explicit", "implicit"):
        guid = c["guidance_on_use"][layer]
        lines.append(f"    {layer}:")
        lines.append(f"      level: {_scalar(guid['level'])}")
        _append_list_field(lines, "      types", guid["types"])
        if layer == "implicit":
            lines.append(f"      notes: {_scalar(guid.get('notes', ''))}")
            lines.append(f"      written_for: {_scalar(guid.get('written_for', ''))}")
            lines.append(
                f"      not_ai_specific: {_scalar(guid.get('not_ai_specific', ''))}"
            )

    lines.append("  accountability:")
    acct_e = c["accountability"]["explicit"]
    lines.append("    explicit:")
    lines.append(
        f"      human_responsibility: {_scalar(acct_e['human_responsibility'])}"
    )
    lines.append(f"      disclosure: {_scalar(acct_e['disclosure'])}")
    _append_list_field(lines, "      disclosure_format", acct_e["disclosure_format"])
    _append_list_field(lines, "      enforcement", acct_e["enforcement"])
    lines.append(f"      new_contributors: {_scalar(acct_e['new_contributors'])}")
    acct_i = c["accountability"]["implicit"]
    lines.append("    implicit:")
    lines.append(
        f"      disclosure_in_practice: {_scalar(acct_i['disclosure_in_practice'])}"
    )
    lines.append(f"      notes: {_scalar(acct_i['notes'])}")

    lines.append("  context:")
    for layer in ("explicit", "implicit"):
        ctx = c["context"][layer]
        lines.append(f"    {layer}:")
        for key, val in ctx.items():
            lines.append(f"      {key}: {_scalar(val)}")

    return "\n".join(lines) + "\n"


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


def _merge_scope_map(dest: dict[str, str], src: Any) -> None:
    if not isinstance(src, Mapping):
        return
    for key, val in src.items():
        yaml_key = str(key).replace("-", "_")
        if val not in (None, ""):
            dest[yaml_key] = str(val)


def _merge_guidance(dest: dict[str, Any], src: Any) -> None:
    if not isinstance(src, Mapping):
        return
    if src.get("level") not in (None, ""):
        dest["level"] = str(src["level"])
    if "types" in src:
        dest["types"] = _str_list(src.get("types"))


def _merge_accountability_explicit(dest: dict[str, Any], src: Any) -> None:
    if not isinstance(src, Mapping):
        return
    if src.get("human_responsibility") not in (None, ""):
        dest["human_responsibility"] = _boolish_id(src["human_responsibility"])
    if src.get("disclosure") not in (None, ""):
        dest["disclosure"] = str(src["disclosure"])
    if "disclosure_format" in src:
        dest["disclosure_format"] = _str_list(src.get("disclosure_format"))
    if "enforcement" in src:
        dest["enforcement"] = _str_list(src.get("enforcement"))
    if src.get("new_contributors") not in (None, ""):
        dest["new_contributors"] = _boolish_id(src["new_contributors"])


def _merge_context(dest: dict[str, Any], src: Any) -> None:
    if not isinstance(src, Mapping):
        return
    nullish_keys = {"governance", "policy_location"}
    for key, val in src.items():
        sk = str(key)
        if val in (None, "") and sk in nullish_keys:
            dest[sk] = None
        elif val is not None:
            dest[sk] = str(val)


def _append_scope_map(
    lines: list[str], indent: str, scope: Mapping[str, Any], order: tuple[str, ...]
) -> None:
    seen: set[str] = set()
    for key in order:
        if key in scope:
            lines.append(f"{indent}{key}: {_scalar(scope[key])}")
            seen.add(key)
    for key, val in scope.items():
        if key not in seen:
            lines.append(f"{indent}{key}: {_scalar(val)}")


def _append_list_field(lines: list[str], key_line: str, items: list[str]) -> None:
    """Append ``key: []`` or ``key:\\n  - item`` (key_line is indent + name)."""
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
