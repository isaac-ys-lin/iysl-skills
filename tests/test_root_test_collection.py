"""Guard the repo-root pytest run.

Every CI gate runs pytest per skill after a cd, so a root-level run can break
without turning CI red. It did: eight skills own a `tests/test_contract.py`,
and under pytest's default prepend import mode those module names collide, so
collection aborted before any test executed.

`pyproject.toml` sets importlib import mode to resolve that. Nothing else
asserts it stays set, which is how a fix quietly becomes prose. These tests
fail if the config is dropped, and the duplicate-basename check keeps the
guard honest: if the collision ever stops existing, this file should be
reconsidered rather than left passing for the wrong reason.
"""

import os
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


class RootTestCollectionTest(unittest.TestCase):
    def test_duplicate_test_basenames_still_exist(self):
        """The condition this guard exists for. If this fails, the guard is stale."""
        counts = Counter(path.name for path in SKILLS.glob("*/tests/test_*.py"))
        duplicates = {name: n for name, n in counts.items() if n > 1}
        self.assertTrue(
            duplicates,
            "no duplicate test basenames remain across skills; the import-mode "
            "guard in pyproject.toml may no longer be needed",
        )

    def test_pytest_collects_every_skill_test_from_the_repo_root(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "skills",
                "--collect-only",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            # Collection imports every skill test module. Without this the
            # subprocess writes __pycache__ into skills/, which is exactly the
            # residue that test_package_contract.py forbids: this guard would
            # then fail the next run of the suite it belongs to.
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(
            result.returncode,
            0,
            "pytest cannot collect the skill suites from the repo root. If this "
            "mentions duplicate basenames, the import-mode setting in "
            "pyproject.toml was removed or overridden.\n"
            f"{result.stdout[-2000:]}{result.stderr[-2000:]}",
        )


if __name__ == "__main__":
    unittest.main()
