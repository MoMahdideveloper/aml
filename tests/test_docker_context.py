"""Production Docker build-context contract (no daemon required)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERIGNORE = ROOT / ".dockerignore"


def _patterns() -> list[str]:
    text = DOCKERIGNORE.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def test_dockerignore_excludes_non_runtime_trees():
    patterns = _patterns()
    joined = "\n".join(patterns)

    required = [
        "stitch_kpi_performance_dashboard",
        "graphify-out",
        "tests",
        "chroma_db",
        "node_modules",
        "platinum-heritage-runnable",
        "templates/_archive",
        "api",
        "matcher",
        "ingestor",
        "chatbot",
    ]
    missing = [p for p in required if p not in joined]
    assert not missing, f".dockerignore missing exclusions: {missing}"


def test_dockerignore_keeps_runtime_inputs_available():
    """Sanity: ignore file must not blanket-exclude templates/ or migrations/."""
    patterns = set(_patterns())
    # Exact excludes of entire runtime trees would break the image.
    forbidden = {"templates", "templates/", "migrations", "migrations/", "static", "static/"}
    bad = forbidden & patterns
    assert not bad, f".dockerignore must not exclude runtime trees: {bad}"


def test_required_runtime_paths_exist_on_disk():
    required = [
        "app.py",
        "main.py",
        "requirements.txt",
        "Dockerfile",
        "docker/entrypoint.sh",
        "templates/base.html",
        "templates/dashboard.html",
        "static/css/stitch.css",
        "migrations/env.py",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Missing runtime paths: {missing}"
