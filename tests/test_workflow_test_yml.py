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
    steps = jobs["pytest"]["steps"]
    joined = "\n".join(str(s.get("run") or s.get("uses") or "") for s in steps)
    assert ".[dev]" in joined or '".[dev]"' in joined
    assert "pytest" in joined
    assert "playwright" in joined.lower()
    assert 'python-version: "3.12"' in text or "python-version: '3.12'" in text
