"""Contract tests for docker/entrypoint.sh fail-closed migrations."""

from pathlib import Path
import os
import shutil
import stat
import subprocess
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "docker" / "entrypoint.sh"


def test_entrypoint_script_exists_and_fail_closed():
    text = ENTRYPOINT.read_text(encoding="utf-8")
    assert "RUN_MIGRATIONS" in text
    assert "flask db upgrade" in text
    # Must not start app after migration failure
    assert "will still start app" not in text
    assert "exit 1" in text
    # Explicit skip path for operator-managed migrations
    assert 'RUN_MIGRATIONS=0' in text or 'RUN_MIGRATIONS:-1' in text


@pytest.mark.skipif(not shutil.which("sh"), reason="POSIX sh required for entrypoint execution tests")
def test_entrypoint_exits_nonzero_when_migrations_fail(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    flask_stub = bin_dir / "flask"
    flask_stub.write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            echo "fake flask failing" >&2
            exit 1
            """
        ),
        encoding="utf-8",
    )
    flask_stub.chmod(flask_stub.stat().st_mode | stat.S_IEXEC)

    sleep_stub = bin_dir / "sleep"
    sleep_stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    sleep_stub.chmod(sleep_stub.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["RUN_MIGRATIONS"] = "1"
    env["MIGRATION_RETRIES"] = "2"
    env["MIGRATION_RETRY_DELAY"] = "0"
    env["FLASK_ENV"] = "production"

    result = subprocess.run(
        ["sh", str(ENTRYPOINT), "echo", "should-not-run"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "refusing to start" in (result.stdout + result.stderr).lower() or "ERROR" in result.stdout
    assert "should-not-run" not in result.stdout


@pytest.mark.skipif(not shutil.which("sh"), reason="POSIX sh required for entrypoint execution tests")
def test_entrypoint_skips_migrations_when_disabled(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # flask should never be needed
    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["RUN_MIGRATIONS"] = "0"

    result = subprocess.run(
        ["sh", str(ENTRYPOINT), "echo", "started-ok"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0
    assert "started-ok" in result.stdout
    assert "skipping migrations" in result.stdout.lower() or "RUN_MIGRATIONS=0" in result.stdout


@pytest.mark.skipif(not shutil.which("sh"), reason="POSIX sh required for entrypoint execution tests")
def test_entrypoint_proceeds_when_migrations_succeed(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    flask_stub = bin_dir / "flask"
    flask_stub.write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            # Accept: flask db upgrade heads
            exit 0
            """
        ),
        encoding="utf-8",
    )
    flask_stub.chmod(flask_stub.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["RUN_MIGRATIONS"] = "1"
    env["MIGRATION_RETRIES"] = "1"

    result = subprocess.run(
        ["sh", str(ENTRYPOINT), "echo", "app-started"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0
    assert "Migrations complete" in result.stdout
    assert "app-started" in result.stdout
