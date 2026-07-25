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


def _is_excluded(path: str) -> bool:
    """Resolve a repo-relative path against the allowlist .dockerignore.

    Docker semantics: patterns are evaluated in order, last match wins. A leading
    "!" re-includes. We only need the subset of syntax this file actually uses
    ("*", "name/", "**/x/", "dir/**", and "!" re-includes).
    """
    excluded = False
    for raw in _patterns():
        negate = raw.startswith("!")
        pattern = raw[1:] if negate else raw
        if _matches(pattern, path):
            excluded = not negate
    return excluded


def _matches(pattern: str, path: str) -> bool:
    pattern = pattern.rstrip("/")
    if pattern == "*":
        # "*" matches only top-level entries, which is what excludes sibling trees.
        return "/" not in path.rstrip("/")
    if pattern.startswith("**/"):
        tail = pattern[3:]
        return any(seg == tail for seg in path.split("/"))
    if pattern.endswith("/**"):
        head = pattern[:-3]
        return path == head or path.startswith(head + "/")
    return path == pattern or path.startswith(pattern + "/")


def test_dockerignore_excludes_non_runtime_trees():
    """Non-runtime trees must not reach the build context.

    Asserts the resolved outcome rather than the presence of denylist substrings:
    the ignore file is an allowlist ("*" then "!" re-includes), so an exclusion is
    correct when nothing re-includes it, not when its name appears in the file.
    """
    must_be_excluded = [
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
        ".env",
        "backups",
        "instance",
        ".git",
        ".venv",
    ]
    leaked = [p for p in must_be_excluded if not _is_excluded(p)]
    assert not leaked, f".dockerignore lets non-runtime paths into the context: {leaked}"


def test_dockerignore_admits_runtime_paths():
    """The allowlist must still admit everything the image needs to boot."""
    must_be_included = [
        "app.py",
        "main.py",
        "celery_app.py",
        "background_matcher.py",
        "vector_service.py",
        "requirements.txt",
        "templates/base.html",
        "static/css/stitch.css",
        "migrations/env.py",
        "docker/entrypoint.sh",
        "services/search_service.py",
        "utils/admin_auth.py",
    ]
    blocked = [p for p in must_be_included if _is_excluded(p)]
    assert not blocked, f".dockerignore excludes required runtime paths: {blocked}"


def test_dockerignore_is_lf_only():
    """CRLF silently breaks every pattern: Docker reads ".git\\r" and matches nothing.

    This is a real regression that made the build context 1.1GB despite correct
    patterns. core.autocrlf=true can reintroduce it, so .gitattributes pins LF.
    """
    raw = DOCKERIGNORE.read_bytes()
    assert b"\r" not in raw, ".dockerignore must be LF-only (CRLF disables all patterns)"


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
