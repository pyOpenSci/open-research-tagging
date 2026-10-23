"""Derive project, PR number, user, and urls from raw GitHub review comments."""

from open_research_tagging.comments import (
    comment_refs,
    pr_number_from_comment,
    project_from_path,
    user_login_from_comment,
)


def test_project_from_path_under_projects():
    assert project_from_path("projects/pyopensci/policy.md") == "pyopensci"


def test_project_from_path_ignores_template():
    assert project_from_path("projects/_template/policy.md") is None


def test_project_from_path_outside_projects():
    assert project_from_path("README.md") is None
    assert project_from_path(None) is None
    assert project_from_path("") is None


def test_project_from_path_normalizes_backslashes():
    assert project_from_path("projects\\acme\\file.md") == "acme"


def test_pr_number_from_pull_request_url():
    comment = {
        "pull_request_url": "https://api.github.com/repos/o/r/pulls/42",
    }
    assert pr_number_from_comment(comment) == 42


def test_pr_number_from_html_url_fallback():
    comment = {
        "html_url": "https://github.com/o/r/pull/7#discussion_r1",
    }
    assert pr_number_from_comment(comment) == 7


def test_pr_number_missing_returns_none():
    assert pr_number_from_comment({}) is None


def test_user_login_from_comment():
    assert user_login_from_comment({"user": {"login": "shaunagm"}}) == "shaunagm"
    assert user_login_from_comment({"user": {}}) is None
    assert user_login_from_comment({}) is None


def test_comment_refs_bundle():
    comment = {
        "path": "projects/pyopensci/generative-ai-policy.md",
        "user": {"login": "alice"},
        "pull_request_url": "https://api.github.com/repos/o/r/pulls/3",
        "html_url": "https://github.com/o/r/pull/3#discussion_r99",
    }
    refs = comment_refs(comment)
    assert refs == {
        "path": "projects/pyopensci/generative-ai-policy.md",
        "project": "pyopensci",
        "user": "alice",
        "pr_number": 3,
        "html_url": "https://github.com/o/r/pull/3#discussion_r99",
    }
