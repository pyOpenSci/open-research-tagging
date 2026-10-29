"""Emit a full ``project.yaml`` for the coding-view Copy action (13e).

Python is the contract; the browser mirrors formatting. The ``coding:`` section
reuses ``emit_coding_block``. Files are passthrough (read-only in the form for
now; editable files are **13k**).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from open_research_tagging.coding_yaml import (
    _scalar,
    emit_coding_block,
)

# Order matches projects/_template/project.yaml provenance block.
PROVENANCE_KEYS: tuple[str, ...] = (
    "source_repo",
    "source_path",
    "source_commit",
    "source_url",
    "retrieved_at",
    "policy_location",
    "policy_date",
    "notes",
)


def empty_provenance() -> dict[str, Any]:
    """Default provenance mapping (nulls / empty notes)."""
    out: dict[str, Any] = {key: None for key in PROVENANCE_KEYS}
    out["notes"] = ""
    return out


def empty_meta() -> dict[str, Any]:
    """Empty project meta for the coding form (slug, name, provenance, files)."""
    return {
        "slug": "",
        "display_name": "",
        "provenance": empty_provenance(),
        "files": [],
    }


def normalize_meta(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Merge project row / form state into a complete meta dict."""
    base = empty_meta()
    if not raw:
        return base
    slug = str(raw.get("slug") or "").strip()
    base["slug"] = slug
    display = raw.get("display_name")
    base["display_name"] = (
        str(display).strip() if display not in (None, "") else slug
    )
    prov_in = raw.get("provenance") if isinstance(raw.get("provenance"), Mapping) else {}
    prov = empty_provenance()
    for key in PROVENANCE_KEYS:
        if key in prov_in:
            val = prov_in[key]
            if key == "notes" and val is None:
                prov[key] = ""
            else:
                prov[key] = val
    base["provenance"] = prov
    files = raw.get("files")
    if isinstance(files, list):
        base["files"] = [dict(f) if isinstance(f, Mapping) else {"path": str(f)} for f in files]
    return base


def emit_project_yaml(
    *,
    slug: str,
    display_name: str | None = None,
    provenance: Mapping[str, Any] | None = None,
    coding: Mapping[str, Any] | None = None,
    files: list[Any] | None = None,
    codebook_path: str | Path | None = None,
) -> str:
    """
    Return a paste-ready full ``project.yaml`` (trailing newline).

    Does not include the template comment header — coder pastes over the file body.
    """
    meta = normalize_meta(
        {
            "slug": slug,
            "display_name": display_name,
            "provenance": provenance or {},
            "files": files or [],
        }
    )
    lines: list[str] = [
        f"slug: {_scalar(meta['slug'] or 'example-project')}",
        f"display_name: {_scalar(meta['display_name'] or meta['slug'] or 'Example Project')}",
        "",
        "provenance:",
    ]
    for key in PROVENANCE_KEYS:
        lines.append(f"  {key}: {_scalar(meta['provenance'].get(key))}")
    lines.append("")
    coding_text = emit_coding_block(coding, codebook_path=codebook_path)
    # emit_coding_block already ends with newline; drop trailing blank join
    lines.append(coding_text.rstrip("\n"))
    lines.append("")
    lines.append("files:")
    file_rows = meta["files"]
    if not file_rows:
        lines.append("  []")
    else:
        for row in file_rows:
            if not isinstance(row, Mapping):
                lines.append(f"  - path: {_scalar(row)}")
                continue
            path = row.get("path")
            lines.append(f"  - path: {_scalar(path)}")
            if "description" in row:
                lines.append(f"    description: {_scalar(row.get('description'))}")
            for extra_key, extra_val in row.items():
                if extra_key in {"path", "description"}:
                    continue
                lines.append(f"    {extra_key}: {_scalar(extra_val)}")
    return "\n".join(lines) + "\n"
