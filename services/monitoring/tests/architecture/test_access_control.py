"""
Every route carries an operation_id and the central check, and config/access-control.json grants each
one to some role. Runs in a subprocess so it checks the app exactly as it starts.
"""

import subprocess
import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[2]


def test_access_control_setup_is_valid() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_access.py"], cwd=SERVICE_DIR, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
