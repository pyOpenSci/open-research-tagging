"""11c: emit_codebook CLI + update-comments workflow wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from open_research_tagging import emit_codebook as emit_mod

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "update-comments.yml"
REAL_CODEBOOK = REPO / "codebook" / "codebook.yaml"


def test_emit_codebook_cli_writes_json(tmp_path: Path):
    out = tmp_path / "codebook.json"
    emit_mod.main(["--codebook", str(REAL_CODEBOOK), "--out", str(out)])
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert '"tag_catalog"' in text
    assert text.endswith("\n")


def test_emit_codebook_cli_missing_codebook(tmp_path: Path):
    missing = tmp_path / "nope.yaml"
    with pytest.raises(SystemExit):
        emit_mod.main(["--codebook", str(missing), "--out", str(tmp_path / "out.json")])


def test_update_comments_workflow_wiring():
    assert WORKFLOW.is_file(), f"missing {WORKFLOW}"
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch" in text
    assert "schedule:" in text or "cron:" in text
    data = yaml.safe_load(text)
    on = data.get("on", data.get(True))
    assert "workflow_dispatch" in on
    assert "schedule" in on
    perms = data.get("permissions") or {}
    assert perms.get("contents") == "read"
    assert perms.get("pages") == "write"
    jobs = data["jobs"]
    assert "refresh-and-deploy" in jobs
    runs = "\n".join(
        str(s.get("run") or s.get("uses") or "")
        for s in jobs["refresh-and-deploy"]["steps"]
    )
    assert "fetch_comments" in runs
    assert "process_comments" in runs
    assert "emit_codebook" in runs
    assert "process_projects" in runs
    assert "--include-open-prs" in runs
    assert "git commit" not in runs
    assert "git push" not in runs
    assert "deploy-pages" in runs or "actions/deploy-pages" in text
