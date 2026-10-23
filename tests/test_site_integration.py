"""Playwright site parity (8d): browse behavior against fixture JSON.

Requires: pip install -e ".[dev]" && playwright install chromium
Pages load Alpine/jQuery/DataTables from CDNs (network needed).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytest.importorskip("pytest_playwright")

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"
COMMENTS_JSON = SITE / "data" / "comments.json"
PROJECTS_JSON = SITE / "data" / "projects.json"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def fixture_meta():
    comments = json.loads(COMMENTS_JSON.read_text(encoding="utf-8"))
    projects = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
    assert comments["meta"]["is_fixture"] is True
    row0 = comments["data"][0]
    stance = projects["data"][0]["overall"]["stance"]["values"][0]
    return {
        "comment_count": len(comments["data"]),
        "project": row0["project"],
        "filter_key": row0["filter_keys"][0],
        "matching_href": stance["links"]["matching"]["href"],
        "display_name": projects["data"][0]["display_name"],
    }


def test_comments_shows_fixture_banner_and_rows(page, site_base_url, fixture_meta):
    page.goto(f"{site_base_url}/index.html", wait_until="networkidle")
    page.wait_for_selector("#commentstable tbody tr")
    assert page.locator("#fixture-banner").is_visible()
    rows = page.locator("#commentstable tbody tr")
    assert rows.count() == fixture_meta["comment_count"]
    assert page.locator(".passage-wrap").count() >= 1


def test_comments_url_filter_narrows_rows(page, site_base_url, fixture_meta):
    project = fixture_meta["project"]
    filt = fixture_meta["filter_key"]
    page.goto(
        f"{site_base_url}/index.html?project={project}&filter={filt}",
        wait_until="networkidle",
    )
    page.wait_for_selector("#url-filter-banner")
    assert page.locator("#url-filter-banner").is_visible()
    page.wait_for_function(
        """() => {
          const rows = document.querySelectorAll('#commentstable tbody tr');
          if (!rows.length) return false;
          // DataTables may leave a single 'no data' row; require real data cells
          return rows.length >= 1 && !rows[0].classList.contains('dataTables_empty');
        }"""
    )
    visible = page.locator("#commentstable tbody tr").filter(
        has_not=page.locator("td.dataTables_empty")
    )
    assert 0 < visible.count() < fixture_meta["comment_count"]


def test_comments_needs_tag_review_url_banner(page, site_base_url):
    page.goto(
        f"{site_base_url}/index.html?needs_tag_review=1",
        wait_until="networkidle",
    )
    page.wait_for_selector("#url-filter-banner")
    assert "needs_tag_review" in page.locator("#url-filter-banner").inner_text()
    # Fixture has no flagged rows → DataTables empty cell (class is on td, not tr)
    page.wait_for_selector("#commentstable tbody td.dataTables_empty")


def test_projects_table_and_evidence_link(page, site_base_url, fixture_meta):
    page.goto(f"{site_base_url}/projects.html", wait_until="networkidle")
    page.wait_for_selector("#projectstable tbody tr")
    assert fixture_meta["display_name"] in page.locator("#projectstable").inner_text()
    pill = page.locator(".code-pill").first
    pill.focus()
    link = page.locator(".code-pill .pop a").first
    href = link.get_attribute("href")
    assert href is not None
    assert href.startswith("index.html?project=")
    assert "filter=" in href or "dimension=" in href or "scope_type=" in href


def test_projects_chip_filter_and_nav_to_comments(page, site_base_url, fixture_meta):
    page.goto(f"{site_base_url}/projects.html", wait_until="networkidle")
    page.wait_for_selector("#dim-filters details.dim-block")
    # Chips live inside collapsed <details>; open first block then click a chip
    page.locator("#dim-filters details.dim-block").first.locator("summary").click()
    chip = page.locator("#dim-filters details.dim-block[open] .chip").first
    chip.click()
    page.wait_for_function(
        """() => {
          const meta = document.getElementById('meta');
          return meta && /of \\d+ projects shown/.test(meta.textContent || '');
        }"""
    )
    page.locator("nav.top a[href='index.html']").click()
    page.wait_for_url("**/index.html")
    page.wait_for_selector("#commentstable tbody tr")
    assert page.locator("#fixture-banner").is_visible()


def test_matching_evidence_href_opens_filtered_comments(
    page, site_base_url, fixture_meta
):
    href = fixture_meta["matching_href"]
    page.goto(f"{site_base_url}/{href}", wait_until="networkidle")
    page.wait_for_selector("#url-filter-banner")
    assert page.locator("#url-filter-banner").is_visible()
    page.wait_for_selector("#commentstable tbody tr")
    visible = page.locator("#commentstable tbody tr").filter(
        has_not=page.locator("td.dataTables_empty")
    )
    assert visible.count() >= 1
    assert visible.count() < fixture_meta["comment_count"]
