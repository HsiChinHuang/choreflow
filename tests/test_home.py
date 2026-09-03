from django.template.loader import render_to_string
from pathlib import Path
from django.conf import settings


def test_base_template_renders():
    html = render_to_string("base.html")
    assert "<!DOCTYPE html>" in html
    assert "ChoreFlow" in html


def test_base_template_has_bootstrap():
    html = render_to_string("base.html")
    assert "cdn.jsdelivr.net/npm/bootstrap" in html


def test_base_template_defines_blocks():
    """Verify base.html defines title, content, and extra_js blocks."""
    base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
    source = base_template_path.read_text()
    assert "{% block title %}" in source
    assert "{% block content %}" in source
    assert "{% block extra_js %}" in source


def test_base_template_has_navbar():
    html = render_to_string("base.html")
    assert 'navbar' in html
    assert "ChoreFlow" in html
