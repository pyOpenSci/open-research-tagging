"""10f: Playwright coding-view walkthrough against pyOpenSci fixture data.

Requires: pip install -e ".[dev]" && playwright install chromium
Alpine loads from CDN (network needed).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from open_research_tagging.coding_yaml import emit_coding_block
from open_research_tagging.project_yaml import emit_project_yaml

pytest.importorskip("playwright")
pytest.importorskip("pytest_playwright")

REPO = Path(__file__).resolve().parents[1]
PROJECT_YAML = REPO / "projects" / "pyopensci" / "project.yaml"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pyopensci_row(site_under_test: Path):
    payload = json.loads(
        (site_under_test / "data" / "projects.json").read_text(encoding="utf-8")
    )
    rows = [r for r in payload["data"] if r.get("slug") == "pyopensci"]
    assert rows, "expected pyopensci in projects.json"
    row = rows[0]
    assert row.get("coding"), "expected raw coding passthrough"
    return row


def test_projects_coding_link_opens_ready_view(page, site_base_url, pyopensci_row):
    page.goto(f"{site_base_url}/projects.html", wait_until="networkidle")
    page.wait_for_selector("#projectstable tbody tr")
    link = page.locator('a[href="coding.html?project=pyopensci"]')
    assert link.count() >= 1
    link.first.click()
    page.wait_for_url("**/coding.html?project=pyopensci")
    page.wait_for_selector("#coding-ready", state="visible")
    assert page.locator("#coding-form").is_visible()
    assert "pyOpenSci" in page.locator("#coding-ready").inner_text()


def test_coding_view_prefills_and_yaml_matches_python(
    page, site_base_url, pyopensci_row
):
    page.goto(
        f"{site_base_url}/coding.html?project=pyopensci",
        wait_until="networkidle",
    )
    page.wait_for_selector("#coding-ready", state="visible")
    page.wait_for_selector("#yaml-preview")

    expected = emit_project_yaml(
        slug=pyopensci_row["slug"],
        display_name=pyopensci_row.get("display_name"),
        provenance=pyopensci_row.get("provenance"),
        coding=pyopensci_row["coding"],
        files=pyopensci_row.get("files") or [],
    )
    page.wait_for_function(
        """(needle) => {
          const ta = document.getElementById('yaml-preview');
          return ta && ta.value.includes(needle);
        }""",
        arg=pyopensci_row["coding"]["stance"]["explicit"],
    )
    # Prefill: metadata + stance.explicit somewhere in the form selects
    assert page.locator("#meta-slug").input_value() == pyopensci_row["slug"]
    assert page.locator("#meta-files").is_visible()
    selects = page.locator("#coding-form select")
    values = [selects.nth(i).input_value() for i in range(selects.count())]
    assert pyopensci_row["coding"]["stance"]["explicit"] in values

    preview = page.locator("#yaml-preview").input_value()
    assert preview == expected
    assert preview.startswith("slug:")
    assert "provenance:\n" in preview
    assert "coding:\n" in preview
    assert "files:\n" in preview

    parsed = yaml.safe_load(preview)
    assert parsed["slug"] == pyopensci_row["slug"]
    assert (
        parsed["coding"]["stance"]["explicit"]
        == pyopensci_row["coding"]["stance"]["explicit"]
    )
    # coding subsection still matches emit_coding_block contract
    assert parsed["coding"] == yaml.safe_load(
        emit_coding_block(pyopensci_row["coding"])
    )["coding"]


def test_section_title_filters_evidence(page, site_base_url):
    page.goto(
        f"{site_base_url}/coding.html?project=pyopensci",
        wait_until="networkidle",
    )
    page.wait_for_selector("#coding-ready", state="visible")
    page.wait_for_selector("#evidence-list .evidence-card")

    all_count = page.locator("#evidence-list .evidence-card").count()
    assert all_count >= 1

    page.locator(".section-evidence-btn", has_text="Stance").click()
    page.wait_for_function(
        """() => {
          const sel = document.getElementById('evidence-dim');
          return sel && sel.value === 'stance';
        }"""
    )
    stance_count = page.locator("#evidence-list .evidence-card").count()
    assert 0 < stance_count <= all_count


def test_form_edit_updates_yaml_preview(page, site_base_url, pyopensci_row):
    page.goto(
        f"{site_base_url}/coding.html?project=pyopensci",
        wait_until="networkidle",
    )
    page.wait_for_selector("#yaml-preview")
    before = page.locator("#yaml-preview").input_value()
    stance_ex = pyopensci_row["coding"]["stance"]["explicit"]
    assert stance_ex in before

    # Stance.explicit select (skip policy_location in metadata)
    page.locator("#coding-form select").nth(1).select_option("permissive")
    page.wait_for_function(
        """() => {
          const ta = document.getElementById('yaml-preview');
          return ta && ta.value.includes('explicit: permissive\\n');
        }"""
    )
    after = page.locator("#yaml-preview").input_value()
    assert "explicit: permissive\n" in after
    assert after != before


def test_disk_project_yaml_coding_matches_site_passthrough(pyopensci_row):
    """Seed coherence: projects.json coding agrees with project.yaml."""
    on_disk = yaml.safe_load(PROJECT_YAML.read_text(encoding="utf-8"))["coding"]
    # Emit both — formatting may differ from hand-written YAML; structure must match
    assert emit_coding_block(on_disk) == emit_coding_block(pyopensci_row["coding"])
