# -*- coding: utf-8 -*-
"""Branded error page templates: 404.html and 500.html.

Asserts the dedicated branded error pages exist alongside the generic
error.html, share the Augur owl/gradient visual style, and that 500.html
extends base.html so the global layout/sidebar is rendered.
"""

import re
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "templates"


def _read(name: str) -> str:
    path = TEMPLATES_DIR / name
    assert path.exists(), f"Missing template: {path}"
    return path.read_text(encoding="utf-8")


class TestBrandedErrorPagesExist:
    """404.html and 500.html must be present in the templates directory."""

    @pytest.mark.parametrize("filename", ["404.html", "500.html"])
    def test_template_file_exists(self, filename):
        path = TEMPLATES_DIR / filename
        assert path.is_file(), f"{filename} must exist in dashboard/templates/"

    @pytest.mark.parametrize("filename", ["404.html", "500.html"])
    def test_template_non_empty(self, filename):
        text = _read(filename)
        assert text.strip(), f"{filename} must not be empty"

    @pytest.mark.parametrize("filename,code", [("404.html", "404"), ("500.html", "500")])
    def test_template_renders_status_code(self, filename, code):
        text = _read(filename)
        # Must surface the HTTP status code prominently (matches error.html style)
        assert code in text, f"{filename} must display the {code} status code"


class Test500InheritsBase:
    """500.html must extend base.html so the global layout is rendered."""

    def test_500_extends_base(self):
        text = _read("500.html")
        assert re.search(r'\{%\s*extends\s+"base\.html"\s*%\}', text), (
            "500.html must {% extends 'base.html' %} to inherit the global layout"
        )

    def test_500_has_content_block(self):
        text = _read("500.html")
        assert "{% block content %}" in text, "500.html must define a content block"
        assert "{% endblock %}" in text, "500.html must close its blocks"

    def test_404_extends_base(self):
        """404.html is also a full page; per task it should also extend base.html."""
        text = _read("404.html")
        assert re.search(r'\{%\s*extends\s+"base\.html"\s*%\}', text), (
            "404.html must {% extends 'base.html' %}"
        )


class TestBrandedErrorPagesStyle:
    """Both pages should match the established error.html visual style."""

    @pytest.mark.parametrize("filename", ["404.html", "500.html"])
    def test_uses_brand_owl_image(self, filename):
        text = _read(filename)
        assert "augur-owl" in text, f"{filename} must use the Augur owl brand image"

    @pytest.mark.parametrize("filename", ["404.html", "500.html"])
    def test_uses_dashboard_home_link(self, filename):
        text = _read(filename)
        assert 'href="/"' in text, f"{filename} must link back to the dashboard"

    @pytest.mark.parametrize("filename", ["404.html", "500.html"])
    def test_renders_error_heading(self, filename):
        text = _read(filename)
        assert "error-heading" in text, (
            f"{filename} must use the .error-heading class for visual consistency"
        )
