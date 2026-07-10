"""CI/CD helper scripts and workflow safety (no network deploy)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        **kwargs,
    )


def test_workflow_safety_script_ok():
    proc = _run(["scripts/ci/assert_workflow_safety.py"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "WORKFLOW_SAFETY_OK" in proc.stdout


def test_deploy_workflows_are_manual_only():
    wf = ROOT / ".github" / "workflows"
    for name in ("deploy-staging.yml", "deploy-production.yml", "rollback.yml"):
        text = (wf / name).read_text(encoding="utf-8")
        assert "workflow_dispatch" in text
        # No unrestricted push trigger
        assert "push:" not in text or "tags:" in text


def test_ci_permissions_are_read_contents():
    text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "permissions:" in text
    assert "contents: read" in text


def test_release_metadata_writes_json(tmp_path):
    out = tmp_path / "meta.json"
    proc = _run(["scripts/ci/release_metadata.py", "--out", str(out)])
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["track"] == "A"
    assert data["python_requires"] == "3.11"
    assert "git_sha" in data
    assert "password" not in json.dumps(data).lower() or "not" in data.get("notes", "")


def test_migration_preflight_offline():
    # Allow destructive patterns in historical migrations for offline OK path when flagged
    proc = _run(["scripts/ci/migration_preflight.py", "--allow-destructive"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "status=ok" in proc.stdout


def test_post_deploy_verify_fails_unreachable():
    proc = _run(
        [
            "scripts/ci/post_deploy_verify.py",
            "--base-url",
            "http://127.0.0.1:1",
            "--timeout",
            "3",
        ]
    )
    assert proc.returncode == 1


def test_dockerfile_pins_python_311_and_nonroot():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.11" in text
    assert "USER appuser" in text
    assert "HEALTHCHECK" in text
    assert "tailwind-ph.css" in text


def test_dockerignore_excludes_secrets_and_track_b():
    text = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    for token in (".env", "chroma_db", "api", "matcher", "ingestor", "chatbot", "tests"):
        assert token in text
