"""Open-PR project.yaml discovery merged into projects.json (13a)."""

from __future__ import annotations

import base64
from pathlib import Path

import yaml

from open_research_tagging.codebook import Codebook, validate_codebook
from open_research_tagging.github_client import GitHubHTTPError
from open_research_tagging.open_pr_projects import (
    discover_open_pr_project_yamls,
    fetch_open_pr_project_docs,
    merge_project_rows,
)
from open_research_tagging.projects import (
    build_project_from_data,
    collect_project_rows,
)

from codebook_fixtures import minimal_codebook


def _codebook() -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook()))


def _project_doc(slug: str) -> dict:
    return {
        "slug": slug,
        "display_name": slug.title(),
        "provenance": {"source_repo": "https://example.com/r"},
        "coding": {"stance": "allow"},
        "files": [{"path": "POLICY.md"}],
    }


def test_merge_adds_open_pr_slug_missing_on_main():
    main = [
        {
            "slug": "pyopensci",
            "display_name": "pyOpenSci",
            "from_open_pr": False,
        }
    ]
    pr_rows = [
        {
            "slug": "earthaccess",
            "display_name": "Earthaccess",
            "from_open_pr": True,
            "pr_number": 2,
        }
    ]
    merged = merge_project_rows(main, pr_rows)
    assert [r["slug"] for r in merged] == ["earthaccess", "pyopensci"]
    assert merged[0]["from_open_pr"] is True
    assert merged[0]["pr_number"] == 2


def test_merge_main_wins_on_slug_conflict():
    main = [{"slug": "acme", "display_name": "Main Acme", "from_open_pr": False}]
    pr_rows = [
        {
            "slug": "acme",
            "display_name": "PR Acme",
            "from_open_pr": True,
            "pr_number": 9,
        }
    ]
    merged = merge_project_rows(main, pr_rows)
    assert len(merged) == 1
    assert merged[0]["display_name"] == "Main Acme"
    assert merged[0].get("from_open_pr") is not True


def test_discover_open_pr_project_yamls_skips_template_and_non_project():
    pulls = {
        "https://api.github.com/repos/o/r/pulls?state=open&per_page=100": (
            [
                {
                    "number": 2,
                    "head": {"sha": "abc123"},
                }
            ],
            {},
        ),
    }
    files = {
        "https://api.github.com/repos/o/r/pulls/2/files?per_page=100": (
            [
                {"filename": "projects/earthaccess/project.yaml"},
                {"filename": "projects/_template/project.yaml"},
                {"filename": "README.md"},
                {"filename": "projects/earthaccess/POLICY.md"},
            ],
            {},
        ),
    }

    def getter(url: str, headers: dict[str, str]):
        if url in pulls:
            return pulls[url]
        if url in files:
            return files[url]
        raise AssertionError(f"unexpected url {url}")

    found = discover_open_pr_project_yamls("o", "r", token="tok", getter=getter)
    assert found == [
        {
            "slug": "earthaccess",
            "path": "projects/earthaccess/project.yaml",
            "pr_number": 2,
            "head_sha": "abc123",
        }
    ]


def test_fetch_open_pr_project_docs_decodes_contents():
    doc = _project_doc("earthaccess")
    encoded = base64.b64encode(yaml.dump(doc).encode("utf-8")).decode("ascii")
    contents_url = (
        "https://api.github.com/repos/o/r/contents/"
        "projects/earthaccess/project.yaml?ref=abc123"
    )

    def getter(url: str, headers: dict[str, str]):
        assert url == contents_url
        return (
            {"content": encoded, "encoding": "base64"},
            {},
        )

    specs = [
        {
            "slug": "earthaccess",
            "path": "projects/earthaccess/project.yaml",
            "pr_number": 2,
            "head_sha": "abc123",
        }
    ]
    docs = fetch_open_pr_project_docs(
        "o", "r", specs, token="tok", getter=getter
    )
    assert len(docs) == 1
    assert docs[0]["pr_number"] == 2
    assert docs[0]["data"]["slug"] == "earthaccess"


def test_build_project_from_data_marks_open_pr_and_files():
    row = build_project_from_data(
        _project_doc("earthaccess"),
        codebook=_codebook(),
        cidx={},
        yaml_path="projects/earthaccess/project.yaml",
        from_open_pr=True,
        pr_number=2,
    )
    assert row is not None
    assert row["slug"] == "earthaccess"
    assert row["from_open_pr"] is True
    assert row["pr_number"] == 2
    assert row["files"] == [{"path": "POLICY.md"}]
    assert row["yaml_path"] == "projects/earthaccess/project.yaml"


def test_collect_plus_open_pr_end_to_end(tmp_path: Path):
    """Main disk projects + open-PR yaml → merged rows for process_projects."""
    proj = tmp_path / "projects" / "pyopensci"
    proj.mkdir(parents=True)
    (proj / "project.yaml").write_text(
        yaml.dump(_project_doc("pyopensci")), encoding="utf-8"
    )

    doc = _project_doc("earthaccess")
    encoded = base64.b64encode(yaml.dump(doc).encode("utf-8")).decode("ascii")

    def getter(url: str, headers: dict[str, str]):
        if url.startswith("https://api.github.com/repos/o/r/pulls?state=open"):
            return (
                [{"number": 2, "head": {"sha": "deadbeef"}}],
                {},
            )
        if "/pulls/2/files" in url:
            return (
                [{"filename": "projects/earthaccess/project.yaml"}],
                {},
            )
        if "contents/projects/earthaccess/project.yaml" in url:
            return ({"content": encoded, "encoding": "base64"}, {})
        raise AssertionError(url)

    codebook = _codebook()
    main_rows = collect_project_rows(
        projects_dir=tmp_path / "projects",
        codebook=codebook,
        comments=[],
        repo_root=tmp_path,
    )
    specs = discover_open_pr_project_yamls(
        "o", "r", token="tok", getter=getter
    )
    docs = fetch_open_pr_project_docs(
        "o", "r", specs, token="tok", getter=getter
    )
    pr_rows = [
        build_project_from_data(
            d["data"],
            codebook=codebook,
            cidx={},
            yaml_path=d["path"],
            from_open_pr=True,
            pr_number=d["pr_number"],
        )
        for d in docs
    ]
    pr_rows = [r for r in pr_rows if r is not None]
    merged = merge_project_rows(main_rows, pr_rows)
    assert [r["slug"] for r in merged] == ["earthaccess", "pyopensci"]


def test_discover_api_error_returns_empty_and_does_not_raise():
    def getter(url: str, headers: dict[str, str]):
        raise GitHubHTTPError(500, url, "boom")

    found = discover_open_pr_project_yamls(
        "o", "r", token="tok", getter=getter
    )
    assert found == []


def test_discover_keeps_first_open_pr_for_duplicate_slug():
    warnings: list[str] = []

    def getter(url: str, headers: dict[str, str]):
        if "pulls?state=open" in url:
            return (
                [
                    {"number": 2, "head": {"sha": "aaa"}},
                    {"number": 3, "head": {"sha": "bbb"}},
                ],
                {},
            )
        if "/pulls/2/files" in url:
            return ([{"filename": "projects/acme/project.yaml"}], {})
        if "/pulls/3/files" in url:
            return ([{"filename": "projects/acme/project.yaml"}], {})
        raise AssertionError(url)

    found = discover_open_pr_project_yamls(
        "o", "r", token="tok", getter=getter, warn=warnings.append
    )
    assert found == [
        {
            "slug": "acme",
            "path": "projects/acme/project.yaml",
            "pr_number": 2,
            "head_sha": "aaa",
        }
    ]
    assert any("first open PR" in w for w in warnings)


def test_fetch_skips_failed_contents_request():
    warnings: list[str] = []

    def getter(url: str, headers: dict[str, str]):
        raise GitHubHTTPError(404, url, "missing")

    docs = fetch_open_pr_project_docs(
        "o",
        "r",
        [
            {
                "slug": "acme",
                "path": "projects/acme/project.yaml",
                "pr_number": 1,
                "head_sha": "abc",
            }
        ],
        token="tok",
        getter=getter,
        warn=warnings.append,
    )
    assert docs == []
    assert warnings
