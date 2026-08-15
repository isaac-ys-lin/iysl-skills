import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "compare-installed-skills.py"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not expose POSIX execute bits")
def test_install_parity_detects_executable_mode_change(tmp_path):
    source = tmp_path / "source" / "example" / "scripts"
    installed = tmp_path / "installed" / "example" / "scripts"
    source.mkdir(parents=True)
    installed.mkdir(parents=True)
    source_script = source / "run.sh"
    installed_script = installed / "run.sh"
    source_script.write_text("#!/bin/sh\n", encoding="utf-8")
    installed_script.write_text("#!/bin/sh\n", encoding="utf-8")
    source_script.chmod(0o755)
    installed_script.chmod(0o644)

    result = subprocess.run(
        [sys.executable, str(RUNNER), str(source.parent.parent), str(installed.parent.parent)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "scripts/run.sh" in result.stderr
