"""Shared site assets exist; filter dims follow codebook.json (no hardcoded list)."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"
CODEBOOK_JSON = SITE / "data" / "codebook.json"


def test_shared_css_and_js_exist():
    assert (SITE / "css" / "site.css").is_file()
    assert (SITE / "js" / "codebook.js").is_file()
    assert (SITE / "js" / "chips.js").is_file()
    assert (SITE / "index.html").is_file()
    assert (SITE / "projects.html").is_file()


def test_pages_link_shared_assets_not_inline_filter_dims():
    index_html = (SITE / "index.html").read_text(encoding="utf-8")
    projects_html = (SITE / "projects.html").read_text(encoding="utf-8")
    for html in (index_html, projects_html):
        assert 'href="css/site.css"' in html
        assert 'src="js/codebook.js"' in html
        assert "FILTER_DIMS" not in html
        assert "filterDimensionsFromCodebook" in html


def test_codebook_js_exports_filter_helper():
    js = (SITE / "js" / "codebook.js").read_text(encoding="utf-8")
    assert "filterDimensionsFromCodebook" in js
    assert "filter_order" in js
    assert "OrtCodebook" in js


def test_codebook_json_filter_order_drives_expected_dims():
    data = json.loads(CODEBOOK_JSON.read_text(encoding="utf-8"))
    order = data["filter_order"]
    assert "stance" in order
    assert "scope" in order
    # Labels available via namespaces for each filter_order entry
    dims = {m["dimension"] for m in data["namespaces"].values()}
    for key in order:
        assert key in dims or key in (data.get("values") or {}) or key == "scope"


def test_site_css_defines_chrome_tokens():
    css = (SITE / "css" / "site.css").read_text(encoding="utf-8")
    assert re.search(r"--accent:", css)
    assert "nav.top" in css
    assert ".chip" in css
