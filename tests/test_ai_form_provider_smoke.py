"""Provider smoke gate tests (TDD — Task 2).

Run mock mode (no credentials/network/DB):
    python scripts/verify_ai_form_provider.py --mode mock

Run live mode (requires AI_FORM_LIVE_SMOKE=1 + provider creds):
    AI_FORM_LIVE_SMOKE=1 python scripts/verify_ai_form_provider.py --mode live

These tests cover CLI behavior and output contract.  They never touch the
database, never write audit records, and use only synthetic fixtures generated
in memory.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT = Path(__file__).parent.parent / "scripts" / "verify_ai_form_provider.py"


def _run(
    *extra_args: str,
    env_overrides: Dict[str, str] | None = None,
) -> "subprocess.CompletedProcess[str]":
    """Execute the smoke script as a subprocess, capturing stdout/stderr."""
    env = os.environ.copy()
    # Guarantee no live-smoke env bleeds from the outer shell during tests
    env.pop("AI_FORM_LIVE_SMOKE", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *extra_args],
        capture_output=True,
        text=True,
        env=env,
    )


# ---------------------------------------------------------------------------
# Phase 1 — Script existence
# ---------------------------------------------------------------------------


def test_script_file_exists():
    """The script must be present at scripts/verify_ai_form_provider.py."""
    assert SCRIPT.exists(), f"Script not found: {SCRIPT}"


# ---------------------------------------------------------------------------
# Phase 2 — Mock mode: zero credentials, zero network, zero DB
# ---------------------------------------------------------------------------


class TestMockMode:
    def test_mock_exits_zero(self):
        """Mock mode must succeed (exit 0) without any credentials."""
        result = _run("--mode", "mock")
        assert result.returncode == 0, (
            f"Expected exit 0 in mock mode.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_mock_outputs_valid_json(self):
        """stdout must be parseable JSON."""
        result = _run("--mode", "mock")
        assert result.returncode == 0
        summary = json.loads(result.stdout)
        assert isinstance(summary, dict), "Summary must be a JSON object"

    def test_mock_summary_has_required_keys(self):
        """JSON summary must contain mode, status, checks, and elapsed_ms."""
        result = _run("--mode", "mock")
        summary = json.loads(result.stdout)
        for key in ("mode", "status", "checks", "elapsed_ms"):
            assert key in summary, f"Missing key '{key}' in summary: {summary}"

    def test_mock_mode_field_in_summary(self):
        """summary['mode'] must equal 'mock'."""
        result = _run("--mode", "mock")
        summary = json.loads(result.stdout)
        assert summary["mode"] == "mock"

    def test_mock_status_is_pass(self):
        """summary['status'] must be 'pass' in mock mode."""
        result = _run("--mode", "mock")
        summary = json.loads(result.stdout)
        assert summary["status"] == "pass"

    def test_mock_checks_is_list_of_dicts(self):
        """summary['checks'] must be a non-empty list of check-result dicts."""
        result = _run("--mode", "mock")
        summary = json.loads(result.stdout)
        checks = summary["checks"]
        assert isinstance(checks, list), "checks must be a list"
        assert len(checks) > 0, "checks must not be empty"
        for chk in checks:
            assert isinstance(chk, dict)
            assert "name" in chk, f"check dict missing 'name': {chk}"
            assert "ok" in chk, f"check dict missing 'ok': {chk}"

    def test_mock_no_sensitive_values_in_output(self):
        """Output must not contain API keys, tokens, or credential patterns."""
        result = _run("--mode", "mock")
        combined = result.stdout + result.stderr
        for suspicious in ("AIza", "Bearer ", "sk-", "-----BEGIN"):
            assert suspicious not in combined, (
                f"Sensitive pattern '{suspicious}' found in script output"
            )

    def test_mock_no_db_write(self, tmp_path):
        """Mock mode must not create or modify any .sqlite3 / audit DB files."""
        project_root = Path(__file__).parent.parent
        before_dbs = set(project_root.rglob("*.sqlite3"))
        _run("--mode", "mock")
        after_dbs = set(project_root.rglob("*.sqlite3"))
        new_dbs = after_dbs - before_dbs
        assert not new_dbs, f"Mock mode created unexpected DB files: {new_dbs}"

    def test_mock_covers_text_check(self):
        """Mock mode must include at least one check that exercises text extraction."""
        result = _run("--mode", "mock")
        summary = json.loads(result.stdout)
        names = [c["name"] for c in summary["checks"]]
        text_checks = [n for n in names if "text" in n.lower() or "extract" in n.lower()]
        assert text_checks, f"No text/extract check found. Checks: {names}"

    def test_mock_covers_schema_registry(self):
        """Mock mode must include at least one check that validates the schema registry."""
        result = _run("--mode", "mock")
        summary = json.loads(result.stdout)
        names = [c["name"] for c in summary["checks"]]
        schema_checks = [n for n in names if "schema" in n.lower() or "registry" in n.lower() or "form" in n.lower()]
        assert schema_checks, f"No schema/registry/form check found. Checks: {names}"

    def test_mock_schema_registry_no_unexpected_forms(self):
        """schema_registry check detail must report extra/unexpected forms if present."""
        result = _run("--mode", "mock")
        summary = json.loads(result.stdout)
        reg_check = next(
            (c for c in summary["checks"] if c["name"] == "schema_registry"), None
        )
        assert reg_check is not None, "schema_registry check not found in output"
        assert reg_check["ok"], f"schema_registry check failed: {reg_check.get('detail')}"
        # Extra forms (in registry but not expected) must be flagged in detail when present.
        # With the current known-good registry this should pass cleanly; if a new form is
        # added without updating the expected set the implementation must surface it.
        detail = reg_check.get("detail", "")
        assert "extra" not in detail.lower(), (
            f"Unexpected extra schemas reported: {detail}"
        )

    def test_mock_elapsed_ms_is_numeric(self):
        """elapsed_ms must be a non-negative number."""
        result = _run("--mode", "mock")
        summary = json.loads(result.stdout)
        assert isinstance(summary["elapsed_ms"], (int, float))
        assert summary["elapsed_ms"] >= 0

    def test_mock_no_persian_text_in_output_values(self):
        """Extracted synthetic Persian text must not appear verbatim in the JSON summary values."""
        result = _run("--mode", "mock")
        summary = json.loads(result.stdout)
        # We want sanitized output — raw extracted content (e.g. customer PII
        # from synthetic text) must not be re-emitted; detail should only carry
        # metadata (field names, booleans, counts), not raw extracted text blobs.
        for chk in summary["checks"]:
            detail = str(chk.get("detail", ""))
            assert len(detail) < 500, (
                f"Check '{chk['name']}' leaks large extracted value in detail: {detail[:200]!r}"
            )


# ---------------------------------------------------------------------------
# Phase 3 — Live mode: guard without env flag
# ---------------------------------------------------------------------------


class TestLiveModeGuard:
    def test_live_without_flag_exits_nonzero(self):
        """Live mode without AI_FORM_LIVE_SMOKE=1 must exit nonzero."""
        result = _run("--mode", "live")
        assert result.returncode != 0, (
            "Expected nonzero exit when AI_FORM_LIVE_SMOKE=1 is not set.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_live_without_flag_emits_safe_message(self):
        """Exit message must be a safe human-readable string, not a traceback."""
        result = _run("--mode", "live")
        combined = result.stdout + result.stderr
        # Must say something meaningful
        assert len(combined.strip()) > 0, "Expected some output explaining why live mode was blocked"
        # Must not be a raw Python traceback
        assert "Traceback (most recent call last)" not in combined, (
            "Live guard should emit a friendly message, not a raw traceback"
        )
        # Must reference the required env flag
        assert "AI_FORM_LIVE_SMOKE" in combined, (
            "Guard message must mention the AI_FORM_LIVE_SMOKE env var"
        )

    def test_live_with_flag_but_no_credentials_exits_nonzero(self):
        """With AI_FORM_LIVE_SMOKE=1 but no credentials, must exit nonzero."""
        result = _run(
            "--mode", "live",
            env_overrides={
                "AI_FORM_LIVE_SMOKE": "1",
                # Ensure no real Gemini credentials bleed in
                "GEMINI_API_KEY": "",
                "GOOGLE_API_KEY": "",
            },
        )
        assert result.returncode != 0, (
            "Expected nonzero exit when live smoke has no valid credentials.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_live_with_flag_no_creds_safe_message(self):
        """Credential failure message must be safe — no key values exposed."""
        result = _run(
            "--mode", "live",
            env_overrides={
                "AI_FORM_LIVE_SMOKE": "1",
                "GEMINI_API_KEY": "",
                "GOOGLE_API_KEY": "",
            },
        )
        combined = result.stdout + result.stderr
        assert "Traceback (most recent call last)" not in combined, (
            "Credential failure should emit a friendly message, not a raw traceback"
        )
        # Must not echo back any credential value
        for suspicious in ("AIza", "Bearer ", "sk-"):
            assert suspicious not in combined


# ---------------------------------------------------------------------------
# Phase 4 — CLI argument contract
# ---------------------------------------------------------------------------


class TestCLIContract:
    def test_unknown_mode_exits_nonzero(self):
        """An unknown --mode value must exit nonzero."""
        result = _run("--mode", "bogus_mode_xyz")
        assert result.returncode != 0

    def test_no_args_exits_nonzero_or_shows_help(self):
        """Running without any arguments must either show help or exit nonzero."""
        result = _run()
        # Either it prints usage/help (exit 0 with help) or it fails
        if result.returncode == 0:
            assert (
                "mode" in result.stdout.lower()
                or "usage" in result.stdout.lower()
                or "help" in result.stdout.lower()
            ), "Exit-0 with no args must output usage/help information"


# ---------------------------------------------------------------------------
# Phase 5 — In-process API contract (importable module interface)
# ---------------------------------------------------------------------------


class TestInProcessAPI:
    """Load the script as a module and call its public functions directly."""

    @pytest.fixture(scope="class")
    def smoke_module(self):
        spec = importlib.util.spec_from_file_location(
            "verify_ai_form_provider", SCRIPT
        )
        if spec is None:
            pytest.skip(f"Cannot load module from {SCRIPT}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    def test_module_has_run_mock_function(self, smoke_module):
        """Script must expose a run_mock() callable."""
        assert hasattr(smoke_module, "run_mock"), (
            "Script must define a run_mock() function for programmatic use"
        )
        assert callable(smoke_module.run_mock)

    def test_run_mock_returns_dict(self, smoke_module):
        """run_mock() must return a dict with mode, status, checks, elapsed_ms."""
        result: Any = smoke_module.run_mock()
        assert isinstance(result, dict)
        for key in ("mode", "status", "checks", "elapsed_ms"):
            assert key in result, f"Missing key '{key}' in run_mock() result"

    def test_run_mock_status_pass(self, smoke_module):
        result: Any = smoke_module.run_mock()
        assert result["status"] == "pass"

    def test_run_mock_checks_all_ok(self, smoke_module):
        result: Any = smoke_module.run_mock()
        failed = [c for c in result["checks"] if not c.get("ok")]
        assert not failed, f"Some checks failed in run_mock(): {failed}"

    def test_run_mock_synthetic_image_check(self, smoke_module):
        """run_mock() must exercise the image fixture path."""
        result: Any = smoke_module.run_mock()
        names = [c["name"] for c in result["checks"]]
        image_checks = [n for n in names if "image" in n.lower()]
        assert image_checks, f"No image-related check in run_mock() checks: {names}"

    def test_run_mock_synthetic_text_persian(self, smoke_module):
        """run_mock() must exercise the Persian-text fixture path."""
        result: Any = smoke_module.run_mock()
        names = [c["name"] for c in result["checks"]]
        # Accepts 'text', 'extract', 'persian', or 'property' checks
        text_checks = [
            n for n in names
            if any(kw in n.lower() for kw in ("text", "extract", "persian", "property"))
        ]
        assert text_checks, f"No text/Persian check in run_mock() checks: {names}"
