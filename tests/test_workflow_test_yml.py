"""11a: GitHub Actions test.yml wiring."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "test.yml"


def test_test_workflow_exists_and_runs_pytest():
    assert WORKFLOW.is_file(), f"missing {WORKFLOW}"
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request" in text
    assert "push:" in text or "push :" in text
    data = yaml.safe_load(text)
    # PyYAML turns the key `on` into boolean True
    on = data.get("on", data.get(True))
    assert isinstance(on, dict)
    assert "pull_request" in on
    assert "push" in on
    jobs = data["jobs"]
    assert "pytest" in jobs
    # 14c: dedicated Checks job so PR checklist names the files: mismatch
    assert "project-files" in jobs
    pf_name = jobs["project-files"].get("name") or ""
    assert "project" in pf_name.lower() and ("file" in pf_name.lower() or "yaml" in pf_name.lower())
    pf_steps = jobs["project-files"]["steps"]
    pf_joined = "\n".join(str(s.get("run") or s.get("uses") or "") for s in pf_steps)
    assert "check_project_files" in pf_joined
    steps = jobs["pytest"]["steps"]
    joined = "\n".join(str(s.get("run") or s.get("uses") or "") for s in steps)
    assert ".[dev]" in joined or '".[dev]"' in joined
    assert "pytest" in joined
    assert "playwright" in joined.lower()
    assert 'python-version: "3.12"' in text or "python-version: '3.12'" in text
    # 14c: keep the membership check out of the pytest job (own Checks entry)
    assert "check_project_files" not in joined
    # Fixture JSON for Playwright is built in a temp site tree (conftest), not
    # by rewriting committed site/data in this workflow.
    assert "raw_comments.fixture.json" not in joined
