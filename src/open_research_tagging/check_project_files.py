"""Check that project.yaml files: paths match the project folder (14a).

Maintainer / CI tool — not a researcher CLI. Exit non-zero on any mismatch.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from open_research_tagging.projects import (
    discover_project_file_paths,
    iter_project_yaml_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROJECTS = REPO_ROOT / "projects"


@dataclass(frozen=True)
class ProjectFilesMismatch:
    """One project whose files: set disagrees with the folder."""

    slug: str
    yaml_path: str
    missing_on_disk: list[str]
    missing_in_yaml: list[str]


def _yaml_file_paths(data: dict[str, Any]) -> set[str]:
    files = data.get("files")
    if not isinstance(files, list):
        return set()
    out: set[str] = set()
    for entry in files:
        if isinstance(entry, dict):
            path = str(entry.get("path") or "").strip()
        else:
            path = str(entry).strip()
        if path:
            out.add(path)
    return out


def check_project_dir(project_dir: str | Path) -> ProjectFilesMismatch | None:
    """
    Compare folder membership to project.yaml files: for one project dir.

    Returns None when sets match; otherwise a mismatch with sorted path lists.
    """
    project_dir = Path(project_dir)
    yaml_path = project_dir / "project.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Missing project.yaml: {yaml_path}")
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected mapping in {yaml_path}")
    slug = str(raw.get("slug") or project_dir.name)
    disk = set(discover_project_file_paths(project_dir))
    listed = _yaml_file_paths(raw)
    missing_on_disk = sorted(listed - disk)
    missing_in_yaml = sorted(disk - listed)
    if not missing_on_disk and not missing_in_yaml:
        return None
    return ProjectFilesMismatch(
        slug=slug,
        yaml_path=str(yaml_path),
        missing_on_disk=missing_on_disk,
        missing_in_yaml=missing_in_yaml,
    )


def check_projects_tree(projects_dir: str | Path) -> list[ProjectFilesMismatch]:
    """Check every discoverable project under projects_dir (skips _-prefixed)."""
    mismatches: list[ProjectFilesMismatch] = []
    for yaml_path in iter_project_yaml_paths(projects_dir):
        mismatch = check_project_dir(yaml_path.parent)
        if mismatch is not None:
            mismatches.append(mismatch)
    return mismatches


def format_mismatches(mismatches: list[ProjectFilesMismatch]) -> str:
    """Human-readable report for CI logs."""
    lines: list[str] = [
        "project.yaml files: do not match project folder contents:",
        "",
    ]
    for m in mismatches:
        lines.append(f"  {m.slug} ({m.yaml_path})")
        if m.missing_on_disk:
            lines.append("    listed in YAML but missing on disk:")
            for path in m.missing_on_disk:
                lines.append(f"      - {path}")
        if m.missing_in_yaml:
            lines.append("    on disk but missing from YAML files:")
            for path in m.missing_in_yaml:
                lines.append(f"      - {path}")
        lines.append("")
    lines.append(
        "Fix: add/rename files on the PR to match paths, or update files: via "
        "the coding view (Copy YAML). Sets must match exactly."
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=DEFAULT_PROJECTS,
        help="Directory containing projects/<slug>/project.yaml",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    projects_dir = args.projects_dir
    if not projects_dir.is_dir():
        raise SystemExit(f"Projects directory not found: {projects_dir}")
    mismatches = check_projects_tree(projects_dir)
    if not mismatches:
        print(f"OK: files: match folders under {projects_dir}")
        return
    print(format_mismatches(mismatches), file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
