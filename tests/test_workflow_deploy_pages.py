"""11d: GitHub Actions deploy-pages.yml wiring."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "deploy-pages.yml"


def test_deploy_pages_workflow_wiring():
    assert WORKFLOW.is_file(), f"missing {WORKFLOW}"
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch" in text
    assert "site/**" in text
    data = yaml.safe_load(text)
    on = data.get("on", data.get(True))
    assert "workflow_dispatch" in on
    assert "push" in on
    paths = on["push"].get("paths") or []
    assert "site/**" in paths
    perms = data.get("permissions") or {}
    assert perms.get("pages") == "write"
    assert perms.get("id-token") == "write"
    jobs = data["jobs"]
    assert "deploy" in jobs
    uses = "\n".join(
        str(s.get("uses") or s.get("with") or "") for s in jobs["deploy"]["steps"]
    )
    assert "actions/deploy-pages" in uses or "deploy-pages" in text
    assert "upload-pages-artifact" in text
    assert "path: site" in text or 'path: "site"' in text
