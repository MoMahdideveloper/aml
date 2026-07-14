"""TDD tests for the staging release rehearsal coordinator.

No network calls, no real DB connections, no paid API calls, no subprocess
destructive actions. All subprocesses are injected via a fake runner.

RED phase: write failing tests first, then implement to GREEN.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import staging_release_rehearsal as srr  # noqa: E402


# ---------------------------------------------------------------------------
# Fake runner: records calls, returns configurable results
# ---------------------------------------------------------------------------

class FakeRunner:
    """Injected runner that records every call without spawning real processes."""

    def __init__(self, default_rc: int = 0, default_stdout: str = "ok", default_stderr: str = ""):
        self.calls: list[dict] = []
        self.default_rc = default_rc
        self.default_stdout = default_stdout
        self.default_stderr = default_stderr
        self._overrides: dict[str, tuple[int, str, str]] = {}

    def set_override(self, keyword: str, rc: int, stdout: str = "", stderr: str = "") -> None:
        """Return specific result when cmd contains keyword."""
        self._overrides[keyword] = (rc, stdout, stderr)

    def __call__(self, cmd: list[str], env: dict | None = None) -> tuple[int, str, str]:
        self.calls.append({"cmd": cmd, "env": env})
        joined = " ".join(cmd)
        for kw, result in self._overrides.items():
            if kw in joined:
                return result
        return self.default_rc, self.default_stdout, self.default_stderr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _disposable_config(**overrides) -> srr.RehearsalConfig:
    """Minimal safe disposable config for tests."""
    base = dict(
        target_db="gptvli_rehearsal_drill",
        target_host="127.0.0.1",
        target_port=5432,
        backup_dest="/tmp/rehearsal_backups",
        uploads_source="/tmp/rehearsal_uploads",
        base_url="http://127.0.0.1:8000",
        dry_run=True,
        live=False,
        opt_in=True,
    )
    base.update(overrides)
    return srr.RehearsalConfig(**base)


# ---------------------------------------------------------------------------
# Contract: opt-in and safety guards
# ---------------------------------------------------------------------------

def test_refuses_missing_opt_in():
    """Coordinator must refuse when opt_in is False."""
    cfg = _disposable_config(opt_in=False)
    with pytest.raises(srr.RehearsalRefused, match="opt.in"):
        srr.RehearsalCoordinator(cfg)


def test_refuses_production_looking_target_db_production():
    cfg = _disposable_config(target_db="production_db")
    with pytest.raises(srr.RehearsalRefused, match="production"):
        srr.RehearsalCoordinator(cfg)


def test_refuses_production_looking_target_db_prod_prefix():
    cfg = _disposable_config(target_db="prod-db")
    # Match the actual marker text reported in the error message.
    with pytest.raises(srr.RehearsalRefused, match=r"prod.db"):
        srr.RehearsalCoordinator(cfg)


def test_refuses_production_looking_host_rds():
    cfg = _disposable_config(target_host="myapp.rds.amazonaws.com")
    with pytest.raises(srr.RehearsalRefused, match="production"):
        srr.RehearsalCoordinator(cfg)


def test_refuses_production_looking_host_azure():
    cfg = _disposable_config(target_host="myapp.database.azure.com")
    with pytest.raises(srr.RehearsalRefused, match="production"):
        srr.RehearsalCoordinator(cfg)


def test_refuses_system_db_names():
    for name in ("postgres", "template0", "template1"):
        cfg = _disposable_config(target_db=name)
        with pytest.raises(srr.RehearsalRefused, match="system"):
            srr.RehearsalCoordinator(cfg)


def test_refuses_live_without_explicit_live_flag():
    """Running with dry_run=False but live=False must be refused at run()."""
    cfg = _disposable_config(dry_run=False, live=False)
    coord = srr.RehearsalCoordinator(cfg)
    with pytest.raises(srr.RehearsalRefused, match="live"):
        coord.run()


def test_refuses_non_local_base_url_in_live_mode():
    """Live mode must refuse base_url pointing at non-localhost hosts."""
    cfg = _disposable_config(
        dry_run=False,
        live=True,
        base_url="https://staging.example.com",
    )
    with pytest.raises(srr.RehearsalRefused, match="disposable|local"):
        srr.RehearsalCoordinator(cfg)


def test_allows_localhost_base_url():
    cfg = _disposable_config(base_url="http://localhost:8000")
    coord = srr.RehearsalCoordinator(cfg)
    assert coord is not None


def test_allows_127_base_url():
    cfg = _disposable_config(base_url="http://127.0.0.1:9000")
    coord = srr.RehearsalCoordinator(cfg)
    assert coord is not None


# ---------------------------------------------------------------------------
# Plan mode: no subprocess, returns step list
# ---------------------------------------------------------------------------

def test_plan_mode_returns_steps_without_subprocess():
    """plan() must return the gate list without calling any runner."""
    cfg = _disposable_config(dry_run=True)
    runner = FakeRunner()
    coord = srr.RehearsalCoordinator(cfg, runner=runner)
    steps = coord.plan()
    assert runner.calls == [], "plan() must not invoke runner"
    assert isinstance(steps, list)
    assert len(steps) > 0


def test_plan_step_structure():
    """Each step dict must have name, command, description."""
    cfg = _disposable_config(dry_run=True)
    coord = srr.RehearsalCoordinator(cfg)
    steps = coord.plan()
    for step in steps:
        assert "name" in step, f"step missing 'name': {step}"
        assert "command" in step, f"step missing 'command': {step}"
        assert "description" in step, f"step missing 'description': {step}"


def test_plan_includes_required_gates():
    """Plan must include workflow_safety, migration_preflight, release_metadata."""
    cfg = _disposable_config(dry_run=True)
    coord = srr.RehearsalCoordinator(cfg)
    steps = coord.plan()
    names = {s["name"] for s in steps}
    assert "workflow_safety" in names
    assert "migration_preflight" in names
    assert "release_metadata" in names


def test_plan_dry_run_excludes_destructive_steps():
    """In dry_run, backup and restore steps must be flagged skip or absent."""
    cfg = _disposable_config(dry_run=True)
    coord = srr.RehearsalCoordinator(cfg)
    steps = coord.plan()
    for step in steps:
        if step["name"] in ("backup_postgres", "restore_drill"):
            assert step.get("skip") is True or step.get("mode") == "dry_run", (
                f"Destructive step {step['name']!r} must be skipped in dry_run"
            )


def test_plan_commands_contain_no_credentials():
    """Commands in plan must never embed password values."""
    cfg = _disposable_config(dry_run=True)
    coord = srr.RehearsalCoordinator(cfg)
    steps = coord.plan()
    for step in steps:
        cmd_str = " ".join(step.get("command", []))
        assert "password" not in cmd_str.lower() or "--no-password" in cmd_str.lower(), (
            f"Step {step['name']!r} command may contain credentials"
        )
        assert "s3cret" not in cmd_str
        assert "PGPASSWORD" not in cmd_str


# ---------------------------------------------------------------------------
# run() in dry-run mode
# ---------------------------------------------------------------------------

def test_dry_run_returns_report_without_runner_calls():
    """dry_run=True run() must return ok report without calling runner."""
    cfg = _disposable_config(dry_run=True)
    runner = FakeRunner()
    coord = srr.RehearsalCoordinator(cfg, runner=runner)
    report = coord.run()
    assert runner.calls == [], "dry_run must not invoke runner"
    assert report["ok"] is True
    assert "steps" in report
    assert "mode" in report
    assert report["mode"] == "dry_run"


def test_dry_run_report_has_no_credentials():
    """Report from dry_run must contain no credential values."""
    cfg = _disposable_config(dry_run=True)
    coord = srr.RehearsalCoordinator(cfg)
    report = coord.run()
    import json
    serialized = json.dumps(report)
    # Must not contain password patterns (simple guard)
    assert "password" not in serialized.lower() or "no-password" in serialized.lower()


def test_dry_run_report_lists_all_gate_names():
    cfg = _disposable_config(dry_run=True)
    coord = srr.RehearsalCoordinator(cfg)
    report = coord.run()
    names = {s["name"] for s in report["steps"]}
    assert "workflow_safety" in names
    assert "migration_preflight" in names
    assert "release_metadata" in names


# ---------------------------------------------------------------------------
# run() in live mode: runner injection
# ---------------------------------------------------------------------------

def test_live_run_invokes_runner_for_each_non_skipped_step(tmp_path):
    """Live mode must call runner for each non-skipped gate."""
    dump = tmp_path / "backup.dump"
    dump.write_bytes(b"PGDMP")
    cfg = _disposable_config(dry_run=False, live=True, backup_dump=str(dump))
    runner = FakeRunner(default_rc=0, default_stdout="WORKFLOW_SAFETY_OK\nstatus=ok\n")
    coord = srr.RehearsalCoordinator(cfg, runner=runner)
    report = coord.run()
    # At least workflow_safety, migration_preflight, release_metadata must be called
    invoked = {" ".join(c["cmd"]) for c in runner.calls}
    assert any("assert_workflow_safety" in cmd for cmd in invoked), \
        "workflow_safety not called"
    assert any("migration_preflight" in cmd for cmd in invoked), \
        "migration_preflight not called"


def test_live_run_report_records_runner_exit_codes(tmp_path):
    dump = tmp_path / "backup.dump"
    dump.write_bytes(b"PGDMP")
    cfg = _disposable_config(dry_run=False, live=True, backup_dump=str(dump))
    runner = FakeRunner(default_rc=0, default_stdout="WORKFLOW_SAFETY_OK\nstatus=ok\n")
    coord = srr.RehearsalCoordinator(cfg, runner=runner)
    report = coord.run()
    for step in report["steps"]:
        if not step.get("skip"):
            assert "rc" in step, f"step {step['name']!r} missing rc"


def test_live_run_fails_report_when_gate_fails(tmp_path):
    """If a gate returns non-zero, report.ok must be False."""
    dump = tmp_path / "backup.dump"
    dump.write_bytes(b"PGDMP")
    cfg = _disposable_config(dry_run=False, live=True, backup_dump=str(dump))
    runner = FakeRunner(default_rc=1, default_stdout="", default_stderr="gate failure")
    coord = srr.RehearsalCoordinator(cfg, runner=runner)
    report = coord.run()
    assert report["ok"] is False


def test_live_run_sanitizes_runner_output(tmp_path):
    """Runner stdout/stderr with password-like strings must be redacted in report."""
    dump = tmp_path / "backup.dump"
    dump.write_bytes(b"PGDMP")
    cfg = _disposable_config(dry_run=False, live=True, backup_dump=str(dump))

    def leaky_runner(cmd, env=None):
        return 0, "connected password=s3krit host=127.0.0.1", ""

    coord = srr.RehearsalCoordinator(cfg, runner=leaky_runner)
    report = coord.run()
    import json
    serialized = json.dumps(report)
    assert "s3krit" not in serialized


def test_live_run_does_not_pass_env_with_passwords_to_steps(tmp_path):
    """When runner is called, env passed must not include raw passwords."""
    dump = tmp_path / "backup.dump"
    dump.write_bytes(b"PGDMP")
    cfg = _disposable_config(dry_run=False, live=True, backup_dump=str(dump))
    captured_envs: list[dict | None] = []

    def recording_runner(cmd, env=None):
        captured_envs.append(dict(env) if env else None)
        return 0, "WORKFLOW_SAFETY_OK\nstatus=ok\n", ""

    coord = srr.RehearsalCoordinator(cfg, runner=recording_runner)
    coord.run()
    for env in captured_envs:
        if env is None:
            continue
        # Coordinator must not inject plaintext password into env for these offline checks
        # (backup_postgres handles its own env securely when called)
        for v in env.values():
            assert "s3cret" not in str(v)
            assert "supersecret" not in str(v)


# ---------------------------------------------------------------------------
# backup_dump validation: live mode requires explicit path
# ---------------------------------------------------------------------------

def test_live_mode_refuses_missing_backup_dump():
    """Live mode must refuse when backup_dump is empty."""
    cfg = _disposable_config(dry_run=False, live=True, backup_dump="")
    with pytest.raises(srr.RehearsalRefused, match="backup.dump"):
        srr.RehearsalCoordinator(cfg)


def test_live_mode_refuses_nonexistent_backup_dump(tmp_path):
    """Live mode must refuse when backup_dump path does not exist on disk."""
    missing = str(tmp_path / "nonexistent.dump")
    cfg = _disposable_config(dry_run=False, live=True, backup_dump=missing)
    with pytest.raises(srr.RehearsalRefused, match="not a file|does not exist"):
        srr.RehearsalCoordinator(cfg)


def test_plan_mode_safe_without_backup_dump():
    """plan() in dry_run must succeed with no backup_dump provided."""
    cfg = _disposable_config(dry_run=True, live=False, backup_dump="")
    coord = srr.RehearsalCoordinator(cfg)
    steps = coord.plan()
    assert any(s["name"] == "restore_drill" for s in steps)


def test_dry_run_safe_without_backup_dump():
    """run() in dry_run must succeed with no backup_dump provided."""
    cfg = _disposable_config(dry_run=True, live=False, backup_dump="")
    coord = srr.RehearsalCoordinator(cfg)
    report = coord.run()
    assert report["ok"] is True
    assert report["mode"] == "dry_run"


def test_live_mode_restore_drill_uses_backup_dump_path(tmp_path):
    """restore_drill command in plan must contain the explicit --backup-dump path."""
    dump = tmp_path / "gptvli-20260714.dump"
    dump.write_bytes(b"PGDMP")
    cfg = _disposable_config(dry_run=False, live=True, backup_dump=str(dump))
    coord = srr.RehearsalCoordinator(cfg)
    steps = coord.plan()
    restore = next(s for s in steps if s["name"] == "restore_drill")
    cmd_str = " ".join(restore["command"])
    assert str(dump) in cmd_str, "restore_drill command must contain the explicit dump path"
    assert "<latest>" not in cmd_str, "restore_drill must not use implicit <latest> placeholder"


# ---------------------------------------------------------------------------
# Output sanitization unit tests
# ---------------------------------------------------------------------------

def test_sanitize_strips_password_value():
    result = srr.sanitize_output("connected pg://user:hunter2@host/db")
    assert "hunter2" not in result
    assert "***" in result


def test_sanitize_strips_pgpassword_env_value():
    result = srr.sanitize_output("PGPASSWORD=mysecret running pg_dump")
    assert "mysecret" not in result


def test_sanitize_preserves_non_secret_content():
    result = srr.sanitize_output("status=ok host=127.0.0.1 toc_entries=42")
    assert "status=ok" in result
    assert "127.0.0.1" in result
    assert "42" in result


def test_sanitize_strips_api_key_patterns():
    result = srr.sanitize_output("GOOGLE_API_KEY=AIzaSyABCDEFGHIJKLMNOPQR")
    assert "AIzaSyABCDEFGHIJKLMNOPQR" not in result


# ---------------------------------------------------------------------------
# Config validation helpers
# ---------------------------------------------------------------------------

def test_is_disposable_target_accepts_localhost():
    assert srr.is_disposable_target("127.0.0.1", "gptvli_drill") is True


def test_is_disposable_target_accepts_drill_db():
    assert srr.is_disposable_target("localhost", "rehearsal_drill_db") is True


def test_is_disposable_target_rejects_rds():
    assert srr.is_disposable_target("myapp.rds.amazonaws.com", "app_db") is False


def test_is_disposable_target_rejects_production_db_name():
    assert srr.is_disposable_target("localhost", "production") is False


def test_is_disposable_target_rejects_prod_db_name():
    assert srr.is_disposable_target("localhost", "prod-db") is False


def test_is_disposable_target_rejects_cloudsql():
    assert srr.is_disposable_target("myproj:us-central1:cloudsql", "app") is False


@pytest.mark.parametrize("db_name", ["postgres", "template0", "template1"])
def test_is_disposable_target_rejects_system_databases(db_name):
    assert srr.is_disposable_target("localhost", db_name) is False


def test_default_runner_converts_timeout_to_failure(monkeypatch):
    import subprocess

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=600)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    rc, stdout, stderr = srr._default_runner(["missing"], None)
    assert rc == 1
    assert stdout == ""
    assert "timed out" in stderr.lower()


def test_default_runner_converts_os_error_to_failure(monkeypatch):
    import subprocess

    def raise_os_error(*args, **kwargs):
        raise FileNotFoundError("missing executable")

    monkeypatch.setattr(subprocess, "run", raise_os_error)
    rc, stdout, stderr = srr._default_runner(["missing"], None)
    assert rc == 1
    assert stdout == ""
    assert "missing executable" in stderr


# ---------------------------------------------------------------------------
# CLI smoke (no live execution)
# ---------------------------------------------------------------------------

def test_cli_plan_exits_zero(tmp_path):
    """CLI --plan flag must exit 0 and print steps."""
    import subprocess
    script = ROOT / "scripts" / "staging_release_rehearsal.py"
    proc = subprocess.run(
        [
            sys.executable, str(script),
            "--plan",
            "--opt-in",
            "--target-db", "gptvli_rehearsal_drill",
            "--target-host", "127.0.0.1",
            "--backup-dest", str(tmp_path / "backups"),
            "--uploads-source", str(tmp_path / "uploads"),
            "--base-url", "http://127.0.0.1:8000",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert "workflow_safety" in proc.stdout or "migration_preflight" in proc.stdout


def test_cli_dry_run_exits_zero(tmp_path):
    """CLI --dry-run must exit 0 without external binaries."""
    import subprocess
    script = ROOT / "scripts" / "staging_release_rehearsal.py"
    proc = subprocess.run(
        [
            sys.executable, str(script),
            "--dry-run",
            "--opt-in",
            "--target-db", "gptvli_rehearsal_drill",
            "--target-host", "127.0.0.1",
            "--backup-dest", str(tmp_path / "backups"),
            "--uploads-source", str(tmp_path / "uploads"),
            "--base-url", "http://127.0.0.1:8000",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr


def test_cli_refuses_without_opt_in(tmp_path):
    """CLI without --opt-in must exit nonzero."""
    import subprocess
    script = ROOT / "scripts" / "staging_release_rehearsal.py"
    proc = subprocess.run(
        [
            sys.executable, str(script),
            "--dry-run",
            "--target-db", "gptvli_rehearsal_drill",
            "--target-host", "127.0.0.1",
            "--backup-dest", str(tmp_path / "backups"),
            "--uploads-source", str(tmp_path / "uploads"),
            "--base-url", "http://127.0.0.1:8000",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode != 0


def test_cli_refuses_prod_host(tmp_path):
    """CLI must exit nonzero for production-looking host."""
    import subprocess
    script = ROOT / "scripts" / "staging_release_rehearsal.py"
    proc = subprocess.run(
        [
            sys.executable, str(script),
            "--dry-run",
            "--opt-in",
            "--target-db", "gptvli_rehearsal_drill",
            "--target-host", "myapp.rds.amazonaws.com",
            "--backup-dest", str(tmp_path / "backups"),
            "--uploads-source", str(tmp_path / "uploads"),
            "--base-url", "http://127.0.0.1:8000",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode != 0
