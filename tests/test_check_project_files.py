"""14a: project.yaml files: must match folder membership."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from open_research_tagging.check_project_files import (
    ProjectFilesMismatch,
    check_project_dir,
    check_projects_tree,
    main,
)


def _write_project(
    root: Path,
    slug: str,
    *,
    files: list[dict] | None = None,
    disk_names: list[str] | None = None,
) -> Path:
    proj = root / "projects" / slug
    proj.mkdir(parents=True)
    (proj / "project.yaml").write_text(
        yaml.dump(
            {
                "slug": slug,
                "display_name": slug,
                "coding": {},
                "files": files if files is not None else [],
            }
        ),
        encoding="utf-8",
    )
    for name in disk_names or []:
        path = proj / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    return proj


def test_check_project_dir_ok_when_sets_match(tmp_path: Path):
    proj = _write_project(
        tmp_path,
        "acme",
        files=[
            {"path": "policy.md", "description": "Primary"},
            {"path": "extra/checklist.md"},
        ],
        disk_names=["policy.md", "extra/checklist.md"],
    )
    assert check_project_dir(proj) is None


def test_check_project_dir_reports_missing_on_disk_and_missing_in_yaml(
    tmp_path: Path,
):
    proj = _write_project(
        tmp_path,
        "acme",
        files=[{"path": "policy.md"}, {"path": "gone.md"}],
        disk_names=["policy.md", "new.md"],
    )
    mismatch = check_project_dir(proj)
    assert isinstance(mismatch, ProjectFilesMismatch)
    assert mismatch.slug == "acme"
    assert mismatch.missing_on_disk == ["gone.md"]
    assert mismatch.missing_in_yaml == ["new.md"]


def test_check_projects_tree_skips_underscore_and_aggregates(tmp_path: Path):
    _write_project(tmp_path, "_template", files=[], disk_names=[])
    _write_project(
        tmp_path,
        "bad",
        files=[{"path": "only-in-yaml.md"}],
        disk_names=[],
    )
    _write_project(
        tmp_path,
        "good",
        files=[{"path": "a.md"}],
        disk_names=["a.md"],
    )
    mismatches = check_projects_tree(tmp_path / "projects")
    assert [m.slug for m in mismatches] == ["bad"]
    assert mismatches[0].missing_on_disk == ["only-in-yaml.md"]


def test_check_project_dir_empty_files_and_empty_folder_ok(tmp_path: Path):
    proj = _write_project(tmp_path, "empty", files=[], disk_names=[])
    assert check_project_dir(proj) is None


def test_cli_exits_nonzero_on_mismatch(tmp_path: Path, capsys):
    _write_project(
        tmp_path,
        "acme",
        files=[{"path": "missing.md"}],
        disk_names=[],
    )
    with pytest.raises(SystemExit) as exc:
        main(["--projects-dir", str(tmp_path / "projects")])
    assert exc.value.code == 1
    captured = capsys.readouterr()
    err = captured.out + captured.err
    assert "acme" in err
    assert "missing.md" in err


def test_cli_exits_zero_when_clean(tmp_path: Path, capsys):
    _write_project(
        tmp_path,
        "acme",
        files=[{"path": "a.md"}],
        disk_names=["a.md"],
    )
    main(["--projects-dir", str(tmp_path / "projects")])
    assert "OK:" in capsys.readouterr().out
