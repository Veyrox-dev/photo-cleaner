"""Integration test for crash input script."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_crash_inputs_script_runs_clean():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "test_crash_inputs.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
