"""Emit the nested ``coding:`` YAML block for the coding-view Copy action.

Python is the contract (emit-drift); the browser mirrors this formatting.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

# Match projects/_template/project.yaml key order.
SCOPE_KEYS: tuple[str, ...] = (
    "code",
    "tests",
    "docs_and_text",
    "issues_and_pr_descriptions",
    "review",
    "autonomous_agents",
    "contribution_types_not_defined",
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


def empty_coding() -> dict[str, Any]:
    """Default nested coding shape (template-compatible)."""
    return {
        "stance": None,
        "scope": {key: "not_addressed" for key in SCOPE_KEYS},
        "stated_rationale": [],
        "guidance_on_use": {"level": None, "types": []},
        "accountability": {
            "human_responsibility": "not_stated",
            "disclosure": "none",
            "disclosure_format": [],
            "enforcement": [],
        },
        "context": {
            "project_size": "",
            "governance": None,
            "domain": "",
            "notes": "",
        },
    }


def normalize_coding(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Merge raw form/YAML coding into a complete nested dict."""
    base = empty_coding()
    if not raw:
        return base

    if raw.get("stance") not in (None, ""):
        base["stance"] = str(raw["stance"])

    scope_in = raw.get("scope")
    if isinstance(scope_in, Mapping):
        for key, val in scope_in.items():
            yaml_key = str(key).replace("-", "_")
            if val not in (None, ""):
                base["scope"][yaml_key] = str(val)

    base["stated_rationale"] = _str_list(raw.get("stated_rationale"))

    guid = raw.get("guidance_on_use")
    if isinstance(guid, Mapping):
        if guid.get("level") not in (None, ""):
            base["guidance_on_use"]["level"] = str(guid["level"])
        base["guidance_on_use"]["types"] = _str_list(guid.get("types"))

    acct = raw.get("accountability")
    if isinstance(acct, Mapping):
        if acct.get("human_responsibility") not in (None, ""):
            base["accountability"]["human_responsibility"] = _boolish_id(
                acct["human_responsibility"]
            )
        if acct.get("disclosure") not in (None, ""):
            base["accountability"]["disclosure"] = str(acct["disclosure"])
        base["accountability"]["disclosure_format"] = _str_list(
            acct.get("disclosure_format")
        )
        base["accountability"]["enforcement"] = _str_list(acct.get("enforcement"))

    ctx = raw.get("context")
    if isinstance(ctx, Mapping):
        if ctx.get("project_size") is not None:
            base["context"]["project_size"] = str(ctx["project_size"])
        if ctx.get("governance") not in (None, ""):
            base["context"]["governance"] = str(ctx["governance"])
        if ctx.get("domain") is not None:
            base["context"]["domain"] = str(ctx["domain"])
        if ctx.get("notes") is not None:
            base["context"]["notes"] = str(ctx["notes"])

    return base


def emit_coding_block(coding: Mapping[str, Any] | None) -> str:
    """
    Return a paste-ready ``coding:`` YAML fragment (trailing newline).

    Does not include provenance or files.
    """
    c = normalize_coding(coding)
    lines: list[str] = ["coding:"]
    lines.append(f"  stance: {_scalar(c['stance'])}")

    lines.append("  scope:")
    seen: set[str] = set()
    for key in SCOPE_KEYS:
        if key in c["scope"]:
            lines.append(f"    {key}: {_scalar(c['scope'][key])}")
            seen.add(key)
    for key, val in c["scope"].items():
        if key not in seen:
            lines.append(f"    {key}: {_scalar(val)}")

    _append_list_field(lines, "  stated_rationale", c["stated_rationale"])

    guid = c["guidance_on_use"]
    lines.append("  guidance_on_use:")
    lines.append(f"    level: {_scalar(guid['level'])}")
    _append_list_field(lines, "    types", guid["types"])

    acct = c["accountability"]
    lines.append("  accountability:")
    lines.append(
        f"    human_responsibility: {_scalar(acct['human_responsibility'])}"
    )
    lines.append(f"    disclosure: {_scalar(acct['disclosure'])}")
    _append_list_field(lines, "    disclosure_format", acct["disclosure_format"])
    _append_list_field(lines, "    enforcement", acct["enforcement"])

    ctx = c["context"]
    lines.append("  context:")
    lines.append(f"    project_size: {_scalar(ctx['project_size'])}")
    lines.append(f"    governance: {_scalar(ctx['governance'])}")
    lines.append(f"    domain: {_scalar(ctx['domain'])}")
    lines.append(f"    notes: {_scalar(ctx['notes'])}")
    return "\n".join(lines) + "\n"


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
