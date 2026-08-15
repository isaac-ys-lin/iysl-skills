import shutil
import subprocess
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VERIFY_SKILL = ROOT / "tools" / "verify-skill.sh"


def bash_executable():
    if os.name != "nt":
        return shutil.which("bash") or "bash"
    git = shutil.which("git")
    if git:
        git_bash = Path(git).parent.parent / "bin" / "bash.exe"
        if git_bash.is_file():
            return str(git_bash)
    pytest.skip("Git for Windows bash.exe is unavailable")


def make_mixed_test_repo(tmp_path, bare_pytest_body):
    repo = tmp_path / "repo"
    (repo / "tools").mkdir(parents=True)
    skill = repo / "skills" / "mixed"
    (skill / "tests").mkdir(parents=True)
    shutil.copy2(VERIFY_SKILL, repo / "tools" / "verify-skill.sh")
    (skill / "SKILL.md").write_text("---\nname: mixed\ndescription: fixture\n---\n")
    (skill / "tests" / "test_unittest_case.py").write_text(
        "import unittest\n\n"
        "class PassingCase(unittest.TestCase):\n"
        "    def test_passes(self):\n"
        "        self.assertTrue(True)\n"
    )
    (skill / "tests" / "test_bare_pytest.py").write_text(
        f"def test_bare_pytest():\n    {bare_pytest_body}\n"
    )
    return repo


def test_mixed_framework_failure_cannot_be_skipped(tmp_path):
    repo = make_mixed_test_repo(tmp_path, "assert False, 'must be collected'")
    result = subprocess.run(
        [bash_executable(), str(repo / "tools" / "verify-skill.sh"), "mixed"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "must be collected" in result.stdout + result.stderr


def test_mixed_framework_success_runs_both_tests(tmp_path):
    repo = make_mixed_test_repo(tmp_path, "assert True")
    result = subprocess.run(
        [bash_executable(), str(repo / "tools" / "verify-skill.sh"), "mixed"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout
