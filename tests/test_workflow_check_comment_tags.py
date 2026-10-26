"""11b: GitHub Actions check-comment-tags.yml wiring."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "check-comment-tags.yml"


def test_check_comment_tags_workflow_wiring():
    assert WORKFLOW.is_file(), f"missing {WORKFLOW}"
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request_review_comment" in text
    assert "pull_request:" in text or "pull_request\n" in text
    data = yaml.safe_load(text)
    on = data.get("on", data.get(True))
    assert isinstance(on, dict)
    assert "pull_request_review_comment" in on
    assert "pull_request" in on
    perms = data.get("permissions") or {}
    assert perms.get("pull-requests") == "write"
    jobs = data["jobs"]
    assert "reply-on-comment" in jobs
    assert "scan-pr" in jobs
    default_ref = "${{ github.event.repository.default_branch }}"
    for job_name in ("reply-on-comment", "scan-pr"):
        steps = jobs[job_name]["steps"]
        checkout = next(
            s for s in steps if str(s.get("uses") or "").startswith("actions/checkout")
        )
        # Content PRs may lag main; checker tooling comes from the default branch.
        assert (checkout.get("with") or {}).get("ref") == default_ref
    reply_runs = "\n".join(
        str(s.get("run") or "") for s in jobs["reply-on-comment"]["steps"]
    )
    scan_runs = "\n".join(
        str(s.get("run") or "") for s in jobs["scan-pr"]["steps"]
    )
    assert "open_research_tagging.check_tags" in reply_runs
    assert "--from-event" in reply_runs
    assert "--reply" in reply_runs
    assert "--soft" in reply_runs
    assert "open_research_tagging.check_tags" in scan_runs
    assert "--pr" in scan_runs
