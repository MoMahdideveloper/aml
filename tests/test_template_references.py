"""Canonical runtime template reference audit (Track A only).

Proves every Flask-rendered template and live Jinja dependency resolves under
`templates/` and never under `templates/_archive/` or Stitch export trees.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
ARCHIVE = TEMPLATES / "_archive"
STITCH = ROOT / "stitch_kpi_performance_dashboard"

# Source trees that constitute the live app (exclude Track B + snapshots).
SCAN_DIRS = [
    ROOT / "views",
    ROOT / "error_handlers.py",
    ROOT / "app.py",
]

JINJA_REF = re.compile(
    r"""\{%\s*(?:extends|include|from|import)\s+["']([^"']+)["']""",
    re.MULTILINE,
)
# Optional: {% include var %} — only string literals are audited.
RENDER_CALL = re.compile(
    r"""render_template\(\s*["']([^"']+)["']""",
    re.MULTILINE,
)


def _iter_python_sources() -> list[Path]:
    files: list[Path] = []
    for item in SCAN_DIRS:
        if item.is_file() and item.suffix == ".py":
            files.append(item)
        elif item.is_dir():
            files.extend(sorted(item.rglob("*.py")))
    return files


def _render_template_names_from_ast(path: Path) -> set[str]:
    """Collect string-literal first args of render_template(...)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name) and func.id == "render_template":
            name = "render_template"
        elif isinstance(func, ast.Attribute) and func.attr == "render_template":
            name = "render_template"
        if name != "render_template" or not node.args:
            continue
        arg0 = node.args[0]
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            found.add(arg0.value)
    return found


def _render_template_names_regex(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return set(RENDER_CALL.findall(text))


def collect_direct_render_templates() -> set[str]:
    names: set[str] = set()
    for path in _iter_python_sources():
        names |= _render_template_names_from_ast(path)
        # Regex backup for edge cases AST might miss
        names |= _render_template_names_regex(path)
    return names


def _normalize_template_name(name: str) -> str:
    return name.replace("\\", "/").lstrip("/")


def template_path(name: str) -> Path:
    return TEMPLATES / _normalize_template_name(name)


def collect_jinja_deps(entry_names: set[str]) -> set[str]:
    """BFS over extends/include/import from entry templates (live tree only)."""
    seen: set[str] = set()
    queue = [ _normalize_template_name(n) for n in entry_names ]
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        path = template_path(name)
        if not path.is_file():
            continue
        # Do not walk into archive or outside templates
        try:
            path.resolve().relative_to(TEMPLATES.resolve())
        except ValueError:
            continue
        if ARCHIVE in path.parents or path == ARCHIVE:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for ref in JINJA_REF.findall(text):
            ref_n = _normalize_template_name(ref)
            if ref_n.startswith("_archive/"):
                continue
            if ref_n not in seen:
                queue.append(ref_n)
    return seen


def test_every_render_template_exists_outside_archive():
    names = collect_direct_render_templates()
    assert names, "Expected at least one render_template() reference in views/"

    missing = []
    archived = []
    stitch_refs = []
    for name in sorted(names):
        n = _normalize_template_name(name)
        if n.startswith("stitch_kpi") or "stitch_kpi_performance_dashboard" in n:
            stitch_refs.append(n)
            continue
        if n.startswith("_archive/"):
            archived.append(n)
            continue
        path = template_path(n)
        if not path.is_file():
            missing.append(n)
        else:
            # Resolve must not live under archive
            resolved = path.resolve()
            if ARCHIVE.resolve() in resolved.parents or resolved == ARCHIVE.resolve():
                archived.append(n)

    assert not stitch_refs, (
        "Runtime code must not render Stitch export HTML: " + ", ".join(stitch_refs)
    )
    assert not archived, (
        "Runtime code must not render archived templates: " + ", ".join(archived)
    )
    assert not missing, (
        "Missing live templates referenced by render_template(): " + ", ".join(missing)
    )


def test_jinja_dependencies_resolve_for_live_entries():
    entries = {
        n
        for n in collect_direct_render_templates()
        if not n.startswith("_archive/")
        and "stitch_kpi" not in n
    }
    all_deps = collect_jinja_deps(entries)
    missing = []
    for name in sorted(all_deps):
        if name.startswith("_archive/"):
            continue
        if not template_path(name).is_file():
            missing.append(name)
    assert not missing, "Unresolved Jinja dependencies: " + ", ".join(missing)


def test_archive_is_not_required_runtime_set():
    """Archive may exist on disk but is never part of canonical runtime entries."""
    entries = collect_direct_render_templates()
    for name in entries:
        assert not _normalize_template_name(name).startswith("_archive/"), name


def test_live_templates_compile(app, db_setup):
    """Compile every template discovered from render_template + Jinja graph."""
    entries = {
        n
        for n in collect_direct_render_templates()
        if "stitch_kpi" not in n and not n.startswith("_archive/")
    }
    names = collect_jinja_deps(entries)
    with app.app_context():
        env = app.jinja_env
        failed = []
        for name in sorted(names):
            if not template_path(name).is_file():
                continue
            try:
                env.get_template(name)
            except Exception as exc:  # noqa: BLE001 — collect all failures
                failed.append(f"{name}: {exc}")
        assert not failed, "Jinja compile failures:\n" + "\n".join(failed)


def test_core_templates_exist_for_ui_shell():
    required = [
        "base.html",
        "dashboard.html",
        "properties.html",
        "customers.html",
        "deals.html",
        "tasks.html",
        "agents.html",
        "recommendations.html",
        "components/_sidebar.html",
        "components/_mobile_header.html",
    ]
    missing = [n for n in required if not template_path(n).is_file()]
    assert not missing, f"Missing shell templates: {missing}"
