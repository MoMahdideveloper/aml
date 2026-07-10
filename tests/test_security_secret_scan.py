"""Secret scanner contract: reports path/pattern only, never secret values."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "scripts" / "scan_secrets.py"


def test_scan_secrets_script_runs_and_omits_values():
    proc = subprocess.run(
        [sys.executable, str(SCANNER), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # May exit 1 on high findings; still must produce valid JSON on stdout
    assert proc.stdout.strip(), proc.stderr
    report = json.loads(proc.stdout)
    assert "findings" in report
    assert "summary" in report
    for f in report["findings"]:
        assert "path" in f and "pattern" in f and "line" in f
        # Never serialize match text
        assert "match" not in f
        assert "value" not in f
        assert "secret" not in f
        assert "snippet" not in f


def test_scan_detects_synthetic_fixture_without_printing_secret(tmp_path):
    """Unit-style: invoke scan() on a tiny tree via import."""
    # Import scanner module
    sys.path.insert(0, str(ROOT / "scripts"))
    import scan_secrets  # type: ignore

    sample = tmp_path / "leak_probe.py"
    # Synthetic only — value must never appear in findings dict
    sample.write_text(
        'API_KEY = "sk-this-is-a-fake-test-key-abcdefgh"\n',
        encoding="utf-8",
    )
    # Monkeypatch git_ls_files to only return our sample
    scan_secrets._git_ls_files = lambda root: [sample]  # type: ignore
    findings = scan_secrets.scan(tmp_path)
    assert findings, "expected at least one pattern hit"
    blob = json.dumps(findings)
    assert "sk-this-is-a-fake-test-key-abcdefgh" not in blob
    assert any(f["pattern"] == "generic_api_key_assignment" for f in findings)
