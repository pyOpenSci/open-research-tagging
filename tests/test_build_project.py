"""Build site project rows from project.yaml + comment index."""

from __future__ import annotations

from pathlib import Path

import yaml

from open_research_tagging.codebook import Codebook, validate_codebook
from open_research_tagging.projects import build_overall, build_project

from codebook_fixtures import minimal_codebook


def _codebook() -> Codebook:
    return Codebook.from_validated(validate_codebook(minimal_codebook()))


def test_build_overall_stance_links_and_omits_not_addressed_scope():
    coding = {
        "stance": "allow",
        "stated_rationale": ["security"],
        "scope": {"code": "banned", "tests": "not-addressed"},
        "guidance_on_use": {"level": "none", "types": ["design"]},
        "accountability": {"disclosure": "required"},
    }
    cidx = {
        "demo": {
            "all_ids": [10],
            "by_dimension": {"stance": [10], "scope": [11]},
            "by_filter_key": {
                "stance:allow": [10],
                "scope:code:banned": [11],
            },
        }
    }
    overall, warnings = build_overall(coding, "demo", _codebook(), cidx)
    assert warnings == []
    assert overall["stance"]["values"][0]["id"] == "allow"
    assert overall["stance"]["values"][0]["unknown_id"] is False
    matching = overall["stance"]["values"][0]["links"]["matching"]
    assert matching["count"] == 1
    assert matching["href"] == "index.html?project=demo&filter=stance:allow"
    assert overall["stance"]["values"][0]["links"]["all"]["href"] == (
        "index.html?project=demo&dimension=stance"
    )

    scope_ids = [v["id"] for v in overall["scope"]["values"]]
    assert "code:banned" in scope_ids
    assert not any(v.startswith("tests:") for v in scope_ids)
    scope_match = overall["scope"]["values"][0]["links"]["matching"]
    assert scope_match["count"] == 1
    assert "scope_type=code" in scope_match["href"]

    assert overall["guidance_level"]["values"][0]["id"] == "none"
    assert overall["guidance_type"]["values"][0]["id"] == "design"
    assert overall["disclosure"]["values"][0]["id"] == "required"
    assert overall["stated_rationale"]["values"][0]["id"] == "security"


def test_build_overall_unknown_id_kept_and_flagged():
    coding = {"stance": "not-a-real-stance"}
    overall, warnings = build_overall(coding, "demo", _codebook(), {})
    value = overall["stance"]["values"][0]
    assert value["id"] == "not-a-real-stance"
    assert value["unknown_id"] is True
    assert value["label"]  # fallback label present
    assert any("not-a-real-stance" in w for w in warnings)


def test_build_overall_empty_coding():
    overall, warnings = build_overall({}, "demo", _codebook(), {})
    assert overall == {}
    assert warnings == []


def test_build_project_row(tmp_path: Path):
    proj = tmp_path / "projects" / "demo"
    proj.mkdir(parents=True)
    yaml_path = proj / "project.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "slug": "demo",
                "display_name": "Demo",
                "provenance": {
                    "source_repo": "https://github.com/ex/repo",
                    "source_commit": "abc",
                    "retrieved_at": "2026-01-01",
                },
                "coding": {
                    "stance": "allow",
                    "context": {"governance": "community", "domain": "test"},
                },
            }
        ),
        encoding="utf-8",
    )
    cidx = {
        "demo": {
            "all_ids": [10],
            "by_dimension": {"stance": [10]},
            "by_filter_key": {"stance:allow": [10]},
        }
    }
    row = build_project(yaml_path, _codebook(), cidx, repo_root=tmp_path)
    assert row is not None
    assert row["slug"] == "demo"
    assert row["display_name"] == "Demo"
    assert row["comment_count"] == 1
    assert row["comments_href"] == "index.html?project=demo"
    assert row["yaml_path"] == "projects/demo/project.yaml"
    assert row["context"]["governance"] == "community"
    assert row["overall"]["stance"]["values"][0]["id"] == "allow"
    assert row["coding_warnings"] == []
    # Normalized nested coding for coding-view form pre-fill (10c / 12e)
    assert row["coding"]["stance"]["explicit"] == "allow"
    assert row["coding"]["context"]["explicit"]["domain"] == "test"


def test_build_project_coerces_yaml_yes_bool_in_coding(tmp_path: Path):
    """Bare YAML yes becomes bool True on load; coding passthrough must store 'yes'."""
    proj = tmp_path / "projects" / "demo"
    proj.mkdir(parents=True)
    yaml_path = proj / "project.yaml"
    yaml_path.write_text(
        "slug: demo\ncoding:\n  accountability:\n    human_responsibility: yes\n",
        encoding="utf-8",
    )
    row = build_project(yaml_path, _codebook(), {}, repo_root=tmp_path)
    assert row is not None
    assert (
        row["coding"]["accountability"]["explicit"]["human_responsibility"] == "yes"
    )


def test_build_project_skips_underscore_slug(tmp_path: Path):
    proj = tmp_path / "projects" / "_template"
    proj.mkdir(parents=True)
    yaml_path = proj / "project.yaml"
    yaml_path.write_text(
        yaml.dump({"slug": "_template", "coding": {}}),
        encoding="utf-8",
    )
    assert build_project(yaml_path, _codebook(), {}, repo_root=tmp_path) is None


def test_build_project_placeholder_display_name_uses_slug(tmp_path: Path):
    """13g: template display_name 'Example Project' must not appear on the site."""
    proj = tmp_path / "projects" / "acme-ai"
    proj.mkdir(parents=True)
    yaml_path = proj / "project.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "slug": "acme-ai",
                "display_name": "Example Project",
                "coding": {},
            }
        ),
        encoding="utf-8",
    )
    row = build_project(yaml_path, _codebook(), {}, repo_root=tmp_path)
    assert row is not None
    assert row["display_name"] == "acme-ai"


def test_build_project_keeps_real_display_name(tmp_path: Path):
    proj = tmp_path / "projects" / "acme-ai"
    proj.mkdir(parents=True)
    yaml_path = proj / "project.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "slug": "acme-ai",
                "display_name": "Acme AI Policy",
                "coding": {},
            }
        ),
        encoding="utf-8",
    )
    row = build_project(yaml_path, _codebook(), {}, repo_root=tmp_path)
    assert row is not None
    assert row["display_name"] == "Acme AI Policy"
