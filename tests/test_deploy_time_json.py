"""13c: site JSON built at deploy/refresh time — no bot commits to main."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
UPDATE = REPO / ".github" / "workflows" / "update-comments.yml"
DEPLOY = REPO / ".github" / "workflows" / "deploy-pages.yml"


def test_update_comments_does_not_commit_site_json():
    text = UPDATE.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    runs = "\n".join(
        str(s.get("run") or "")
        for s in data["jobs"]["refresh-and-deploy"]["steps"]
    )
    assert "fetch_comments" in runs
    assert "process_comments" in runs
    assert "emit_codebook" in runs
    assert "process_projects" in runs
    assert "--include-open-prs" in runs
    assert "git commit" not in runs
    assert "git push" not in runs
    perms = data.get("permissions") or {}
    assert perms.get("contents") != "write"


def test_deploy_pages_rebuilds_site_json_before_upload():
    text = DEPLOY.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    on = data.get("on", data.get(True))
    paths = (on.get("push") or {}).get("paths") or []
    assert "site/**" in paths
    assert "projects/**" in paths
    assert "codebook/**" in paths
    runs = "\n".join(
        str(s.get("run") or s.get("uses") or "")
        for s in data["jobs"]["deploy"]["steps"]
    )
    assert "fetch_comments" in runs
    assert "process_comments" in runs
    assert "emit_codebook" in runs
    assert "process_projects" in runs
    assert "--include-open-prs" in runs
    assert "actions/deploy-pages" in runs or "deploy-pages" in text
    assert "git commit" not in runs
