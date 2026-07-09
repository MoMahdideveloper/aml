"""
Verify live CRM templates exist and compile (no Stitch export coupling).
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

CORE = [
    "dashboard.html",
    "properties.html",
    "customers.html",
    "deals.html",
    "tasks.html",
    "agents.html",
    "recommendations.html",
]


def test_core_templates_exist_and_are_jinja():
    for name in CORE:
        path = TEMPLATES / name
        assert path.is_file(), f"Missing live template: {name}"
        assert path.stat().st_size > 0
        content = path.read_text(encoding="utf-8")
        assert any(tok in content for tok in ("{{", "{%")), f"{name} should use Jinja"
        assert "class=" in content


def test_base_shell_structure():
    base = TEMPLATES / "base.html"
    assert base.is_file()
    content = base.read_text(encoding="utf-8").lower()
    assert "<html" in content and "</html>" in content


def test_no_core_template_only_under_archive():
    archive = TEMPLATES / "_archive"
    for name in CORE:
        live = TEMPLATES / name
        assert live.is_file(), f"{name} must exist outside _archive"
        if (archive / name).exists():
            assert live.resolve() != (archive / name).resolve()


def test_core_templates_compile(app, db_setup):
    with app.app_context():
        for name in CORE + ["base.html"]:
            app.jinja_env.get_template(name)


if __name__ == "__main__":
    pytest.main([__file__])
