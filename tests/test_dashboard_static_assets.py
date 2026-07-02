# -*- coding: utf-8 -*-
"""Dashboard static-asset wiring audit (Round 5 Agent D).

Verifies that the critical static assets referenced by the dashboard
templates are present, that the robots.txt and sitemap.xml routes are
exposed by the FastAPI app, and that the base template's <link>/<script>
references resolve to real files on disk.  Without these, browsers will
log 404s in the console and crawlers have no guidance.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app

STATIC_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "static"
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "templates"
BASE_HTML = TEMPLATES_DIR / "base.html"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestStaticDirectoryLayout:
    """The /static tree must contain css/, js/, images/ subdirectories."""

    def test_static_dir_exists(self):
        assert STATIC_DIR.is_dir(), f"missing {STATIC_DIR}"

    @pytest.mark.parametrize("subdir", ["css", "js", "images"])
    def test_subdir_exists(self, subdir):
        assert (STATIC_DIR / subdir).is_dir(), f"missing {STATIC_DIR / subdir}"


class TestLinkedAssetsResolve:
    """Every <link href=/static/...> and <script src=/static/...> in base.html
    must point to a file that actually exists on disk."""

    @pytest.fixture(scope="class")
    def base_html_text(self):
        assert BASE_HTML.is_file(), f"missing {BASE_HTML}"
        return BASE_HTML.read_text(encoding="utf-8")

    def _extract_static_refs(self, html, pattern):
        import re
        return re.findall(pattern, html)

    def test_css_assets_resolve(self, base_html_text):
        import re
        css_refs = re.findall(r'href="(/static/css/[^"?]+\.css)(?:\?[^"]*)?"', base_html_text)
        assert css_refs, "base.html should reference at least one /static/css file"
        for ref in css_refs:
            rel = ref.lstrip("/")
            assert (STATIC_DIR.parent / rel).is_file(), f"css asset missing on disk: {ref}"

    def test_js_assets_resolve(self, base_html_text):
        import re
        js_refs = re.findall(r'src="(/static/js/[^"?]+\.js)(?:\?[^"]*)?"', base_html_text)
        assert js_refs, "base.html should reference at least one /static/js file"
        for ref in js_refs:
            rel = ref.lstrip("/")
            assert (STATIC_DIR.parent / rel).is_file(), f"js asset missing on disk: {ref}"

    def test_favicon_resolves(self, base_html_text):
        import re
        fav = re.search(r'href="(/static/images/favicon\.[a-z]+)"', base_html_text)
        assert fav, "base.html must declare a favicon link"
        rel = fav.group(1).lstrip("/")
        assert (STATIC_DIR.parent / rel).is_file(), f"favicon missing on disk: {fav.group(1)}"


class TestRobotsAndSitemapRoutes:
    """/robots.txt and /sitemap.xml must be served by the FastAPI app."""

    def test_robots_txt_endpoint(self, client):
        r = client.get("/robots.txt")
        assert r.status_code == 200, f"robots.txt returned {r.status_code}"
        assert "User-agent" in r.text
        assert "Allow" in r.text

    def test_sitemap_xml_endpoint(self, client):
        r = client.get("/sitemap.xml")
        assert r.status_code == 200, f"sitemap.xml returned {r.status_code}"
        assert "<urlset" in r.text
        assert "<loc>" in r.text

    def test_static_favicon_served(self, client):
        r = client.get("/static/images/favicon.png")
        assert r.status_code == 200, f"favicon.png returned {r.status_code}"
        assert r.headers.get("content-type", "").startswith("image/")

    def test_base_css_served(self, client):
        r = client.get("/static/css/layout.css")
        assert r.status_code == 200, f"layout.css returned {r.status_code}"
        assert "text/css" in r.headers.get("content-type", "")

    def test_i18n_js_served(self, client):
        r = client.get("/static/js/i18n.js")
        assert r.status_code == 200, f"i18n.js returned {r.status_code}"
        assert "javascript" in r.headers.get("content-type", "")
