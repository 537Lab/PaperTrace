"""Exercise the team-offline test collection entry point used by Gate 5."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_gate5_importlib_collects_evaluation_control_paths():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            "papertrace.pytest.ini",
            "--import-mode=importlib",
            "--collect-only",
            "-q",
            "-p",
            "pytest_socket",
            "test/offline/test_evaluation_control_paths.py",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTEST_ADDOPTS": "", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "::test_evaluation_controls_are_implementation_not_unapproved_test_edits" in result.stdout
